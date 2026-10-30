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
        self.assertIn("different version", describe_error("Unsupported project schema version"))

    def test_cancel_is_not_reported_as_a_failure(self):
        self.assertEqual(describe_error("Project export cancelled"), "Export cancelled. Nothing was written.")

    def test_long_project_export_explains_the_limit(self):
        """#61 acceptance: a 20-minute project failed with 'exceeds unmastered PCM memory budget'."""
        rate = 48000
        clip = Clip("c1", "sound", 0, 20 * 60 * rate, asset_id="sound_abc", loop=True)
        project = AudioProject("p1", "Long", tracks=[Track("t1", "sound", "Ocean", clips=[clip])])
        text = describe_error("Project exceeds unmastered PCM memory budget", project)
        self.assertIn("20.0 minutes", text)
        self.assertIn("about 11.7 minutes", text)          # 512 MiB / (8 bytes x 2 x 48 kHz)
        self.assertNotIn("PCM", text)
        source = (ROOT / "this_voice_thing/core/audio_timeline_mix.py").read_text(encoding="utf-8")
        self.assertIn("Project exceeds unmastered PCM memory budget", source)
        self.assertIn("Project has no rendered audio", source)
        self.assertIn("add a sound", describe_error("Project has no rendered audio"))

    def test_unknown_errors_pass_through(self):
        self.assertEqual(describe_error("Disk full"), "Disk full")
        self.assertEqual(describe_error("'missing-track'"), "missing-track")   # KeyError quoting

    def test_review_findings_are_worded_plainly(self):
        project = self.project()
        self.assertIn("longer than its audio", describe_error("Source shorter than nonlooping clip: c1", project))
        self.assertIn("Narrator", describe_error("Source shorter than nonlooping clip: c1", project))
        self.assertIn("already exists", describe_error("Refusing to replace an untracked project file"))
        self.assertIn("damaged", describe_error("Unsupported project schema version"))
        for raw in ("Source shorter than nonlooping clip", "Refusing to replace an untracked project file",
                    "Cannot resolve clip asset", "Project export cancelled"):
            source = "".join((ROOT / "this_voice_thing/core" / name).read_text(encoding="utf-8")
                             for name in ("audio_project.py", "audio_project_session.py",
                                          "audio_project_export.py", "audio_timeline_mix.py"))
            self.assertIn(raw, source, "describe_error matches a message the core no longer raises")


class WindowBehaviour(unittest.TestCase):
    def test_editor_is_not_modal_and_the_app_closes_it_first(self):
        generate = (ROOT / "this_voice_thing/ui/pages/generate.py").read_text(encoding="utf-8")
        opener = generate[generate.index("def open_project_editor"):generate.index("def _project_editor_closed")]
        self.assertNotIn(".exec()", opener)          # Speech must stay usable while a project is open
        self.assertIn("self.show_page(self.PAGE_PROJECT)", opener)   # the Studio is a page, not a modal
        window = (ROOT / "this_voice_thing/ui/main_window.py").read_text(encoding="utf-8")
        close = window[window.index("def closeEvent"):]
        self.assertLess(close.index("close_project_editor()"), close.index("save_app_settings()"))

    def test_imports_are_tied_to_the_session_they_started_in(self):
        editor = (ROOT / "this_voice_thing/ui/pages/project_editor.py").read_text(encoding="utf-8")
        self.assertEqual(editor.count("self.session_serial += 1"), 2)          # New and Open
        self.assertIn("if serial != self.session_serial:", editor)

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
