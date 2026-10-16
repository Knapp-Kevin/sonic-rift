"""Opt-in project editor for Create; legacy single-text generation stays intact.

First usable list-based track editor, not yet a graphical drag-and-drop timeline.
Qt widgets only hold inputs; versioned project state lives in ProjectSession.
"""
from copy import deepcopy
from threading import Event
import math
import os
from pathlib import Path
import re

import soundfile as sf

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
    QInputDialog, QLabel, QMessageBox, QPushButton, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QDialogButtonBox,
)

from this_voice_thing.core.audio_project import AudioProject, Clip, new_id
from this_voice_thing.core.audio_project_session import ProjectSession
from this_voice_thing.core.audio_project_media import ProjectMedia
from this_voice_thing.core.audio_project_export import export_project
from this_voice_thing.ui.threads import TaskThread


class ProjectEditorDialog(QDialog):
    """Save, arrange and export tracks without changing ordinary Create settings."""

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setWindowTitle("Sonic Rift | Create project")
        self.resize(850, 580)
        self.session = ProjectSession(AudioProject(new_id(), "Untitled project"))
        self.saved_revision = None
        self.worker = None
        self.export_cancel = None
        self.media = ProjectMedia(owner.script_dir, owner.sound_library)
        layout = QVBoxLayout(self)
        self.heading = QLabel()
        layout.addWidget(self.heading)
        file_actions = QHBoxLayout()
        self._button(file_actions, "New", self.new_project)
        self._button(file_actions, "Open…", self.open_project)
        self._button(file_actions, "Save", self.save_project)
        self._button(file_actions, "Rename", self.rename_project)
        file_actions.addStretch()
        self._button(file_actions, "Undo", self.undo)
        self._button(file_actions, "Redo", self.redo)
        layout.addLayout(file_actions)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Track / clip", "Starts", "Length", "Gain", "Source"])
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemDoubleClicked.connect(lambda *_: self.edit_selected())
        layout.addWidget(self.tree, 1)

        edit_actions = QHBoxLayout()
        self._button(edit_actions, "+ Track", self.add_track)
        self._button(edit_actions, "+ Saved sound", self.add_sound)
        self._button(edit_actions, "+ Create text", self.add_text_block)
        self._button(edit_actions, "+ / Attach narration", self.add_voice_take)
        self._button(edit_actions, "Edit…", self.edit_selected)
        self._button(edit_actions, "Remove", self.remove_selected)
        self._button(edit_actions, "↑", lambda: self.move_track(-1))
        self._button(edit_actions, "↓", lambda: self.move_track(1))
        layout.addLayout(edit_actions)

        self.note = QLabel("Save a project, then export a mastered mix and post-duck premaster WAV stems. "
                           "Text blocks need rendered narration attached before export; use Create to generate it.")
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        actions = QHBoxLayout()
        self.export_button = self._button(actions, "Export mastered mix + stems…", self.export)
        self.cancel_button = self._button(actions, "Cancel export", self.cancel_export)
        self.cancel_button.setEnabled(False)
        actions.addStretch()
        self.close_button = self._button(actions, "Close", self.reject)
        layout.addLayout(actions)
        self.refresh()

    @staticmethod
    def _button(row, label, callback):
        button = QPushButton(label)
        button.clicked.connect(callback)
        row.addWidget(button)
        return button

    def _error(self, exc):
        QMessageBox.warning(self, "Project", str(exc))

    def refresh(self, selected=None):
        project = self.session.project
        dirty = self.saved_revision is None or self.saved_revision != project.revision
        self.heading.setText(f"{project.title}  •  revision {project.revision}" +
                             ("  •  unsaved edits" if dirty else "  •  saved"))
        self.tree.clear()
        for track in project.tracks:
            row = QTreeWidgetItem([f"{track.name} ({track.kind})" + (" [muted]" if track.muted else ""),
                                   "", "", f"{track.gain_db:+.1f} dB", ""])
            row.setData(0, Qt.ItemDataRole.UserRole, ("track", track.id))
            self.tree.addTopLevelItem(row)
            for clip in track.clips:
                source = clip.asset_id or "(unrendered text)"
                item = QTreeWidgetItem([
                    clip.text[:55] if clip.text and not clip.asset_id else f"Clip {clip.id[:8]}",
                    f"{clip.start_frame / project.sample_rate:.3f}s",
                    f"{clip.frame_count / project.sample_rate:.3f}s",
                    f"{clip.gain_db:+.1f} dB", source,
                ])
                item.setData(0, Qt.ItemDataRole.UserRole, ("clip", clip.id))
                row.addChild(item)
                if selected == clip.id:
                    self.tree.setCurrentItem(item)
            row.setExpanded(True)
            if selected == track.id:
                self.tree.setCurrentItem(row)

    def _selected(self):
        item = self.tree.currentItem()
        return item.data(0, Qt.ItemDataRole.UserRole) if item else None

    def _mutate(self, function, selected=None):
        try:
            function()
            self.refresh(selected)
        except Exception as exc:
            self._error(exc)

    def _confirm_discard(self):
        if self.saved_revision is not None and self.saved_revision == self.session.project.revision:
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
            self.saved_revision = None
            self.refresh()

    def open_project(self):
        if not self._confirm_discard():
            return
        filename, _ = QFileDialog.getOpenFileName(self, "Open project", self.owner.script_dir,
                                                 "Sonic Rift projects (*.sonicrift.json)")
        if filename:
            try:
                self.session = ProjectSession.open(filename)
                self.saved_revision = self.session.project.revision
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
            self.saved_revision = self.session.project.revision
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

    def add_sound(self):
        assets = self.owner.sound_library.assets
        if not assets:
            QMessageBox.information(self, "Sounds", "Keep a sound on the Sounds page first.")
            return
        labels = [f"{a.name}  |  {a.id}" for a in assets]
        label, ok = QInputDialog.getItem(self, "Add saved sound", "Sound", labels, 0, False)
        if not ok:
            return
        asset = assets[labels.index(label)]
        try:
            pcm, source_rate = self.media.resolve("sound_" + asset.id)
            frames = math.ceil(len(pcm) * self.session.project.sample_rate / source_rate)
            clip = Clip(new_id(), "sound", 0, frames, asset_id="sound_" + asset.id, loop=asset.loop)
            selection = self._selected()
            selected_track_id = self._track_for_selection(selection, "sound")
            def change(project):
                from this_voice_thing.core.audio_project import Track
                track = next((track for track in project.tracks if track.id == selected_track_id), None)
                if track is None:
                    project.tracks.append(Track(new_id(), "sound", asset.name, clips=[clip]))
                else:
                    track.clips.append(clip)
            self._mutate(lambda: self.session.apply(change))
        except Exception as exc:
            self._error(exc)

    def _track_for_selection(self, selection, kind):
        """Return a selected compatible track ID, never a project file path."""
        if not selection:
            return None
        selected_kind, identifier = selection
        for track in self.session.project.tracks:
            if track.kind != kind:
                continue
            if selected_kind == "track" and track.id == identifier:
                return track.id
            if selected_kind == "clip" and any(clip.id == identifier for clip in track.clips):
                return track.id
        return None

    def add_text_block(self):
        text = self.owner.text_input.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Narration", "Enter text on Create first.")
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

    def add_voice_take(self):
        initial = self.owner.current_audio_file or self.owner.output_directory
        filename, _ = QFileDialog.getOpenFileName(self, "Import rendered narration", initial,
                                                 "Audio files (*.wav *.flac *.ogg *.mp3)")
        if not filename:
            return
        try:
            info = sf.info(filename)
            if info.duration > 900 or info.channels not in (1, 2):
                raise ValueError("Narration must be mono/stereo and no longer than 15 minutes")
            pcm, sr = sf.read(filename, dtype="float32", always_2d=True)
            asset_id = self.media.import_voice_take(pcm, sr)
            frames = math.ceil(len(pcm) * self.session.project.sample_rate / sr)
            selection = self._selected()
            existing = next((clip for track in self.session.project.tracks for clip in track.clips
                             if selection == ("clip", clip.id) and clip.kind == "voice"), None)
            if existing is not None:
                self._mutate(lambda: self.session.update_clip(
                    existing.id, asset_id=asset_id, frame_count=frames), existing.id)
            else:
                clip = Clip(new_id(), "voice", 0, frames, asset_id=asset_id)
                selected_track_id = self._track_for_selection(selection, "voice")
                def change(project):
                    from this_voice_thing.core.audio_project import Track
                    track = next((track for track in project.tracks if track.id == selected_track_id), None)
                    if track is None:
                        project.tracks.append(Track(new_id(), "voice", Path(filename).stem, clips=[clip]))
                    else:
                        track.clips.append(clip)
                self._mutate(lambda: self.session.apply(change))
        except Exception as exc:
            self._error(exc)

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

    def move_track(self, offset):
        selection = self._selected()
        if not selection or selection[0] != "track":
            return
        track_id = selection[1]
        index = next(i for i, t in enumerate(self.session.project.tracks) if t.id == track_id)
        self._mutate(lambda: self.session.move_track(track_id, index + offset), track_id)

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
                                               track.gain_db, -60, 24, 1)
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
        params = {
            "start_frame": round(start.value() * rate),
            "frame_count": round(duration.value() * rate),
            "gain_db": gain.value(),
            "fade_in_frames": round(fade_in.value() * rate),
            "fade_out_frames": round(fade_out.value() * rate),
            "loop": loop.isChecked(),
        }
        self._mutate(lambda: self.session.update_clip(identifier, **params), identifier)

    def export(self):
        if self.worker is not None:
            return
        if self.saved_revision != self.session.project.revision and not self.save_project():
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
        snapshot = deepcopy(self.session.project)
        media = self.media
        self.export_button.setEnabled(False)
        self.export_cancel = Event()
        self.cancel_button.setEnabled(True)
        should_cancel = self.export_cancel.is_set
        self.worker = TaskThread(lambda: export_project(snapshot, media, destination, formats=formats,
                                                        include_stems=True, should_cancel=should_cancel), self)
        self.worker.done.connect(self._export_done)
        self.worker.finished.connect(self._export_finished)
        self.note.setText("Exporting project. Keep this editor open until completion.")
        self.worker.start()

    def cancel_export(self):
        if self.worker is not None and self.export_cancel is not None:
            self.export_cancel.set()
            self.note.setText("Cancellation requested. Cleaning up after the current rendering stage.")

    def _export_done(self, result, error):
        if error:
            self.note.setText("Export failed. Source files were not modified.")
            self._error(error)
        else:
            self.note.setText(f"Export complete: {Path(result).parent}")
            QMessageBox.information(self, "Project exported",
                                    f"Master WAV, premaster stems and manifest saved to:\n{Path(result).parent}")

    def _export_finished(self):
        self.worker = None
        self.export_cancel = None
        self.cancel_button.setEnabled(False)
        self.export_button.setEnabled(True)

    def reject(self):
        if self.worker is not None:
            QMessageBox.information(self, "Project export", "Finish exporting before closing this editor.")
            return
        if self._confirm_discard():
            super().reject()

    def closeEvent(self, event):
        if self.worker is not None:
            event.ignore()
            return
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()
