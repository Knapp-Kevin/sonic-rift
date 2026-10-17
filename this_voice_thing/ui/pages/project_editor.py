"""The Studio: arrange speech, sounds and narration on one timeline and export the mix.

A visual timeline (lanes, clip blocks with waveforms, playhead, mix preview) above the
track list. Narration scripts can be rendered in place with the voice chosen in Create.
Qt widgets only hold inputs; versioned project state lives in ProjectSession.
"""
from copy import deepcopy
from threading import Event
import math
import os
from pathlib import Path
import re
import tempfile

import soundfile as sf

from PySide6.QtCore import QUrl, Qt, Slot
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView,
    QInputDialog, QLabel, QMessageBox, QPushButton, QSplitter, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QDialogButtonBox,
)

from this_voice_thing.core.audio_project import AudioProject, Clip, new_id
from this_voice_thing.core.audio_project_session import (
    ProjectSession, compatible_track_id, generated_take_target, may_attach_import_result,
)
from this_voice_thing.core.audio_project_media import ProjectMedia
from this_voice_thing.core.audio_project_export import export_project
from this_voice_thing.ui.project_timeline import TimelineView, envelope, preview_mix, seconds_label
from this_voice_thing.ui.threads import TaskThread
from this_voice_thing.ui.widgets import MenuButton, set_empty_text, set_role


def describe_error(message, project=None):
    """Plain-language text for errors raised by the project core and exporter."""
    text = str(message or "")
    if text.startswith("Cannot resolve clip asset:"):
        asset_id = text.split(":", 1)[1].strip()
        for track in (project.tracks if project is not None else []):
            for clip in track.clips:
                if clip.asset_id == asset_id:
                    what = "sound" if asset_id.startswith("sound_") else "narration take"
                    return (f"The {what} used on \u201c{track.name}\u201d at "
                            f"{clip.start_frame / project.sample_rate:.1f} s is missing or has changed on disk, "
                            "so the project can't be mixed. Re-attach it, or remove that clip.")
        return "Some audio this project uses is missing or has changed on disk. Re-attach it, then try again."
    if text.startswith("Source shorter than nonlooping clip:"):
        clip_id = text.split(":", 1)[1].strip()
        for track in (project.tracks if project is not None else []):
            for clip in track.clips:
                if clip.id == clip_id:
                    return (f"The clip on \u201c{track.name}\u201d at {clip.start_frame / project.sample_rate:.1f} s "
                            "is longer than its audio. Shorten it, or turn on \u201cRepeat sound as needed\u201d.")
        return "A clip is longer than its audio. Shorten it, or turn on looping."
    messages = {
        "Project export cancelled": "Export cancelled. Nothing was written.",
        "Unsupported project schema version":
            "This project file is from a different version of Sonic Rift or is damaged, so it can't be "
            "opened here.",
        "Refusing to replace an untracked project file":
            "A file with that name already exists. Choose a new name for this project.",
        "Project changed on disk; reopen instead of overwriting":
            "This project was changed outside the editor since you opened it. Reopen it to see those "
            "changes, or save it as a new file.",
        "Project changed on disk; reopen or save a new copy":
            "This project was changed outside the editor. Reopen it before exporting.",
        "Project has no rendered audio":
            "There's nothing to mix yet: add a sound or attach narration audio first.",
        "Refusing to overwrite an existing project export":
            "A folder with that name already exists there. Choose a new export name.",
    }
    if text == "Project exceeds unmastered PCM memory budget" and project is not None and project.tracks:
        from this_voice_thing.core.audio_timeline_mix import DEFAULT_MAX_MIX_BYTES
        rate = project.sample_rate
        ends = [c.start_frame + c.frame_count for t in project.tracks for c in t.clips] or [0]
        tracks = len(project.tracks)
        # The mixer holds the mix and one stem per track in memory (32-bit stereo).
        limit_minutes = DEFAULT_MAX_MIX_BYTES / (8 * (tracks + 1) * rate) / 60
        length_minutes = max(ends) / rate / 60
        return (f"This project is too long to export yet: it runs {length_minutes:.1f} minutes, and with "
                f"{tracks} track{'s' if tracks != 1 else ''} the current limit is about {limit_minutes:.1f} "
                "minutes. Shorten it or use fewer tracks; longer exports are planned.")
    if text in messages:
        return messages[text]
    if text.startswith(("Expecting", "Extra data", "Unterminated", "Invalid control", "'utf-8' codec")):
        return "This file isn't a readable Sonic Rift project. It may be damaged or incomplete."
    return text.strip("'\"")


class ProjectEditorDialog(QDialog):
    """Save, arrange and export tracks without changing Speech's settings.

    embedded=True: it is the Studio page of the main window (a child widget, not a window);
    Esc then doesn't close it, and the main window asks it to close when the app closes."""

    def __init__(self, owner, embedded=False):
        super().__init__(owner)
        self.owner = owner
        self.embedded = embedded
        if embedded:
            self.setWindowFlags(Qt.WindowType.Widget)
        self.setWindowTitle("Sonic Rift | Studio")
        self.resize(1000, 720)
        self.session = ProjectSession(AudioProject(new_id(), "Untitled project"))
        self.saved_revision = None
        self.baseline_revision = self.session.project.revision   # nothing to lose until edited
        self.session_serial = 0   # bumped on New/Open: a late import can't attach to another session
        self.worker = None
        self.import_worker = None
        self._pending_import = None
        self.export_cancel = None
        self.narration_job = None        # in-editor narration render: thread, target clip, then import
        self.peak_worker = None
        self.preview_worker = None
        self.preview_revision = None     # project revision the preview file was rendered from
        self.preview_file = None
        self.media = ProjectMedia(owner.script_dir, owner.sound_library)
        layout = QVBoxLayout(self)
        # As a page, line up with every other page's title and card edges.
        layout.setContentsMargins(*((24, 14, 24, 12) if embedded else (18, 14, 18, 14)))
        layout.setSpacing(8)
        # Same page header as the main window: title, then a muted state line.
        title_row = QHBoxLayout()
        self.title_label = QLabel()
        self.title_label.setObjectName("PageTitle")
        title_row.addWidget(self.title_label, 1)
        self.undo_button = self._button(title_row, "Undo", self.undo)
        self.redo_button = self._button(title_row, "Redo", self.redo)
        title_row.addWidget(MenuButton("Project", [
            ("New project\u2026", self.new_project),
            ("Open\u2026", self.open_project),
            ("Save", self.save_project),
            ("Rename\u2026", self.rename_project),
        ]))
        layout.addLayout(title_row)
        self.heading = QLabel()
        self.heading.setObjectName("PageSubtitle")
        layout.addWidget(self.heading)

        transport = QHBoxLayout()
        self.play_button = self._button(transport, "Play mix", self.play_preview)
        self.play_button.setToolTip("Listen to the arranged mix (with ducking; not mastered). "
                                    "Click the ruler to jump.")
        self.stop_button = self._button(transport, "Stop", self.stop_preview)
        self.stop_button.setEnabled(False)
        self.position_label = QLabel("0:00.0")
        self.position_label.setObjectName("Muted")
        transport.addWidget(self.position_label)
        transport.addStretch()
        layout.addLayout(transport)
        self.player = QMediaPlayer(self)
        self.audio_out = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_out)
        self.player.positionChanged.connect(self._on_preview_position)
        self.player.playbackStateChanged.connect(self._on_preview_state)

        self.timeline = TimelineView(self._clip_label)
        self.timeline.clipSelected.connect(self._select_clip_in_tree)
        self.timeline.clipActivated.connect(lambda clip_id: (self._select_clip_in_tree(clip_id),
                                                             self.edit_selected()))
        self.timeline.seekRequested.connect(self._seek_preview)
        self.timeline.clipPlaced.connect(self._clip_placed)

        self.tree = QTreeWidget()
        set_empty_text(self.tree, "Add a saved sound or narration to start. Each kind gets its own track.")
        self.tree.setHeaderLabels(["Track / clip", "Starts", "Length", "Gain", "Source"])
        self.tree.setRootIsDecorated(True)
        header = self.tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)       # names were cut to "Evenin..."
        for column in range(1, 5):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemDoubleClicked.connect(lambda *_: self.edit_selected())
        self.tree.currentItemChanged.connect(self._tree_selection_changed)
        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(self.timeline)
        split.addWidget(self.tree)
        split.setStretchFactor(0, 1)      # a few tracks no longer leave half the page empty
        split.setStretchFactor(1, 1)
        split.setSizes([360, 300])        # the timeline's size hint otherwise takes most of the height
        split.setChildrenCollapsible(False)
        layout.addWidget(split, 1)

        # One row: add things, change the selection, then the export the editor exists for.
        add_actions = QHBoxLayout()
        add_actions.addWidget(MenuButton("Add", [
            ("Saved sound\u2026", self.add_sound),
            ("Latest Speech take", self.add_latest_take),
            ("Narration file\u2026", lambda: self.add_voice_take()),
            ("Narration script\u2026", self.add_text_block),
            None,
            ("Empty track\u2026", self.add_track),
        ]))
        self._button(add_actions, "Edit\u2026", self.edit_selected)
        self.narrate_button = self._button(add_actions, "Generate narration", self.generate_narration)
        self.narrate_button.setToolTip("Render the selected narration script with the voice and settings "
                                       "chosen in Create, and put the take on that clip.")
        add_actions.addWidget(MenuButton("Selection", [
            ("Mute / unmute track", self.toggle_track_mute),
            ("Edit narration script\u2026", self.edit_narration),
            ("Move track up", lambda: self.move_track(-1)),
            ("Move track down", lambda: self.move_track(1)),
            None,
            ("Remove\u2026", self.remove_selected),
        ]))
        add_actions.addStretch()
        self.cancel_button = self._button(add_actions, "Cancel export", self.cancel_export)
        self.cancel_button.setEnabled(False)
        self.cancel_button.setVisible(False)
        self.export_button = set_role(self._button(add_actions, "Export mix\u2026", self.export), "primary")
        self.export_button.setToolTip("A mastered mix (WAV, plus MP3/OGG if you like) and one stem per track, "
                                      "in a new folder.")
        layout.addLayout(add_actions)

        self.note = QLabel("Narration scripts need audio before export: select a script and use Generate "
                           "narration (it speaks with the voice chosen on Speech), or make it on Speech and use "
                           "Add › Latest Speech take with the script selected.")
        self.note.setObjectName("Muted")
        self.note.setWordWrap(True)
        layout.addWidget(self.note)

        self.refresh()

    @staticmethod
    def _button(row, label, callback):
        button = QPushButton(label)
        button.clicked.connect(callback)
        row.addWidget(button)
        return button

    def _error(self, exc):
        QMessageBox.warning(self, "Project", describe_error(exc, self.session.project))

    def is_dirty(self):
        return self.session.project.revision != self.baseline_revision

    def _mark_clean(self):
        self.saved_revision = self.session.project.revision
        self.baseline_revision = self.session.project.revision

    def _clip_label(self, clip):
        if clip.kind == "sound" and clip.asset_id:
            asset = self.owner.sound_library.get(clip.asset_id[len("sound_"):])
            return asset.name if asset is not None else "Missing sound"
        if clip.text:
            return clip.text if len(clip.text) <= 55 else clip.text[:54] + "\u2026"
        return "Narration take" if clip.kind == "voice" else "Clip"

    @staticmethod
    def _clip_source(clip):
        if not clip.asset_id:
            return "Script only \u2014 needs audio"
        return "Sound library" if clip.asset_id.startswith("sound_") else "Narration take"

    def refresh(self, selected=None):
        project = self.session.project
        if self.is_dirty():
            state = "Unsaved changes"
        elif self.session.path is not None:
            state = f"Saved \u00b7 {self.session.path.name}"
        else:
            state = "New project"
        self.title_label.setText(project.title)
        self.heading.setText(f"Studio · {state}" if self.embedded else state)
        self.undo_button.setEnabled(self.session.can_undo)
        self.redo_button.setEnabled(self.session.can_redo)
        self.timeline.set_project(project)
        self._request_peaks()
        self.tree.clear()
        for track in project.tracks:
            row = QTreeWidgetItem([f"{track.name} ({track.kind})" + (" [muted]" if track.muted else ""),
                                   "", "", f"{track.gain_db:+.1f} dB", ""])
            row.setData(0, Qt.ItemDataRole.UserRole, ("track", track.id))
            self.tree.addTopLevelItem(row)
            for clip in track.clips:
                length = f"{clip.frame_count / project.sample_rate:.3f} s" + ("  (loops)" if clip.loop else "")
                item = QTreeWidgetItem([
                    self._clip_label(clip),
                    f"{clip.start_frame / project.sample_rate:.3f} s",
                    length if clip.asset_id else "\u2014",
                    f"{clip.gain_db:+.1f} dB", self._clip_source(clip),
                ])
                item.setToolTip(4, clip.asset_id or "Select it and use Generate narration, or attach a Speech take.")
                item.setData(0, Qt.ItemDataRole.UserRole, ("clip", clip.id))
                row.addChild(item)
                if selected == clip.id:
                    self.tree.setCurrentItem(item)
            row.setExpanded(True)
            if selected == track.id:
                self.tree.setCurrentItem(row)

    # ---- timeline ----
    def _select_clip_in_tree(self, clip_id):
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            for j in range(top.childCount()):
                item = top.child(j)
                if item.data(0, Qt.ItemDataRole.UserRole) == ("clip", clip_id):
                    self.tree.setCurrentItem(item)
                    return

    def _clip_placed(self, clip_id, start, count, offset):
        """A drag on the timeline finished: one undoable edit (scripts can only move)."""
        clip = next((c for t in self.session.project.tracks for c in t.clips if c.id == clip_id), None)
        if clip is None:
            return
        if clip.asset_id:
            change = lambda: self.session.place_clip(clip_id, start, count, offset)
        else:
            change = lambda: self.session.update_clip(clip_id, start_frame=start)
        if self._mutate(change, clip_id):
            rate = self.session.project.sample_rate
            if clip.asset_id:
                self.note.setText(f"Clip now starts at {start / rate:.2f} s and runs {count / rate:.2f} s. "
                                  "Undo puts it back; the source audio is unchanged.")
            else:
                self.note.setText(f"Script moved to {start / rate:.2f} s. Undo puts it back.")

    def _tree_selection_changed(self, current, _previous):
        data = current.data(0, Qt.ItemDataRole.UserRole) if current else None
        self.timeline.set_selected(data[1] if data and data[0] == "clip" else None)

    def _request_peaks(self):
        """Waveforms for clips that have audio, computed off the UI thread, once per asset."""
        if self.peak_worker is not None:
            return
        wanted = sorted({clip.asset_id for track in self.session.project.tracks for clip in track.clips
                         if clip.asset_id and clip.asset_id not in self.timeline.peaks})
        if not wanted:
            return
        media = self.media

        def compute():
            found = {}
            for asset_id in wanted:
                try:
                    pcm, rate = media.resolve(asset_id)
                    found[asset_id] = (envelope(pcm, rate), (len(pcm), rate))   # length: the trim limit
                except Exception:
                    found[asset_id] = None          # missing media: the block stays plain
            return found
        self.peak_worker = TaskThread(compute, self)
        self.peak_worker.done.connect(self._peaks_done)
        self.peak_worker.finished.connect(self._peaks_finished)
        self.peak_worker.finished.connect(self.peak_worker.deleteLater)
        self.peak_worker.start()

    @Slot(object, str)
    def _peaks_done(self, result, _error):
        for asset_id, found in (result or {}).items():
            if found is not None:
                peaks, length = found
                self.timeline.set_peaks(asset_id, peaks, length)

    @Slot()
    def _peaks_finished(self):
        self.peak_worker = None
        self._request_peaks()          # anything added meanwhile

    def play_preview(self):
        if self.preview_worker is not None:
            return
        if not any(clip.asset_id for track in self.session.project.tracks for clip in track.clips):
            QMessageBox.information(self, "Play mix", "Add a sound or a narration take first.")
            return
        if self.preview_file and self.preview_revision == self.session.project.revision:
            self.player.play()
            return
        snapshot = deepcopy(self.session.project)
        media = self.media
        folder = tempfile.mkdtemp(prefix="sonicrift_preview_")

        def render():
            audio, rate = preview_mix(snapshot, media)
            path = os.path.join(folder, "preview.wav")
            sf.write(path, audio, rate, subtype="PCM_16")
            return path, snapshot.revision
        self.play_button.setEnabled(False)
        self.note.setText("Preparing the mix to play\u2026")
        self.preview_worker = TaskThread(render, self)
        self.preview_worker.done.connect(self._preview_ready)
        self.preview_worker.finished.connect(self._preview_finished)
        self.preview_worker.finished.connect(self.preview_worker.deleteLater)
        self.preview_worker.start()

    @Slot(object, str)
    def _preview_ready(self, result, error):
        if error:
            self.note.setText("The mix couldn't be prepared for playback.")
            self._error(error)
            return
        path, revision = result
        self.player.stop()
        self.preview_file, self.preview_revision = path, revision
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()
        self.note.setText("Playing the arranged mix (not mastered). Export makes the final file.")

    @Slot()
    def _preview_finished(self):
        self.preview_worker = None
        self.play_button.setEnabled(True)

    def stop_preview(self):
        self.player.stop()

    def _seek_preview(self, seconds):
        if self.preview_file and self.preview_revision == self.session.project.revision:
            self.player.setPosition(int(seconds * 1000))
            if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                self.player.play()
        else:
            self.timeline.set_playhead(seconds)
            self.position_label.setText(seconds_label(seconds))

    def _on_preview_position(self, milliseconds):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
            return
        self.timeline.set_playhead(milliseconds / 1000)
        self.position_label.setText(seconds_label(milliseconds / 1000))

    def _on_preview_state(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.stop_button.setEnabled(playing)
        self.play_button.setText("Playing\u2026" if playing else "Play mix")
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.timeline.set_playhead(None)
            self.position_label.setText("0:00.0")

    def _selected(self):
        item = self.tree.currentItem()
        return item.data(0, Qt.ItemDataRole.UserRole) if item else None

    def _mutate(self, function, selected=None):
        try:
            function()
            self.refresh(selected)
            return True
        except Exception as exc:
            self._error(exc)
            return False

    def _confirm_discard(self):
        if not self.is_dirty():
            return True
        answer = QMessageBox.question(
            self, "Unsaved project", "Discard unsaved project edits?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def new_project(self):
        if not self._confirm_discard():
            return
        title, ok = QInputDialog.getText(self, "New project", "Project title")
        if ok and title.strip():
            self.session = ProjectSession(AudioProject(new_id(), title.strip()))
            self.session_serial += 1
            self.saved_revision = None
            self.baseline_revision = self.session.project.revision
            self.refresh()

    def open_project(self):
        if not self._confirm_discard():
            return
        filename, _ = QFileDialog.getOpenFileName(self, "Open project", self.owner.script_dir,
                                                 "Sonic Rift projects (*.sonicrift.json)")
        if filename:
            try:
                self.session = ProjectSession.open(filename)
                self.session_serial += 1
                self._mark_clean()
                self.refresh()
            except Exception as exc:
                self._error(exc)

    def save_project(self):
        path = self.session.path
        if path is None:
            name, _ = QFileDialog.getSaveFileName(
                self, "Save project", os.path.join(self.owner.script_dir, "Untitled.sonicrift.json"),
                "Sonic Rift projects (*.sonicrift.json)")
            if not name:
                return False
            path = Path(name)
            if not str(path).endswith(".sonicrift.json"):
                path = Path(str(path) + ".sonicrift.json")
        try:
            self.session.save(path)
            self._mark_clean()
            self.refresh()
            return True
        except Exception as exc:
            self._error(exc)
            return False

    def rename_project(self):
        title, ok = QInputDialog.getText(self, "Rename project", "Title",
                                         text=self.session.project.title)
        if ok and title.strip():
            self._mutate(lambda: self.session.apply(lambda p: setattr(p, "title", title.strip())))

    def undo(self):
        self._mutate(self.session.undo)

    def redo(self):
        self._mutate(self.session.redo)

    def add_track(self):
        kind, ok = QInputDialog.getItem(self, "Track", "Type", ["voice", "sound", "effect"], 0, False)
        if not ok:
            return
        name, ok = QInputDialog.getText(self, "Track", "Name", text=kind.capitalize())
        if ok and name.strip():
            self._mutate(lambda: self.session.add_track(kind, name.strip()))

    def add_sound(self, asset=None):
        """Add a kept sound; with no `asset`, pick one (Sounds' Add to Studio passes it)."""
        if self.import_worker is not None or self.worker is not None:
            QMessageBox.information(self, "Project", "Finish the current media operation first.")
            return
        if asset is None:
            assets = self.owner.sound_library.assets
            if not assets:
                QMessageBox.information(self, "Sounds", "Keep a sound on the Sounds page first.")
                return
            # Names only (no internal ids); a repeated name gets a number.
            labels, seen = [], {}
            for a in assets:
                seen[a.name] = seen.get(a.name, 0) + 1
                labels.append(a.name if seen[a.name] == 1 else f"{a.name} ({seen[a.name]})")
            label, ok = QInputDialog.getItem(self, "Add saved sound", "Sound", labels, 0, False)
            if not ok:
                return
            asset = assets[labels.index(label)]
        selection = self._selected()
        project_id = self.session.project.id
        revision = self.session.project.revision
        sample_rate = self.session.project.sample_rate
        media = self.media
        def resolve_sound():
            pcm, source_rate = media.resolve("sound_" + asset.id)
            frames = math.ceil(len(pcm) * sample_rate / source_rate)
            return asset.id, asset.name, asset.loop, frames
        self._pending_import = ("sound", selection, project_id, revision, self.session_serial)
        self.import_worker = TaskThread(resolve_sound, self)
        self.import_worker.done.connect(self._import_done)
        self.import_worker.finished.connect(self._voice_import_finished)
        self.import_worker.finished.connect(self.import_worker.deleteLater)
        self.note.setText("Verifying saved sound in the background.")
        self.import_worker.start()

    @Slot(object, str)
    def _import_done(self, result, error):
        """Dispatch worker results to Qt's UI thread through a bound QObject slot."""
        if self._pending_import is None:
            return
        kind, selection, project_id, revision, serial = self._pending_import
        if serial != self.session_serial:
            self.note.setText("A different project was opened during the import, so nothing was attached.")
            return
        if kind == "sound":
            self._sound_import_done(result, error, selection, project_id, revision)
        else:
            self._voice_import_done(result, error, selection, project_id, revision)

    def _sound_import_done(self, result, error, selection, project_id, revision):
        if error:
            self.note.setText("Sound import failed; no project edits were made.")
            self._error(error)
            return
        if not may_attach_import_result(self.session.project, project_id, revision):
            self.note.setText("Project changed while verifying sound. Re-select the sound to attach it.")
            return
        asset_id, name, loop, frames = result
        clip = Clip(new_id(), "sound", 0, frames, asset_id="sound_" + asset_id, loop=loop)
        selected_track_id = self._track_for_selection(selection, "sound")
        def change(project):
            from this_voice_thing.core.audio_project import Track
            track = next((track for track in project.tracks if track.id == selected_track_id), None)
            if track is None:
                project.tracks.append(Track(new_id(), "sound", name, clips=[clip]))
            else:
                track.clips.append(clip)
        if self._mutate(lambda: self.session.apply(change), clip.id):
            self.note.setText("Saved sound attached. Save the project to keep the new clip.")
        else:
            self.note.setText("Sound verification passed, but the project edit was rejected.")

    def _track_for_selection(self, selection, kind):
        return compatible_track_id(self.session.project, selection, kind)

    def add_text_block(self):
        text, ok = QInputDialog.getMultiLineText(
            self, "New narration", "Narration text",
            self.owner.text_input.toPlainText().strip())
        if not ok:
            return
        text = text.strip()
        if not text:
            QMessageBox.information(self, "Narration", "Enter narration text first.")
            return
        clip = Clip(new_id(), "voice", 0, 0, text=text,
                    voice_id=self.owner.active_voice_id or "")
        selected_track_id = self._track_for_selection(self._selected(), "voice")
        def change(project):
            from this_voice_thing.core.audio_project import Track
            track = next((track for track in project.tracks if track.id == selected_track_id), None)
            if track is None:
                project.tracks.append(Track(new_id(), "voice", "Narration", clips=[clip]))
            else:
                track.clips.append(clip)
        self._mutate(lambda: self.session.apply(change))

    def add_latest_take(self):
        """Attach the take Speech made most recently (to the selected script clip, if any)."""
        latest = self.owner.current_audio_file
        if not latest or not os.path.isfile(latest):
            QMessageBox.information(self, "Narration", "Generate narration in Create first. This editor "
                                    "can stay open while you do.")
            return
        self.add_voice_take(latest, text=getattr(self.owner, "take_texts", {}).get(os.path.abspath(latest), ""))

    def add_voice_take(self, filename=None, text=""):
        """Import a narration take. `text`: what it says (from Speech), shown on its clip."""
        self._pending_take_text = text if isinstance(text, str) else ""
        self._add_voice_take(filename)

    def _add_voice_take(self, filename=None):
        if self.import_worker is not None or self.worker is not None:
            QMessageBox.information(self, "Project", "Finish the current media operation first.")
            return
        if not filename:
            initial = self.owner.current_audio_file or self.owner.output_directory
            filename, _ = QFileDialog.getOpenFileName(self, "Import rendered narration", initial,
                                                     "Audio files (*.wav *.flac *.ogg *.mp3)")
        if not filename:
            return
        selection = self._selected()
        project_id = self.session.project.id
        revision = self.session.project.revision
        project_rate = self.session.project.sample_rate
        media = self.media
        def import_file():
            info = sf.info(filename)
            if info.duration > 900 or info.channels not in (1, 2):
                raise ValueError("Narration must be mono/stereo and no longer than 15 minutes")
            pcm, sr = sf.read(filename, dtype="float32", always_2d=True)
            asset_id = media.import_voice_take(pcm, sr)
            frames = math.ceil(len(pcm) * project_rate / sr)
            return asset_id, frames, filename
        self._pending_import = ("voice", selection, project_id, revision, self.session_serial)
        self.import_worker = TaskThread(import_file, self)
        self.import_worker.done.connect(self._import_done)
        self.import_worker.finished.connect(self._voice_import_finished)
        self.import_worker.finished.connect(self.import_worker.deleteLater)
        self.note.setText("Importing narration in the background. Source files are not modified.")
        self.import_worker.start()

    def _voice_import_done(self, result, error, selection, project_id, revision):
        if error:
            self.note.setText("Narration import failed; no project edits were made.")
            self._error(error)
            return
        if not may_attach_import_result(self.session.project, project_id, revision):
            self.note.setText("Project changed during import. Re-select the narration take to attach it.")
            return
        asset_id, frames, filename = result
        existing = next((clip for track in self.session.project.tracks for clip in track.clips
                         if selection == ("clip", clip.id) and clip.kind == "voice"), None)
        if existing is not None:
            applied = self._mutate(lambda: self.session.attach_narration_take(
                existing.id, asset_id, frames), existing.id)
        else:
            clip = Clip(new_id(), "voice", 0, frames, asset_id=asset_id,
                        text=getattr(self, "_pending_take_text", "").strip())
            selected_track_id = self._track_for_selection(selection, "voice")
            if selected_track_id is None:
                # Nothing (or something else) selected: the narration track, not a new track per take.
                selected_track_id = next((t.id for t in self.session.project.tracks if t.kind == "voice"), None)
            gap = self.session.project.sample_rate          # one second after the last line
            def change(project):
                from this_voice_thing.core.audio_project import Track
                track = next((track for track in project.tracks if track.id == selected_track_id), None)
                if track is None:
                    project.tracks.append(Track(new_id(), "voice", "Narration", clips=[clip]))
                else:
                    if track.clips:     # after what's there, instead of on top of it at 0:00
                        clip.start_frame = max(c.start_frame + c.frame_count for c in track.clips) + gap
                    track.clips.append(clip)
            applied = self._mutate(lambda: self.session.apply(change))
        if applied:
            self.note.setText("Narration imported. Save the project to keep the new clip.")
        else:
            self.note.setText("Narration was saved, but could not be attached to this clip.")

    @Slot()
    def _voice_import_finished(self):
        self.import_worker = None
        self._pending_import = None

    # ---- narration rendered in place ----
    def _selected_script(self):
        selection = self._selected()
        if not selection or selection[0] != "clip":
            return None
        return next((c for t in self.session.project.tracks for c in t.clips
                     if c.id == selection[1] and c.kind == "voice" and c.text.strip()), None)

    def generate_narration(self):
        """Render the selected script and attach the take to that clip (one undoable edit).

        The model works in the background; the project stays editable. The take is attached
        only if that clip still has the same script and take when it finishes."""
        if self.narration_job is not None:
            self.cancel_narration()
            return
        clip = self._selected_script()
        if clip is None:
            QMessageBox.information(self, "Narration", "Select a narration script (a voice clip with text) "
                                    "first. Add \u203a Narration script\u2026 makes one.")
            return
        if clip.asset_id:
            answer = QMessageBox.question(
                self, "Replace take",
                "This clip already has a take. Generate a new one and use it instead? The current take "
                "stays in project media, and Undo puts it back.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        problem = self.owner.narration_generation_problem(clip.voice_id)
        if problem:
            QMessageBox.information(self, "Narration", problem)
            return
        try:
            thread = self.owner.narration_generator(
                clip.text, os.path.join(self.owner.output_directory, "project_narration"))
        except Exception as exc:
            QMessageBox.information(self, "Narration", str(exc))
            return
        self.narration_job = {
            "thread": thread, "import": None, "cancelled": False, "serial": self.session_serial,
            "project_id": self.session.project.id, "clip_id": clip.id, "text": clip.text,
            "previous_asset_id": clip.asset_id,
        }
        thread.generation_complete.connect(self._narration_rendered)
        thread.error_occurred.connect(self._narration_failed)
        thread.chunk_generated.connect(self._narration_progress)
        thread.finished.connect(self._narration_thread_finished)
        self.owner.begin_editor_generation()
        thread.start()
        self.narrate_button.setText("Cancel narration")
        self.note.setText(f"Generating narration for \u201c{self._clip_label(clip)}\u201d with the voice chosen "
                          "in Create. You can keep editing; Cancel narration stops it.")

    def cancel_narration(self):
        job = self.narration_job
        if job is None:
            return
        job["cancelled"] = True
        if job["thread"] is not None:
            job["thread"].stop()
            self.narrate_button.setEnabled(False)
            self.narrate_button.setText("Stopping\u2026")
            self.note.setText("Stopping after the section in progress. Nothing will be attached.")

    @Slot(int, int, int)
    def _narration_progress(self, _first, last, total):
        if self.narration_job is not None and not self.narration_job["cancelled"] and total > 1:
            self.note.setText(f"Generating narration: {last} of {total} sections done. "
                              "You can keep editing; Cancel narration stops it.")

    @Slot(str, int)
    def _narration_rendered(self, output_path, _sample_rate):
        job = self.narration_job
        if job is None:
            return
        thread = job["thread"]
        if job["cancelled"] or (thread is not None and thread.partial_info):
            job["cancelled"] = True
            self.note.setText("Narration cancelled. Nothing was attached.")
            return
        project_rate = self.session.project.sample_rate
        media = self.media

        def import_take():
            info = sf.info(output_path)
            if info.duration > 900 or info.channels not in (1, 2):
                raise ValueError("Narration must be mono/stereo and no longer than 15 minutes")
            pcm, sr = sf.read(output_path, dtype="float32", always_2d=True)
            return media.import_voice_take(pcm, sr), math.ceil(len(pcm) * project_rate / sr), project_rate
        worker = TaskThread(import_take, self)
        job["import"] = worker
        worker.done.connect(self._narration_imported)
        worker.finished.connect(self._narration_import_finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    @Slot(object, str)
    def _narration_imported(self, result, error):
        job = self.narration_job
        if job is None or job["cancelled"]:
            return
        if error:
            self.note.setText("The narration was generated but couldn't be imported; no project edits were made.")
            QMessageBox.warning(self, "Narration", describe_error(error, self.session.project))
            return
        if job["serial"] != self.session_serial:
            self.note.setText("A different project was opened while it was generating, so the new take "
                              "wasn't attached.")
            return
        clip, reason = generated_take_target(self.session.project, job["project_id"], job["clip_id"],
                                             job["text"], job["previous_asset_id"])
        asset_id, frames, rate = result
        if clip is None or rate != self.session.project.sample_rate:
            self.note.setText(reason or "The project's sample rate changed, so the new take wasn't attached.")
            return
        if self._mutate(lambda: self.session.attach_narration_take(clip.id, asset_id, frames), clip.id):
            self.note.setText("Narration generated and placed on its clip. Undo removes it; save the project "
                              "to keep it.")

    @Slot(str)
    def _narration_failed(self, message):
        job = self.narration_job
        if job is None:
            return
        if job["cancelled"] or "stopped" in message.lower():
            job["cancelled"] = True
            self.note.setText("Narration cancelled. Nothing was attached.")
            return
        self.note.setText("Narration generation failed; no project edits were made.")
        QMessageBox.warning(self, "Narration", message)

    @Slot()
    def _narration_thread_finished(self):
        job = self.narration_job
        if job is None:
            return
        thread, job["thread"] = job["thread"], None
        if thread is not None:
            thread.deleteLater()
        self.owner.end_editor_generation()      # the model is free; importing doesn't need it
        if job["import"] is None:
            self._narration_done()

    @Slot()
    def _narration_import_finished(self):
        job = self.narration_job
        if job is not None:
            job["import"] = None
            if job["thread"] is None:
                self._narration_done()

    def _narration_done(self):
        self.narration_job = None
        self.narrate_button.setEnabled(True)
        self.narrate_button.setText("Generate narration")

    def remove_selected(self):
        selection = self._selected()
        if not selection:
            return
        kind, identifier = selection
        if QMessageBox.question(self, "Remove item", "Remove selected item from the project? "
                                "Stored source media will not be deleted.") != QMessageBox.StandardButton.Yes:
            return
        function = (lambda: self.session.remove_track(identifier)) if kind == "track" else (
            lambda: self.session.remove_clip(identifier))
        self._mutate(function)

    def toggle_track_mute(self):
        selection = self._selected()
        if not selection:
            return
        track_id = self._track_for_selection(selection, "voice")
        if track_id is None:
            track_id = self._track_for_selection(selection, "sound")
        if track_id is None:
            track_id = self._track_for_selection(selection, "effect")
        if track_id is None:
            return
        track = next(t for t in self.session.project.tracks if t.id == track_id)
        self._mutate(lambda: self.session.update_track(track_id, muted=not track.muted), track_id)

    def move_track(self, offset):
        selection = self._selected()
        if not selection or selection[0] != "track":
            return
        track_id = selection[1]
        index = next(i for i, t in enumerate(self.session.project.tracks) if t.id == track_id)
        if not 0 <= index + offset < len(self.session.project.tracks):
            return
        self._mutate(lambda: self.session.move_track(track_id, index + offset), track_id)

    def edit_narration(self):
        selection = self._selected()
        if not selection or selection[0] != "clip":
            QMessageBox.information(self, "Narration", "Select a voice clip to edit its script.")
            return
        clip_id = selection[1]
        clip = next((c for t in self.session.project.tracks for c in t.clips if c.id == clip_id), None)
        if clip is None or clip.kind != "voice":
            QMessageBox.information(self, "Narration", "Select a voice clip to edit its script.")
            return
        text, ok = QInputDialog.getMultiLineText(
            self, "Edit narration", "Script", clip.text)
        if not ok or text.strip() == clip.text:
            return
        if clip.asset_id:
            answer = QMessageBox.question(
                self, "Rendered audio",
                "Changing the script will detach the previous rendered take from this clip. "
                "The saved audio will not be deleted. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._mutate(lambda: self.session.update_narration_text(clip.id, text), clip.id)

    def edit_selected(self):
        selection = self._selected()
        if not selection:
            return
        kind, identifier = selection
        if kind == "track":
            track = next(t for t in self.session.project.tracks if t.id == identifier)
            name, ok = QInputDialog.getText(self, "Track name", "Name", text=track.name)
            if not ok or not name.strip():
                return
            gain, ok = QInputDialog.getDouble(self, "Track gain", "Gain (dB)",
                                               track.gain_db, -60, 24, 2)
            if not ok:
                return
            self._mutate(lambda: self.session.update_track(
                identifier, name=name.strip(), gain_db=gain), identifier)
            return
        clip = next(c for t in self.session.project.tracks for c in t.clips if c.id == identifier)
        rate = self.session.project.sample_rate
        dialog = QDialog(self)
        dialog.setWindowTitle("Clip properties")
        form = QFormLayout(dialog)
        def spin(label, value, low, high):
            control = QDoubleSpinBox()
            # Six decimal places preserve 44.1/48 kHz frame boundaries on save.
            # Millisecond rounding silently changes clip positions during edits.
            control.setDecimals(6)
            control.setRange(low, high)
            control.setValue(value)
            form.addRow(label, control)
            return control
        start = spin("Start (seconds)", clip.start_frame / rate, 0, 36000)
        duration = spin("Duration (seconds)", clip.frame_count / rate, 0, 36000)
        duration.setEnabled(bool(clip.asset_id))
        gain = spin("Gain (dB)", clip.gain_db, -60, 24)
        fade_in = spin("Fade in (seconds)", clip.fade_in_frames / rate, 0, 36000)
        fade_out = spin("Fade out (seconds)", clip.fade_out_frames / rate, 0, 36000)
        for control in (fade_in, fade_out):
            control.setEnabled(bool(clip.asset_id))   # a script-only clip has no audio to fade yet
        loop = QCheckBox("Repeat sound as needed")
        loop.setChecked(clip.loop)
        loop.setEnabled(clip.kind == "sound")
        form.addRow(loop)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        offset = clip.source_offset_frames
        if clip.loop and not loop.isChecked() and offset:
            # A looping clip's trimmed start may wrap past the end of its audio; without looping
            # it must sit inside the audio, at the same point in the sound.
            source = self.timeline.source_frames(clip.asset_id)
            offset = offset % source if source else 0
        params = {
            "source_offset_frames": offset,
            "start_frame": round(start.value() * rate),
            "frame_count": round(duration.value() * rate),
            "gain_db": gain.value(),
            "fade_in_frames": round(fade_in.value() * rate),
            "fade_out_frames": round(fade_out.value() * rate),
            "loop": loop.isChecked(),
        }
        self._mutate(lambda: self.session.update_clip(identifier, **params), identifier)

    def export(self):
        if self.worker is not None or self.import_worker is not None:
            return
        if (self.is_dirty() or self.session.path is None) and not self.save_project():
            return
        try:
            self.session.ensure_current_file()
        except (OSError, ValueError) as exc:
            self._error(exc)
            return
        parent = QFileDialog.getExistingDirectory(self, "Choose export location",
                                                  self.owner.output_directory)
        if not parent:
            return
        profile, ok = QInputDialog.getItem(
            self, "Export formats", "Master format",
            ["WAV", "WAV + MP3", "WAV + OGG", "WAV + MP3 + OGG"], 0, False)
        if not ok:
            return
        formats = tuple(fmt for fmt in ("wav", "mp3", "ogg") if fmt.upper() in profile)
        label, ok = QInputDialog.getText(self, "Export folder", "New folder name",
                                         text="SonicRift_Mix")
        if not ok:
            return
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _-]{0,63}", label):
            self._error(ValueError("Use a simple, new folder name (letters, numbers, spaces, - or _)"))
            return
        destination = Path(parent) / label
        # A file chooser may be open while another process edits the project.
        # Recheck immediately before freezing the export snapshot.
        try:
            self.session.ensure_current_file()
        except (OSError, ValueError) as exc:
            self._error(exc)
            return
        snapshot = deepcopy(self.session.project)
        media = self.media
        self.export_button.setEnabled(False)
        self.export_cancel = Event()
        self.cancel_button.setEnabled(True)
        self.cancel_button.setVisible(True)
        should_cancel = self.export_cancel.is_set
        self.worker = TaskThread(lambda: export_project(snapshot, media, destination, formats=formats,
                                                        include_stems=True, should_cancel=should_cancel), self)
        self.worker.done.connect(self._export_done)
        self.worker.finished.connect(self._export_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.note.setText("Exporting the mix and one stem per track… You can keep using the other pages.")
        self.worker.start()

    def cancel_export(self):
        if self.worker is not None and self.export_cancel is not None:
            self.export_cancel.set()
            self.note.setText("Cancellation requested. Cleaning up after the current rendering stage.")

    @Slot(object, str)
    def _export_done(self, result, error):
        if error == "Project export cancelled":
            self.note.setText(describe_error(error))
        elif error:
            self.note.setText("Export failed. Source files were not modified.")
            self._error(error)
        else:
            folder = Path(result).parent
            # The folder's name, not its whole path (which carries the user's home folder); the
            # full path is in the tooltip and the dialog.
            self.note.setText(f"Export complete: “{folder.name}” — the master, one stem per track "
                              "and a manifest.")
            self.note.setToolTip(str(folder))
            QMessageBox.information(self, "Project exported",
                                    f"Master WAV, premaster stems and manifest saved to:\n{Path(result).parent}")

    @Slot()
    def _export_finished(self):
        self.worker = None
        self.export_cancel = None
        self.cancel_button.setEnabled(False)
        self.cancel_button.setVisible(False)
        self.export_button.setEnabled(True)

    def _finish_quick_jobs(self):
        """Peaks and the preview render only read media; let them finish before closing."""
        self.player.stop()
        for job in (self.peak_worker, self.preview_worker):
            if job is not None:
                job.wait(10000)

    def keyPressEvent(self, event):
        if self.embedded and event.key() == Qt.Key.Key_Escape:
            event.ignore()          # a page doesn't close on Esc
            return
        super().keyPressEvent(event)

    def _narration_running(self):
        if self.narration_job is None:
            return False
        QMessageBox.information(self, "Project", "Narration is still generating. Use Cancel narration, "
                                "then close this editor.")
        return True

    def reject(self):
        if self._narration_running():
            return
        if self.worker is not None or self.import_worker is not None:
            QMessageBox.information(self, "Project", "Finish the media operation before closing this editor.")
            return
        if self._confirm_discard():
            self._finish_quick_jobs()
            super().reject()

    def closeEvent(self, event):
        if self._narration_running():
            event.ignore()
            return
        if self.worker is not None or self.import_worker is not None:
            QMessageBox.information(self, "Project", "Finish the media operation before closing this editor.")
            event.ignore()
            return
        if self._confirm_discard():
            self._finish_quick_jobs()
            QDialog.reject(self)   # finished(): the owner drops its reference (no second prompt)
            event.accept()
        else:
            event.ignore()
