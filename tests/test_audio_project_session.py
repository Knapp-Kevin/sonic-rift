"""Pure standard-library editor-state tests: no Qt, audio engines or personal files."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from this_voice_thing.core.audio_project import AudioProject, Clip, new_id
from this_voice_thing.core.audio_project_session import ProjectSession, MAX_HISTORY


class ProjectEditSessionTests(unittest.TestCase):
    def setUp(self):
        self.session = ProjectSession(AudioProject("project", "Ocean"))
        self.track = self.session.add_track("sound", "Waves")

    def test_undo_redo_and_increasing_revision(self):
        self.session.add_clip(self.track, Clip("wave", "sound", 0, 48000, asset_id="sound_deadbeef1234"))
        self.session.update_clip("wave", start_frame=24000)
        self.assertEqual(self.session.project.revision, 3)
        self.assertTrue(self.session.undo())
        self.assertEqual(self.session.project.tracks[0].clips[0].start_frame, 0)
        self.assertTrue(self.session.redo())
        self.assertEqual(self.session.project.tracks[0].clips[0].start_frame, 24000)
        self.assertEqual(self.session.project.revision, 5)

    def test_new_edit_after_undo_erases_redo(self):
        self.session.add_clip(self.track, Clip("wave", "sound", 0, 48000, asset_id="sound_deadbeef1234"))
        self.session.undo()
        self.assertTrue(self.session.can_redo)
        self.session.update_track(self.track, name="Surf")
        self.assertFalse(self.session.can_redo)

    def test_reject_invalid_edit_without_mutating_snapshot_or_undo_stack(self):
        before = deepcopy(self.session.project)
        undo_count = len(self.session._undo)
        with self.assertRaises(ValueError):
            self.session.add_clip(self.track, Clip("broken", "voice", 0, 100, asset_id="voice_123"))
        self.assertEqual(self.session.project, before)
        self.assertEqual(len(self.session._undo), undo_count)

    def test_missing_ids_and_unsupported_fields_fail(self):
        with self.assertRaises(KeyError):
            self.session.update_track("missing", name="None")
        with self.assertRaises(KeyError):
            self.session.remove_clip("missing")
        with self.assertRaises(ValueError):
            self.session.update_track(self.track, kind="voice")
        with self.assertRaises(ValueError):
            self.session.update_clip("missing", kind="sound")

    def test_project_file_save_and_reopen(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "scene.sonicrift.json"
            self.session.save(path)
            self.assertEqual(ProjectSession.open(path).project, self.session.project)
            self.session.update_track(self.track, name="Gentle Surf")
            self.session.save()
            self.assertEqual(ProjectSession.open(path).project.tracks[0].name, "Gentle Surf")

    def test_refuse_external_file_changes_even_at_same_revision(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "scene.sonicrift.json"
            self.session.save(path)
            path.write_bytes(path.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "changed on disk"):
                self.session.save()
            self.assertIn(b" ", path.read_bytes())

    def test_refuse_file_collision_and_preserve_other_project(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "scene.sonicrift.json"
            path.write_text("do not overwrite")
            with self.assertRaises(FileExistsError):
                self.session.save(path)
            self.assertEqual(path.read_text(), "do not overwrite")

    def test_move_track_then_undo(self):
        other = self.session.add_track("voice", "Narration")
        self.assertTrue(self.session.move_track(other, 0))
        self.assertEqual([t.id for t in self.session.project.tracks], [other, self.track])
        self.session.undo()
        self.assertEqual([t.id for t in self.session.project.tracks], [self.track, other])
        with self.assertRaises(ValueError):
            self.session.move_track(other, 100)

    def test_noop_edit_does_not_advance_revision(self):
        initial = self.session.project.revision
        self.assertFalse(self.session.update_track(self.track, name="Waves"))
        self.assertEqual(self.session.project.revision, initial)
        self.assertFalse(self.session.can_redo)

    def test_delete_undo_and_copy_isolation(self):
        self.session.add_clip(self.track, Clip("wave", "sound", 0, 48000, asset_id="sound_deadbeef1234"))
        self.session.remove_track(self.track)
        self.assertEqual(len(self.session.project.tracks), 0)
        self.session.undo()
        self.assertEqual(len(self.session.project.tracks[0].clips), 1)
        original = self.session.project
        self.session.update_clip("wave", gain_db=-12)
        self.assertEqual(original.tracks[0].clips[0].gain_db, 0)

    def test_history_is_bounded(self):
        for number in range(MAX_HISTORY + 15):
            self.session.update_track(self.track, name=f"Waves {number}")
        self.assertEqual(len(self.session._undo), MAX_HISTORY)
        for _ in range(MAX_HISTORY):
            self.assertTrue(self.session.undo())
        self.assertFalse(self.session.undo())


if __name__ == "__main__":
    unittest.main()
