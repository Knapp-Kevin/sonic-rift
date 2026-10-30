"""Speech's Model picker names the loaded model, even when it was loaded from somewhere else
(a voice pick, the Models page, Voices), and syncing it does not start another load."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication, QComboBox  # noqa: E402

from this_voice_thing.ui.pages.model_loading import ModelLoading  # noqa: E402

APP = QApplication.instance() or QApplication([])
ENTRIES = [{"label": "Official multilingual", "repo_id": "chatterbox", "backend": "multilingual"},
           {"label": "Qwen3 voice cloning", "repo_id": "qwen3-base", "backend": "qwen"}]


def window(loaded):
    combo = QComboBox()
    combo.addItem("CLONE", None)             # a section header, as the real picker has
    for index, entry in enumerate(ENTRIES):
        combo.addItem(entry["label"], index)
    combo.setCurrentIndex(1)                 # last picked on Speech: Official multilingual
    w = SimpleNamespace(model_repo_combo=combo, selected_model_repo="chatterbox", loads=[], refreshed=[])
    w.get_visible_model_entries = lambda: ENTRIES
    w.entry_key = lambda entry: (entry["repo_id"], entry["backend"])
    w.loaded_entry_key = lambda: (loaded["repo_id"], loaded["backend"])
    w.refresh_model_repo_tooltip = lambda: w.refreshed.append("tooltip")
    w.refresh_language_options = lambda: w.refreshed.append("languages")
    combo.currentIndexChanged.connect(lambda _i: w.loads.append(combo.currentText()))
    return w


class PickerShowsTheLoadedModel(unittest.TestCase):
    def test_a_model_loaded_elsewhere_is_shown(self):
        w = window(ENTRIES[1])
        ModelLoading.show_loaded_model_in_picker(w)
        self.assertEqual(w.model_repo_combo.currentText(), "Qwen3 voice cloning")
        self.assertEqual(w.selected_model_repo, "qwen3-base")
        self.assertEqual(w.refreshed, ["tooltip", "languages"])
        self.assertEqual(w.loads, [], "showing the loaded model must not load it again")

    def test_already_matching_picker_is_left_alone(self):
        w = window(ENTRIES[0])
        ModelLoading.show_loaded_model_in_picker(w)
        self.assertEqual(w.model_repo_combo.currentText(), "Official multilingual")
        self.assertEqual(w.refreshed, [])

    def test_a_model_not_in_the_list_changes_nothing(self):
        w = window({"repo_id": "other", "backend": "kokoro"})
        ModelLoading.show_loaded_model_in_picker(w)
        self.assertEqual(w.model_repo_combo.currentText(), "Official multilingual")

    def test_sync_runs_after_the_picker_is_rebuilt(self):
        # The picker gains a newly loaded model only when the load handler rebuilds it, so the
        # sync must come after that or the new model is not in the list yet.
        calls = []
        w = mock.MagicMock(system_has_nvidia_gpu=False, device_used="cuda")
        w.loaded_entry.return_value = {"label": "Qwen3 voice cloning"}
        w.after_voice_model_ready.side_effect = lambda: calls.append("rebuild")
        w.show_loaded_model_in_picker.side_effect = lambda: calls.append("sync")
        ModelLoading.on_model_loaded(w, object(), "cuda")
        self.assertEqual(calls, ["rebuild", "sync"])


if __name__ == "__main__":
    unittest.main()
