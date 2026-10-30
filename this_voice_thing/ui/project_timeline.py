"""The project timeline: one lane per track, clips as blocks with their waveform, a playhead.

Painted with QPainter from the theme tokens, so it follows light/dark like the rest of the app.
It only draws and reports clicks; the project and its edits stay in ProjectSession.
"""
import math
from dataclasses import replace

import numpy as np
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from this_voice_thing.core.timeline_visual_math import PEAKS_PER_SECOND, envelope, ruler_tick_step
from this_voice_thing.ui import theme as ui_theme

class TimelineView(QWidget):
    clipSelected = Signal(str)        # clip id
    clipActivated = Signal(str)       # double-click: edit
    seekRequested = Signal(float)     # seconds, from a click on the ruler
    clipPlaced = Signal(str, int, int, int)   # drag finished: clip id, start, length, source offset (frames)

    RULER = 26
    LANE = 72
    HEADER = 148
    MIN_SECONDS = 10.0
    EDGE = 7                          # px at each end of a clip that trims instead of moving
    MIN_CLIP_SECONDS = 0.05           # trimming stops here: no near-zero clips
    MAX_LOOP_SECONDS = 4 * 3600       # a looping sound can be stretched this far

    def __init__(self, label_for_clip=None, parent=None):
        super().__init__(parent)
        self.project = None
        self.peaks = {}               # asset_id -> envelope at PEAKS_PER_SECOND
        self.selected = None
        self.playhead = None          # seconds, or None when stopped
        self.label_for_clip = label_for_clip or (lambda clip: "")
        self._hits = []               # (QRectF, clip_id)
        self.source_lengths = {}      # asset_id -> (source samples, source rate): the trim limit
        self._drag = None             # the clip being moved or trimmed, while the button is down
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(self.RULER + self.LANE + 8)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ---- state ----
    def set_project(self, project):
        self._drag = None             # the clip may have changed under the pointer
        self.project = project
        self.setMinimumHeight(self.RULER + max(1, len(project.tracks if project else [])) * self.LANE + 8)
        self.updateGeometry()
        self.update()

    def set_peaks(self, asset_id, peaks, source_length=None):
        """source_length: (samples, sample_rate) of the asset as stored."""
        self.peaks[asset_id] = peaks
        if source_length:
            self.source_lengths[asset_id] = (int(source_length[0]), int(source_length[1]))
        self.update()

    def source_frames(self, asset_id):
        """The asset's length at this project's rate, as the mixer resamples it (or None)."""
        found = self.source_lengths.get(asset_id)
        if not found or not self.project:
            return None
        samples, rate = found
        return math.ceil(samples * self.project.sample_rate / rate)

    def set_selected(self, clip_id):
        self.selected = clip_id
        self.update()

    def set_playhead(self, seconds):
        self.playhead = seconds
        self.update()

    def total_seconds(self):
        if self._drag is not None:
            return self._drag["total"]    # the scale stays put while a clip is dragged
        if not self.project:
            return self.MIN_SECONDS
        rate = self.project.sample_rate
        ends = [(c.start_frame + c.frame_count) / rate for t in self.project.tracks for c in t.clips]
        return max([self.MIN_SECONDS] + ends) * 1.04

    def _x(self, seconds):
        width = max(1.0, self.width() - self.HEADER - 12)
        return self.HEADER + seconds / self.total_seconds() * width

    def _seconds_at(self, x):
        width = max(1.0, self.width() - self.HEADER - 12)
        return max(0.0, (x - self.HEADER) / width * self.total_seconds())

    # ---- painting ----
    def paintEvent(self, _event):
        c = ui_theme.current()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # The card surface with a frame, like the track list below it: on the light theme the
        # timeline's old fill matched the page, so it had no visible edge.
        painter.fillRect(self.rect(), QColor(c["surface"]))
        self._hits = []
        self._paint_ruler(painter, c)
        if self.project:
            for index, track in enumerate(self.project.tracks):
                self._paint_lane(painter, c, index, track)
        if self.playhead is not None:
            x = self._x(self.playhead)
            painter.setPen(QPen(QColor(c["brand_tertiary"]), 2))
            painter.drawLine(QPointF(x, 0), QPointF(x, self.height()))
        if self.project is None or not self.project.tracks:
            painter.setPen(QColor(c["muted"]))
            painter.setFont(self.font())            # the ruler's small font was still set
            painter.drawText(self.rect().adjusted(self.HEADER, self.RULER, 0, 0), Qt.AlignmentFlag.AlignCenter,
                             "Tracks appear here as you add sounds and narration.")
        painter.setPen(QColor(c["border"]))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 7, 7)
        painter.end()

    def _paint_ruler(self, painter, c):
        painter.setPen(QColor(c["muted"]))
        small = QFont(self.font())
        small.setPointSizeF(max(7.0, small.pointSizeF() - 1.5))
        painter.setFont(small)
        total = self.total_seconds()
        step = ruler_tick_step(total)
        for tick in range(0, int(total) + 1, step):
            x = self._x(tick)
            painter.drawLine(QPointF(x, self.RULER - 6), QPointF(x, self.RULER))
            minutes, seconds = divmod(tick, 60)
            painter.drawText(QRectF(x + 3, 2, 60, self.RULER - 6), Qt.AlignmentFlag.AlignLeft,
                             f"{minutes}:{seconds:02d}")
        painter.setPen(QColor(c["border"]))
        painter.drawLine(QPointF(0, self.RULER), QPointF(self.width(), self.RULER))

    def _paint_lane(self, painter, c, index, track):
        top = self.RULER + index * self.LANE
        lane = QRectF(0, top, self.width(), self.LANE)
        painter.fillRect(lane, QColor(c["surface"] if index % 2 == 0 else c["surface_alt"]))
        painter.setPen(QColor(c["border"]))
        painter.drawLine(lane.bottomLeft(), lane.bottomRight())
        # header: name, kind and mute state
        painter.setPen(QColor(c["muted"] if track.muted else c["text"]))
        name_font = QFont(self.font())
        name_font.setBold(True)
        painter.setFont(name_font)
        painter.drawText(QRectF(12, top + 8, self.HEADER - 18, 18), Qt.AlignmentFlag.AlignLeft,
                         painter.fontMetrics().elidedText(track.name, Qt.TextElideMode.ElideRight, self.HEADER - 18))
        painter.setFont(self.font())
        painter.setPen(QColor(c["muted"]))
        detail = track.kind.capitalize() + ("  ·  muted" if track.muted else "") + (
            f"  ·  {track.gain_db:+.1f} dB" if track.gain_db else "")
        painter.drawText(QRectF(12, top + 28, self.HEADER - 18, 18), Qt.AlignmentFlag.AlignLeft, detail)
        rate = self.project.sample_rate
        tint = QColor(c["accent"] if track.kind == "voice" else c["brand_secondary"] if track.kind == "sound"
                      else c["brand_blue"])
        for clip in track.clips:
            clip = self._shown(clip)
            x1, x2 = self._x(clip.start_frame / rate), self._x((clip.start_frame + clip.frame_count) / rate)
            if clip.frame_count == 0:          # script without audio yet: a dashed marker
                x2 = x1 + 70
            rect = QRectF(x1, top + 6, max(4.0, x2 - x1), self.LANE - 12)
            self._paint_clip(painter, c, clip, rect, tint, track.muted)
            self._hits.append((rect, clip.id))

    def _paint_clip(self, painter, c, clip, rect, tint, muted):
        fill = QColor(tint)
        fill.setAlpha(60 if muted else 95)
        edge = QColor(tint)
        edge.setAlpha(120 if muted else 220)
        path = QPainterPath()
        path.addRoundedRect(rect, 6, 6)
        painter.fillPath(path, fill)
        pen = QPen(QColor(c["focus"]) if clip.id == self.selected else edge, 2 if clip.id == self.selected else 1)
        if not clip.asset_id:
            pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawPath(path)
        peaks = self.peaks.get(clip.asset_id)
        if peaks is not None and len(peaks) and rect.width() > 6:
            painter.save()
            painter.setClipPath(path)
            wave = QColor(tint)
            wave.setAlpha(150 if muted else 235)
            painter.setPen(QPen(wave, 1))
            seconds = clip.frame_count / self.project.sample_rate
            middle, half = rect.center().y(), rect.height() * 0.42
            columns = int(rect.width())
            skipped = clip.source_offset_frames / self.project.sample_rate * PEAKS_PER_SECOND
            for column in range(0, columns, 2):
                position = skipped + column / max(1, columns) * seconds * PEAKS_PER_SECOND
                index = int(position) % len(peaks) if clip.loop else min(int(position), len(peaks) - 1)
                level = float(peaks[index]) * self._fade_gain(clip, column / max(1, columns))
                x = rect.left() + column
                painter.drawLine(QPointF(x, middle - level * half), QPointF(x, middle + level * half))
            painter.restore()
        label = self.label_for_clip(clip)
        if label and rect.width() > 40:
            painter.setPen(QColor(c["text"]))
            painter.drawText(rect.adjusted(8, 3, -6, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                             painter.fontMetrics().elidedText(label, Qt.TextElideMode.ElideRight, int(rect.width() - 14)))

    @staticmethod
    def _fade_gain(clip, fraction):
        if clip.frame_count <= 0:
            return 1.0
        position = fraction * clip.frame_count
        gain = 1.0
        if clip.fade_in_frames and position < clip.fade_in_frames:
            gain = position / clip.fade_in_frames
        remaining = clip.frame_count - position
        if clip.fade_out_frames and remaining < clip.fade_out_frames:
            gain = min(gain, remaining / clip.fade_out_frames)
        return max(0.0, gain)

    # ---- interaction ----
    def _clip_at(self, point):
        for rect, clip_id in reversed(self._hits):
            if rect.contains(point):
                return clip_id
        return None

    def _shown(self, clip):
        """The clip as drawn: with the in-progress drag applied, if this is the dragged clip."""
        drag = self._drag
        if drag is None or drag["clip_id"] != clip.id or drag["now"] is None:
            return clip
        start, count, offset = drag["now"]
        return replace(clip, start_frame=start, frame_count=count, source_offset_frames=offset)

    def _clip(self, clip_id):
        for track in (self.project.tracks if self.project else []):
            for clip in track.clips:
                if clip.id == clip_id:
                    return clip
        return None

    def _zone(self, point, clip_id):
        """'start' / 'end' near a clip's edges (trim), 'move' elsewhere; scripts only move."""
        clip = self._clip(clip_id)
        rect = next(r for r, cid in self._hits if cid == clip_id)
        if clip is None or not clip.asset_id or rect.width() < 3 * self.EDGE:
            return "move"
        if point.x() - rect.left() <= self.EDGE:
            return "start"
        if rect.right() - point.x() <= self.EDGE:
            return "end"
        return "move"

    def _frames_per_pixel(self):
        width = max(1.0, self.width() - self.HEADER - 12)
        return self.total_seconds() * self.project.sample_rate / width

    def _drag_to(self, x):
        """Placement for a drag that reached x, inside every limit (whole frames)."""
        d = self._drag
        rate = self.project.sample_rate
        delta = round((x - d["press_x"]) * d["frames_per_px"])
        start, count, offset = d["start"], d["count"], d["offset"]
        minimum = max(1, round(self.MIN_CLIP_SECONDS * rate))
        minimum = max(1, min(minimum, count, d["source"] - offset))   # a clip already shorter stays legal
        if d["mode"] == "move":
            return max(0, start + delta), count, offset
        if d["mode"] == "start":
            # Moving the start edge: start and offset move together, the end stays put.
            delta = max(delta, -start, -offset)
            delta = min(delta, count - minimum)
            return start + delta, count - delta, offset + delta
        # Moving the end edge: only the length changes; never past the end of the audio.
        longest = round(self.MAX_LOOP_SECONDS * rate) if d["loop"] else d["source"] - offset
        return start, max(minimum, min(count + delta, longest)), offset

    def mousePressEvent(self, event):
        point = event.position()
        if event.button() == Qt.MouseButton.RightButton and self._drag is not None:
            self.cancel_drag()
            return
        if point.y() <= self.RULER and point.x() >= self.HEADER:
            self.seekRequested.emit(self._seconds_at(point.x()))
            return
        clip_id = self._clip_at(point)
        if not clip_id:
            return
        self.set_selected(clip_id)
        self.clipSelected.emit(clip_id)
        if event.button() != Qt.MouseButton.LeftButton:
            return
        clip = self._clip(clip_id)
        if clip is None:
            return
        source = self.source_frames(clip.asset_id)
        mode = self._zone(point, clip_id)
        if mode != "move" and not clip.loop and source is None:
            mode = "move"                 # the audio's length isn't known yet: no trimming
        self._drag = {"clip_id": clip_id, "mode": mode, "press_x": point.x(), "now": None,
                      "start": clip.start_frame, "count": clip.frame_count, "offset": clip.source_offset_frames,
                      "loop": clip.loop, "source": source or clip.source_offset_frames + clip.frame_count,
                      "total": self.total_seconds()}
        self._drag["frames_per_px"] = self._frames_per_pixel()
        self.setFocus()

    def mouseMoveEvent(self, event):
        point = event.position()
        if self._drag is not None:
            if event.buttons() & Qt.MouseButton.LeftButton:
                self._drag["now"] = self._drag_to(point.x())
                self.update()
                return
            self.cancel_drag()        # the release was lost (another window took the pointer)
        clip_id = self._clip_at(point)
        if clip_id:
            zone = self._zone(point, clip_id)
            self.setCursor(Qt.CursorShape.SizeHorCursor if zone != "move" else Qt.CursorShape.OpenHandCursor)
        elif point.y() <= self.RULER and point.x() >= self.HEADER:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        drag, self._drag = self._drag, None
        if drag is None or event.button() != Qt.MouseButton.LeftButton:
            self._drag = drag if event.button() != Qt.MouseButton.LeftButton else None
            return
        now = drag["now"]
        self.update()
        if now is not None and now != (drag["start"], drag["count"], drag["offset"]):
            self.clipPlaced.emit(drag["clip_id"], *now)

    def cancel_drag(self):
        """Esc or a right-click mid-drag puts the clip back where it was."""
        if self._drag is not None:
            self._drag = None
            self.update()

    def focusOutEvent(self, event):
        self.cancel_drag()
        super().focusOutEvent(event)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.ActivationChange and not self.isActiveWindow():
            self.cancel_drag()
        super().changeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self._drag is not None:
            self.cancel_drag()
            event.accept()
            return
        super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self._drag = None
        clip_id = self._clip_at(event.position())
        if clip_id:
            self.clipActivated.emit(clip_id)

def preview_mix(project, media, duck=True):
    """Render the arranged mix for listening (not mastered); returns (audio, sample_rate)."""
    from this_voice_thing.core.audio_project_duck import duck_ambience
    from this_voice_thing.core.audio_timeline_mix import render_timeline
    raw = render_timeline(project, media.resolve)
    mixed = duck_ambience(project, raw) if duck else raw
    audio = np.asarray(mixed.audio, dtype=np.float32)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0.99:                       # preview only: keep it from clipping, no loudness change
        audio = audio * (0.99 / peak)
    return audio, project.sample_rate


def seconds_label(seconds):
    minutes, rest = divmod(max(0.0, seconds), 60)
    return f"{int(minutes)}:{rest:04.1f}" if not math.isnan(rest) else "0:00.0"
