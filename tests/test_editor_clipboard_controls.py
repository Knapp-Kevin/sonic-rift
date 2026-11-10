"""Studio clipboard UI actions: service-only mutations and guarded placement.

Qt is imported by the actual editor, but test actions use lightweight stand-ins;
the Windows offscreen GUI integration remains an independent release gate.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import Mock

from this_voice_thing.core.audio_project import AudioProject, Clip
from this_voice_thing.core.audio_project_session import ProjectSession
from this_voice_thing.ui.pages.project_editor import ProjectEditorDialog


class StudioClipboardActions(TestCase):
    def setUp(self):
        session = ProjectSession(AudioProject("p", "Clipboard UI"))
        track = session.add_track("sound", "Music")
        session.add_clip(track, Clip("first", "sound", 100, 500, asset_id="sound_first"))
        session.add_clip(track, Clip("second", "sound", 800, 300, asset_id="sound_second"))
        self.editor = SimpleNamespace(
            session=session,
            timeline=SimpleNamespace(playhead=1.5, selected_clips=["first", "second"]),
            _clip_clipboard=None, refresh=Mock(), _error=Mock(), note=Mock(),
            _selected_clip_ids=lambda: ("first", "second"),
        )

    def test_menu_shortcuts_and_multiselect_hooks_are_declared(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "this_voice_thing/ui/pages/project_editor.py").read_text(encoding="utf-8")
        timeline = (root / "this_voice_thing/ui/project_timeline.py").read_text(encoding="utf-8")
        self.assertIn('("Copy selected clips", self.copy_selected_clips)', source)
        self.assertIn('("Paste at playhead", self.paste_copied_clips)', source)
        for key in ("StandardKey.Copy", "StandardKey.Paste", '"Ctrl+D"', '"Ctrl+E"'):
            self.assertIn(key, source)
        self.assertIn("clipsSelectionChanged = Signal(object)", timeline)
        self.assertIn("self.timeline.clipsSelectionChanged.connect(self._sync_tree_clip_selection)", source)
        self.assertIn("SelectionMode.ExtendedSelection", source)

    def test_copy_and_paste_at_playhead_single_undo(self):
        e = self.editor
        original_revision = e.session.project.revision
        ProjectEditorDialog.copy_selected_clips(e)
        self.assertIsNotNone(e._clip_clipboard)
        self.assertEqual(e.session.project.revision, original_revision)
        ProjectEditorDialog.paste_copied_clips(e)
        clips = e.session.project.tracks[0].clips
        self.assertEqual(len(clips), 4)
        self.assertEqual((clips[2].start_frame, clips[3].start_frame),
                         (72000, 72700))
        self.assertEqual(e.session.project.revision, original_revision + 1)
        self.assertEqual([c.asset_id for c in clips[2:]], ["sound_first", "sound_second"])
        e.refresh.assert_called_once_with(clips[-1].id)
        e._error.assert_not_called()
        self.assertTrue(e.session.undo())
        self.assertEqual(len(e.session.project.tracks[0].clips), 2)

    def test_no_copy_or_no_playhead_does_not_change_document(self):
        e = self.editor
        rev = e.session.project.revision
        ProjectEditorDialog.paste_copied_clips(e)
        self.assertEqual(e.session.project.revision, rev)
        e.refresh.assert_not_called()
        ProjectEditorDialog.copy_selected_clips(e)
        e.timeline.playhead = None
        ProjectEditorDialog.paste_copied_clips(e)
        self.assertEqual(e.session.project.revision, rev)
        e.refresh.assert_not_called()
        e._error.assert_not_called()

    def test_copy_requires_selection_and_source(self):
        e = self.editor
        e._selected_clip_ids = lambda: ()
        ProjectEditorDialog.copy_selected_clips(e)
        self.assertIsNone(e._clip_clipboard)
        self.assertEqual(e.session.project.tracks[0].clips[0].id, "first")
        e._error.assert_not_called()

    def test_ruler_seek_is_stable_when_preview_is_cached_and_stopped(self):
        from PySide6.QtMultimedia import QMediaPlayer
        from this_voice_thing.ui.pages.project_editor import seconds_label

        e = self.editor
        player = Mock()
        player.playbackState.return_value = QMediaPlayer.PlaybackState.StoppedState
        e.player = player
        e.preview_file = "cached-preview.wav"
        e.preview_revision = e.session.project.revision
        e.timeline.set_playhead = Mock()
        e.position_label = Mock()

        ProjectEditorDialog._seek_preview(e, 2.25)

        e.timeline.set_playhead.assert_called_once_with(2.25)
        e.position_label.setText.assert_called_once_with(seconds_label(2.25))
        player.setPosition.assert_called_once_with(2250)
        player.play.assert_not_called()

    def test_ruler_seek_without_cached_preview_sets_cursor_only(self):
        e = self.editor
        e.player = Mock()
        e.preview_file = None
        e.preview_revision = None
        e.timeline.set_playhead = Mock()
        e.position_label = Mock()

        ProjectEditorDialog._seek_preview(e, 3.5)

        e.timeline.set_playhead.assert_called_once_with(3.5)
        e.player.setPosition.assert_not_called()
        e.player.play.assert_not_called()

    def test_stopping_preview_does_not_erase_edit_position(self):
        from PySide6.QtMultimedia import QMediaPlayer

        e = self.editor
        e.stop_button = Mock()
        e.play_button = Mock()
        e.timeline.set_playhead = Mock()
        e.position_label = Mock()
        ProjectEditorDialog._on_preview_state(
            e, QMediaPlayer.PlaybackState.StoppedState)

        e.stop_button.setEnabled.assert_called_once_with(False)
        e.timeline.set_playhead.assert_not_called()
        e.position_label.setText.assert_not_called()

    def test_preview_stop_blocks_late_zero_position_and_preserves_cursor(self):
        from PySide6.QtMultimedia import QMediaPlayer

        e = self.editor
        e.player = Mock()
        e.player.playbackState.return_value = QMediaPlayer.PlaybackState.PlayingState
        e.timeline.set_playhead = Mock()
        e.position_label = Mock()
        e.stop_button = Mock()
        e.play_button = Mock()
        e._stop_requested = False

        ProjectEditorDialog.stop_preview(e)
        self.assertTrue(e._stop_requested)
        e.player.stop.assert_called_once()
        ProjectEditorDialog._on_preview_position(e, 0)
        e.timeline.set_playhead.assert_not_called()
        e.position_label.setText.assert_not_called()

        ProjectEditorDialog._on_preview_state(e, QMediaPlayer.PlaybackState.StoppedState)
        self.assertFalse(e._stop_requested)
        e.timeline.set_playhead.assert_not_called()

    def test_single_clip_commands_refuse_ambiguous_multi_selection(self):
        e = self.editor
        before = e.session.project.revision
        ProjectEditorDialog.split_selected_at_playhead(e)
        ProjectEditorDialog.duplicate_selected_clip(e)

        self.assertEqual(e.session.project.revision, before)
        self.assertEqual(len(e.session.project.tracks[0].clips), 2)
        self.assertEqual(e.note.setText.call_count, 2)
        self.assertIn("one clip", e.note.setText.call_args_list[0].args[0])
        self.assertIn("one clip", e.note.setText.call_args_list[1].args[0])
        e._error.assert_not_called()
        e.refresh.assert_not_called()

    def test_clipboard_not_reusable_in_another_project(self):
        e = self.editor
        ProjectEditorDialog.copy_selected_clips(e)
        e.session = ProjectSession(AudioProject("new", "Other project"))
        new_revision = e.session.project.revision
        ProjectEditorDialog.paste_copied_clips(e)
        e._error.assert_called_once()
        self.assertEqual(e.session.project.revision, new_revision)
        e.refresh.assert_not_called()


if __name__ == "__main__":
    main()
