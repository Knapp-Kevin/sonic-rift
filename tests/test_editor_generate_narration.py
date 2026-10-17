"""#71: narration rendered in place from the project editor.

The take must land on the same clip (same id, same start) as one undoable edit, never
replace a take or script that changed meanwhile, attach nothing when cancelled, and keep
the model exclusive while it renders."""

import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from this_voice_thing.core.audio_project import AudioProject, Clip, Track  # noqa: E402
from this_voice_thing.core.audio_project_session import generated_take_target  # noqa: E402

VOICE_A = "voice_" + "a" * 64
VOICE_B = "voice_" + "b" * 64


def _project(asset_id="", text="Breathe in slowly."):
    clip = Clip("c1", "voice", 4 * 48000, 48000 if asset_id else 0, asset_id=asset_id, text=text)
    return AudioProject("p1", "Wind-down", tracks=[Track("t1", "voice", "Narrator", clips=[clip])])


class GeneratedTakeTarget(unittest.TestCase):
    def test_same_clip_same_script_attaches(self):
        project = _project()
        clip, reason = generated_take_target(project, "p1", "c1", "Breathe in slowly.", "")
        self.assertEqual((clip.id, reason), ("c1", ""))

    def test_stale_results_are_refused_with_a_reason(self):
        cases = {
            "different project": (_project(), "other", "c1", "Breathe in slowly.", ""),
            "removed": (_project(), "p1", "gone", "Breathe in slowly.", ""),
            "script edited": (_project(text="Breathe out."), "p1", "c1", "Breathe in slowly.", ""),
            "take attached meanwhile": (_project(asset_id=VOICE_B), "p1", "c1", "Breathe in slowly.", VOICE_A),
        }
        for name, args in cases.items():
            with self.subTest(name):
                clip, reason = generated_take_target(*args)
                self.assertIsNone(clip)
                self.assertTrue(reason)

    def test_a_sound_clip_is_not_a_target(self):
        project = AudioProject("p1", "x", tracks=[Track("t1", "sound", "S", clips=[
            Clip("c1", "sound", 0, 10, asset_id="sound_abcdefabcdef")])])
        self.assertIsNone(generated_take_target(project, "p1", "c1", "", "sound_abcdefabcdef")[0])


class NarrationProblem(unittest.TestCase):
    """The owner-side gate: model, busy jobs and the script's voice."""

    def owner(self, **overrides):
        library = SimpleNamespace(get=lambda vid: SimpleNamespace(name="Calm narrator") if vid == "v1" else None)
        values = dict(model=object(), model_is_loading=False, live_voice_busy=False, active_voice_id="v1",
                      voice_library=library, model_busy_outside_live=lambda: False)
        values.update(overrides)
        return SimpleNamespace(**values)

    def problem(self, owner, voice_id=""):
        from this_voice_thing.ui.pages.generation import Generation
        return Generation.narration_generation_problem(owner, voice_id)

    def test_ready(self):
        self.assertIsNone(self.problem(self.owner()))
        self.assertIsNone(self.problem(self.owner(), "v1"))

    def test_missing_or_loading_model(self):
        self.assertIn("Load a speech model", self.problem(self.owner(model=None)))
        self.assertIn("still loading", self.problem(self.owner(model_is_loading=True)))

    def test_busy_model(self):
        self.assertIn("busy", self.problem(self.owner(model_busy_outside_live=lambda: True)))
        self.assertIn("busy", self.problem(self.owner(live_voice_busy=True)))

    def test_script_written_for_another_voice(self):
        self.assertIn("Calm narrator", self.problem(self.owner(active_voice_id="v2"), "v1"))
        self.assertIn("no longer in the Voice Library", self.problem(self.owner(), "gone"))


try:
    from PySide6.QtCore import QThread, Signal
    from PySide6.QtWidgets import QApplication, QWidget
except ImportError:   # pragma: no cover
    QThread = None


if QThread is not None:
    class _FakeRender(QThread):
        """Stands in for AudioGeneratorThread: writes a short WAV when released."""
        generation_complete = Signal(str, int)
        error_occurred = Signal(str)
        chunk_generated = Signal(int, int, int)
        section_timed = Signal(int, int, float)

        def __init__(self, output_dir, seconds=1.5, fail=None):
            super().__init__()
            self.output_dir, self.seconds, self.fail = output_dir, seconds, fail
            self.release = threading.Event()
            self.partial_info = None
            self._stopped = False

        def stop(self):
            self._stopped = True
            self.release.set()

        def run(self):
            self.release.wait(10)
            if self._stopped:
                self.error_occurred.emit("Stopped by user before start.")
                return
            if self.fail:
                self.error_occurred.emit(self.fail)
                return
            os.makedirs(self.output_dir, exist_ok=True)
            path = os.path.join(self.output_dir, f"narration_{id(self)}.wav")
            t = np.arange(int(24000 * self.seconds)) / 24000
            sf.write(path, (0.2 * np.sin(2 * np.pi * 220 * t)).astype("float32"), 24000)
            self.chunk_generated.emit(1, 1, 1)
            self.generation_complete.emit(path, 24000)

    class _Owner(QWidget):
        def __init__(self, root):
            super().__init__()
            self.script_dir = root
            self.output_directory = os.path.join(root, "outputs")
            self.current_audio_file = None
            self.active_voice_id = None
            self.sound_library = SimpleNamespace(get=lambda _id: None, audio_dir=root)
            self.text_input = SimpleNamespace(toPlainText=lambda: "")
            self.problem = None
            self.renders = []
            self.busy = []

        def narration_generation_problem(self, voice_id=""):
            return self.problem

        def narration_generator(self, text, output_dir):
            render = _FakeRender(output_dir, **getattr(self, "render_options", {}))
            render.text = text
            self.renders.append(render)
            return render

        def begin_editor_generation(self):
            self.busy.append("begin")

        def end_editor_generation(self):
            self.busy.append("end")


@unittest.skipIf(QThread is None, "PySide6 not available")
class EditorGeneratesNarration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from this_voice_thing.ui.pages import project_editor
        self.module = project_editor
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.owner = _Owner(self.tmp.name)
        self.dialogs = []
        self.answer = project_editor.QMessageBox.StandardButton.Yes
        self.patches = [
            patch.object(project_editor.QMessageBox, "information",
                         lambda *a, **k: self.dialogs.append(("information", a[2]))),
            patch.object(project_editor.QMessageBox, "warning",
                         lambda *a, **k: self.dialogs.append(("warning", a[2]))),
            patch.object(project_editor.QMessageBox, "question",
                         lambda *a, **k: (self.dialogs.append(("question", a[2])), self.answer)[1]),
        ]
        for p in self.patches:
            p.start()
        self.editor = project_editor.ProjectEditorDialog(self.owner)
        clip = Clip("c1", "voice", 4 * 48000, 0, text="Breathe in slowly.")
        self.editor.session.apply(lambda project: project.tracks.append(
            Track("t1", "voice", "Narrator", clips=[clip])))
        self.editor.refresh("c1")

    def tearDown(self):
        job = self.editor.narration_job
        if job and job["thread"] is not None:
            job["thread"].stop()
            job["thread"].wait(5000)
        self.pump(lambda: self.editor.narration_job is None, 5)
        self.pump(lambda: self.editor.peak_worker is None, 5)       # waveforms read the takes
        for p in self.patches:
            p.stop()
        self.editor.deleteLater()
        self.owner.deleteLater()
        self.app.processEvents()
        self.tmp.cleanup()

    def pump(self, condition, timeout=10):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.app.processEvents()
            if condition():
                return True
            time.sleep(0.01)
        return False

    def clip(self):
        return self.editor.session.project.tracks[0].clips[0]

    def run_render(self):
        render = self.owner.renders[-1]
        render.release.set()
        self.assertTrue(self.pump(lambda: self.editor.narration_job is None))

    def test_take_lands_on_the_same_clip_as_one_undoable_edit(self):
        revision = self.editor.session.project.revision
        self.editor.generate_narration()
        self.assertEqual(self.editor.narrate_button.text(), "Cancel narration")
        self.assertEqual(self.owner.renders[-1].text, "Breathe in slowly.")
        self.run_render()
        clip = self.clip()
        self.assertEqual((clip.id, clip.start_frame, clip.text), ("c1", 4 * 48000, "Breathe in slowly."))
        self.assertTrue(clip.asset_id.startswith("voice_"))
        self.assertEqual(clip.frame_count, 72000)                      # 1.5 s at the project's 48 kHz
        self.assertEqual(self.editor.session.project.revision, revision + 1)
        self.assertEqual(self.owner.busy, ["begin", "end"])
        self.assertEqual(self.editor.narrate_button.text(), "Generate narration")
        self.assertTrue(self.editor.is_dirty())
        self.editor.undo()
        self.assertEqual((self.clip().asset_id, self.clip().frame_count), ("", 0))
        stored = Path(self.tmp.name) / "project_media" / "voice" / (clip.asset_id[len("voice_"):] + ".wav")
        self.assertTrue(stored.is_file())                             # undo never deletes media

    def test_replacing_a_take_asks_and_undo_brings_the_old_one_back(self):
        self.editor.generate_narration()
        self.run_render()
        first = self.clip().asset_id
        self.owner.render_options = {"seconds": 2.0}
        self.editor.refresh("c1")
        self.answer = self.module.QMessageBox.StandardButton.No
        self.editor.generate_narration()
        self.assertEqual(len(self.owner.renders), 1)                    # declined: nothing started
        self.answer = self.module.QMessageBox.StandardButton.Yes
        self.editor.generate_narration()
        self.run_render()
        self.assertNotEqual(self.clip().asset_id, first)
        self.assertEqual(self.clip().frame_count, 96000)
        self.editor.undo()
        self.assertEqual(self.clip().asset_id, first)

    def test_script_edited_while_rendering_is_not_overwritten(self):
        self.editor.generate_narration()
        self.editor.session.update_narration_text("c1", "Breathe out.")
        self.run_render()
        self.assertEqual((self.clip().text, self.clip().asset_id), ("Breathe out.", ""))
        self.assertIn("edited", self.editor.note.text())

    def test_other_edits_meanwhile_still_attach(self):
        self.editor.generate_narration()
        self.editor.session.update_track("t1", gain_db=-3.0)
        self.run_render()
        self.assertTrue(self.clip().asset_id)
        self.assertEqual(self.editor.session.project.tracks[0].gain_db, -3.0)

    def test_cancel_attaches_nothing_and_frees_the_model(self):
        self.editor.generate_narration()
        self.editor.generate_narration()                               # the button now cancels
        self.assertTrue(self.pump(lambda: self.editor.narration_job is None))
        self.assertEqual(self.clip().asset_id, "")
        self.assertEqual(self.owner.busy, ["begin", "end"])
        self.assertIn("cancelled", self.editor.note.text().lower())
        self.assertFalse([d for d in self.dialogs if d[0] == "warning"])

    def test_a_new_project_meanwhile_gets_nothing(self):
        self.editor.generate_narration()
        self.editor.session_serial += 1                               # what New / Open do
        self.run_render()
        self.assertEqual(self.clip().asset_id, "")
        self.assertIn("different project", self.editor.note.text())

    def test_missing_model_is_explained_and_nothing_starts(self):
        self.owner.problem = "Load a speech model in Models first (this window can stay open)."
        self.editor.generate_narration()
        self.assertEqual(self.owner.renders, [])
        self.assertIn("Load a speech model", self.dialogs[-1][1])
        self.assertIsNone(self.editor.narration_job)

    def test_a_failed_render_is_reported_and_changes_nothing(self):
        self.owner.render_options = {"fail": "CUDA out of memory"}
        revision = self.editor.session.project.revision
        self.editor.generate_narration()
        self.run_render()
        self.assertEqual(self.editor.session.project.revision, revision)
        self.assertEqual(self.dialogs[-1], ("warning", "CUDA out of memory"))
        self.assertEqual(self.owner.busy, ["begin", "end"])

    def test_only_scripts_can_be_generated(self):
        self.editor.tree.setCurrentItem(self.editor.tree.topLevelItem(0))   # the track row
        self.editor.generate_narration()
        self.assertEqual(self.owner.renders, [])
        self.assertIn("Select a narration script", self.dialogs[-1][1])

    def test_closing_waits_for_the_render(self):
        self.editor.generate_narration()
        self.editor.reject()
        self.assertIn("still generating", self.dialogs[-1][1])
        self.assertIsNotNone(self.editor.narration_job)


if __name__ == "__main__":
    unittest.main()
