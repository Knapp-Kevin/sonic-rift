"""Stage-1 Studio editing controls: source-level wiring plus Qt-independent call contracts.

The action methods are invoked directly on a lightweight editor stand-in. This
does NOT replace the Windows/Qt GUI acceptance test or a real playback audition.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import Mock

from this_voice_thing.core.audio_project import AudioProject, Clip
from this_voice_thing.core.audio_project_session import ProjectSession
from this_voice_thing.ui.pages.project_editor import ProjectEditorDialog


class PrecisionStudioControls(TestCase):
    def setUp(self):
        session = ProjectSession(AudioProject("scene", "Precision editing"))
        track_id = session.add_track("sound", "Soundtrack")
        session.add_clip(track_id, Clip("original", "sound", 0, 48000, asset_id="sound_test"))
        self.session = session
        self.editor = SimpleNamespace(
            session=session, timeline=SimpleNamespace(playhead=0.5),
            note=Mock(), refresh=Mock(), _error=Mock(),
            _selected=lambda: ("clip", "original"),
        )

    def test_selection_menu_exposes_two_real_commands(self):
        source = (Path(__file__).resolve().parents[1] /
                  "this_voice_thing/ui/pages/project_editor.py").read_text(encoding="utf-8")
        self.assertIn('("Split clip at playhead", self.split_selected_at_playhead)', source)
        self.assertIn('("Duplicate clip", self.duplicate_selected_clip)', source)

    def test_split_selected_at_ruler_position(self):
        ProjectEditorDialog.split_selected_at_playhead(self.editor)
        clips = self.session.project.tracks[0].clips
        self.assertEqual(len(clips), 2)
        self.assertEqual(
            [(clip.start_frame, clip.frame_count, clip.source_offset_frames) for clip in clips],
            [(0, 24000, 0), (24000, 24000, 24000)],
        )
        self.editor.refresh.assert_called_once_with(clips[1].id)
        self.editor._error.assert_not_called()
        self.assertTrue(self.session.undo())
        self.assertEqual(len(self.session.project.tracks[0].clips), 1)

    def test_duplicate_selected_uses_session_not_media_files(self):
        ProjectEditorDialog.duplicate_selected_clip(self.editor)
        clips = self.session.project.tracks[0].clips
        self.assertEqual(len(clips), 2)
        self.assertEqual(clips[1].start_frame, 48000)
        self.assertEqual(clips[1].asset_id, "sound_test")
        self.editor.refresh.assert_called_once_with(clips[1].id)
        self.editor._error.assert_not_called()

    def test_split_without_playhead_is_non_mutating(self):
        self.editor.timeline.playhead = None
        initial_revision = self.session.project.revision
        ProjectEditorDialog.split_selected_at_playhead(self.editor)
        self.assertEqual(self.session.project.revision, initial_revision)
        self.editor.note.setText.assert_called_once()
        self.editor.refresh.assert_not_called()
        self.editor._error.assert_not_called()

    def test_split_at_boundary_reports_error_without_mutation(self):
        self.editor.timeline.playhead = 1.0
        initial_revision = self.session.project.revision
        ProjectEditorDialog.split_selected_at_playhead(self.editor)
        self.assertEqual(self.session.project.revision, initial_revision)
        self.editor._error.assert_called_once()
        self.editor.refresh.assert_not_called()

    def test_selection_must_be_a_clip_for_both_actions(self):
        self.editor._selected = lambda: ("track", self.session.project.tracks[0].id)
        initial_revision = self.session.project.revision
        ProjectEditorDialog.split_selected_at_playhead(self.editor)
        ProjectEditorDialog.duplicate_selected_clip(self.editor)
        self.assertEqual(self.session.project.revision, initial_revision)
        self.assertEqual(self.editor.note.setText.call_count, 2)
        self.editor.refresh.assert_not_called()
        self.editor._error.assert_not_called()


if __name__ == "__main__":
    main()
