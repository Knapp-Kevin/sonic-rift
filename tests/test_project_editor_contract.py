"""Static Create editor contract without importing Qt or user app settings.

These tests do NOT replace launching/using PySide6 on the owner's Windows PC.
"""
import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProjectEditorContractTests(unittest.TestCase):
    def test_new_editor_parses_and_exposes_workflow_actions(self):
        path = ROOT / "this_voice_thing/ui/pages/project_editor.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        dialog = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                      and node.name == "ProjectEditorDialog")
        members = {node.name for node in dialog.body if isinstance(node, ast.FunctionDef)}
        self.assertTrue({
            "new_project", "open_project", "save_project", "rename_project",
            "add_sound", "add_voice_take", "add_text_block", "edit_selected",
            "remove_selected", "undo", "redo", "edit_narration", "toggle_track_mute",
            "_import_done", "_sound_import_done", "export", "cancel_export",
            "_export_done", "_export_finished",
        } <= members)
        self.assertIn("TaskThread(", source)
        self.assertIn("should_cancel=should_cancel", source)
        self.assertIn("setDecimals(6)", source)
        self.assertIn("math.ceil(len(pcm) * sample_rate / source_rate)", source)
        self.assertIn("math.ceil(len(pcm) * project_rate / sr)", source)
        self.assertIn("getMultiLineText", source)
        self.assertIn("compatible_track_id(", source)
        self.assertIn("update_narration_text(", source)
        self.assertIn("self.import_worker = TaskThread(resolve_sound, self)", source)
        self.assertIn("self.session.update_track(track_id, muted=not track.muted)", source)
        self.assertIn("may_attach_import_result(", source)
        self.assertIn("self.session.ensure_current_file()", source)
        self.assertIn("add_actions = QHBoxLayout()", source)
        self.assertIn("self.import_worker.done.connect(self._import_done)", source)
        self.assertEqual(source.count("self.import_worker.finished.connect(self.import_worker.deleteLater)"), 2)
        self.assertIn("self.worker.finished.connect(self.worker.deleteLater)", source)
        self.assertIn("@Slot(object, str)", source)
        self.assertIn("@Slot()", source)
        self.assertNotIn("lambda result, error: self._sound_import_done", source)
        self.assertNotIn("lambda result, error: self._voice_import_done", source)

    def test_create_page_keeps_existing_text_generation_path(self):
        path = ROOT / "this_voice_thing/ui/pages/generate.py"
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path))
        self.assertIn("Project…", source)
        self.assertIn("open_project_editor", source)
        self.assertIn("self._build_text_card()", source)
        self.assertIn("self._build_player_card()", source)

    def test_no_source_data_mutation_or_auto_model_download_in_editor(self):
        source = (ROOT / "this_voice_thing/ui/pages/project_editor.py").read_text(encoding="utf-8")
        for forbidden in ("voice_library.save(", "sound_library.remove(", "torch.load(", "snapshot_download(", "run.bat"):
            self.assertNotIn(forbidden, source)

    def test_cancel_is_cooperative_with_exporter(self):
        path = ROOT / "this_voice_thing/core/audio_project_export.py"
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path))
        self.assertIn("class ExportCancelled(", source)
        self.assertIn("should_cancel=None", source)
        self.assertIn("_check_cancel(should_cancel)", source)


if __name__ == "__main__":
    unittest.main()
