"""Project editor wording and window behaviour found in Windows acceptance of #99."""

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from this_voice_thing.core.audio_project import AudioProject, Clip, Track  # noqa: E402
from this_voice_thing.ui.pages.project_editor import describe_error  # noqa: E402


class DescribeError(unittest.TestCase):
    def project(self):
        clip = Clip("c1", "voice", 4 * 48000, 48000, asset_id="voice_" + "a" * 64)
        return AudioProject("p1", "Wind-down", tracks=[Track("t1", "voice", "Narrator", clips=[clip])])

    def test_missing_media_names_the_track_and_time(self):
        text = describe_error("Cannot resolve clip asset: voice_" + "a" * 64, self.project())
        self.assertIn("Narrator", text)
        self.assertIn("4.0 s", text)
        self.assertNotIn("voice_aaa", text)

    def test_damaged_and_newer_files_are_explained(self):
        self.assertIn("isn't a readable Sonic Rift project", describe_error("Expecting value: line 1 column 34 (char 33)"))
        self.assertIn("newer version", describe_error("Unsupported project schema version"))

    def test_cancel_is_not_reported_as_a_failure(self):
        self.assertEqual(describe_error("Project export cancelled"), "Export cancelled. Nothing was written.")

    def test_unknown_errors_pass_through(self):
        self.assertEqual(describe_error("Disk full"), "Disk full")


class WindowBehaviour(unittest.TestCase):
    def test_editor_is_not_modal_and_the_app_closes_it_first(self):
        generate = (ROOT / "this_voice_thing/ui/pages/generate.py").read_text(encoding="utf-8")
        opener = generate[generate.index("def open_project_editor"):generate.index("def _project_editor_closed")]
        self.assertNotIn(".exec()", opener)          # Create must stay usable while a project is open
        self.assertIn("setModal(False)", opener)
        window = (ROOT / "this_voice_thing/ui/main_window.py").read_text(encoding="utf-8")
        close = window[window.index("def closeEvent"):]
        self.assertLess(close.index("close_project_editor()"), close.index("save_app_settings()"))

    def test_no_internal_identifiers_in_the_editor_list(self):
        editor = (ROOT / "this_voice_thing/ui/pages/project_editor.py").read_text(encoding="utf-8")
        self.assertNotIn('f"Clip {clip.id[:8]}"', editor)
        self.assertNotIn("revision {project.revision}", editor)


class EditorDirtyState(unittest.TestCase):
    def test_fresh_editor_has_nothing_to_discard(self):
        """The editor's dirty flag compares against the revision it started from."""
        from this_voice_thing.core.audio_project_session import ProjectSession
        from this_voice_thing.core.audio_project import new_id
        session = ProjectSession(AudioProject(new_id(), "Untitled project"))
        baseline = session.project.revision
        self.assertEqual(session.project.revision, baseline)       # untouched: nothing to lose
        session.add_track("voice", "Narration")
        self.assertNotEqual(session.project.revision, baseline)    # edited: prompt before discarding


if __name__ == "__main__":
    unittest.main()
