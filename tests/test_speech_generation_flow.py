"""Speech's model loading and rendering helpers: loading-state transitions, the picker's
selected entry, language lists per backend, sample text, status texts and take seeding."""

import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from PySide6.QtWidgets import QApplication, QComboBox, QProgressBar, QPushButton  # noqa: E402

from this_voice_thing.ui import threads  # noqa: E402
from this_voice_thing.ui.pages import generate, generation  # noqa: E402
from this_voice_thing.ui.pages.generation import Generation  # noqa: E402
from this_voice_thing.ui.pages.model_loading import ModelLoading  # noqa: E402

APP = QApplication.instance() or QApplication([])


class LoadingState(unittest.TestCase):
    def window(self):
        w = SimpleNamespace(model_load_progress=QProgressBar(), model_repo_combo=QComboBox(),
                            use_preset_button=QPushButton(), language_combo=QComboBox(), calls=[])
        w.update_model_details = lambda: w.calls.append("details")
        w.refresh_language_options = lambda: w.calls.append("languages")
        return w

    def test_loading_shows_busy_bar_and_locks_model_controls(self):
        w = self.window()
        ModelLoading.show_model_loading(w, True)
        bar = w.model_load_progress
        self.assertEqual((bar.minimum(), bar.maximum()), (0, 0))
        self.assertTrue(bar.isEnabled())
        self.assertTrue(w.model_is_loading)
        self.assertFalse(w.model_repo_combo.isEnabled())
        self.assertFalse(w.use_preset_button.isEnabled())
        self.assertFalse(w.language_combo.isEnabled())
        self.assertEqual(w.calls, ["details"])

    def test_done_resets_the_bar_and_unlocks(self):
        w = self.window()
        ModelLoading.show_model_loading(w, True)
        ModelLoading.show_model_loading(w, False)
        bar = w.model_load_progress
        self.assertEqual((bar.minimum(), bar.maximum(), bar.value()), (0, 1, 0))
        self.assertFalse(bar.isEnabled())
        self.assertFalse(w.model_is_loading)
        self.assertTrue(w.model_repo_combo.isEnabled())
        self.assertTrue(w.use_preset_button.isEnabled())
        self.assertEqual(w.calls[-1], "languages")   # the language list decides its own state

    def test_live_summary_follows_when_live_page_exists(self):
        w = self.window()
        w.live_model_label = object()
        w.refresh_live_voice_summary = lambda: w.calls.append(("live", w.model_is_loading))
        ModelLoading.show_model_loading(w, True)
        self.assertIn(("live", True), w.calls)


class SelectedEntry(unittest.TestCase):
    ENTRIES = [{"label": "A", "repo_id": "a"}, {"label": "B", "repo_id": "b"}]

    def owner(self, data):
        combo = QComboBox()
        combo.addItem("row", data)
        return SimpleNamespace(model_repo_combo=combo, get_visible_model_entries=lambda: self.ENTRIES)

    def test_row_data_is_the_entry_position(self):
        self.assertEqual(ModelLoading.get_selected_model_entry(self.owner(1))["label"], "B")

    def test_header_or_stale_rows_fall_back_to_the_first_entry(self):
        for data in (None, 5, -1):
            self.assertEqual(ModelLoading.get_selected_model_entry(self.owner(data))["label"], "A", data)


LANGUAGES = {"multilingual": {"en": "English", "fr": "French", "de": "German"},
             "legacy": {"en": "English"}, "qwen3": {"zh": "Chinese", "fr": "French"}}


class LanguageOptions(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(generate, "languages_for_backend", lambda backend: LANGUAGES[backend])
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_multilingual_selects_the_entrys_language(self):
        rows, wanted, usable = generate.language_choices({"backend": "multilingual", "language_id": "fr"})
        self.assertEqual(rows[0], ("English [en]", "en"))
        self.assertEqual(wanted, "fr")
        self.assertTrue(usable)

    def test_english_model_is_fixed_to_english(self):
        rows, wanted, usable = generate.language_choices({"backend": "legacy", "language_id": "fr"})
        self.assertEqual((rows, wanted, usable), ([("English [en]", "en")], "en", False))

    def test_falls_back_to_english_then_the_first_language(self):
        self.assertEqual(generate.language_choices({"backend": "multilingual", "language_id": "xx"})[1], "en")
        self.assertEqual(generate.language_choices({"backend": "qwen3"})[1], "zh")

    def test_combo_is_filled_without_signals(self):
        combo = QComboBox()
        changes = []
        combo.currentIndexChanged.connect(changes.append)
        owner = SimpleNamespace(language_combo=combo,
                                get_selected_model_entry=lambda: {"backend": "legacy"})
        generate.GeneratePage.refresh_language_options(owner)
        self.assertEqual(combo.currentData(), "en")
        self.assertFalse(combo.isEnabled())
        self.assertEqual(combo.toolTip(), generate.ENGLISH_ONLY_TIP)
        self.assertEqual(changes, [])


class SampleText(unittest.TestCase):
    def test_entry_sample_for_the_language_wins(self):
        entry = {"backend": "multilingual", "test_texts": {"fr": "Bonjour."}, "test_text": "Hello."}
        self.assertEqual(generate.sample_text(entry, "fr"), "Bonjour.")

    def test_multilingual_uses_built_in_samples_with_english_fallback(self):
        builtin = {"en": "Built-in English.", "de": "Eingebaut."}
        with mock.patch.object(generate, "DEFAULT_LANGUAGE_TEST_TEXTS", builtin):
            self.assertEqual(generate.sample_text({"backend": "multilingual"}, "de"), "Eingebaut.")
            self.assertEqual(generate.sample_text({"backend": "multilingual"}, "xx"), "Built-in English.")

    def test_other_engines_use_their_general_sample_or_nothing(self):
        self.assertEqual(generate.sample_text({"backend": "kokoro", "test_text": "Hi."}, "en"), "Hi.")
        self.assertIsNone(generate.sample_text({"backend": "kokoro"}, "en"))


class StatusTexts(unittest.TestCase):
    def test_a_stop_is_not_a_failure(self):
        status, was_stop = generation.error_status("Generation stopped by user before section 2 of 4.")
        self.assertTrue(was_stop)
        self.assertNotIn("(", status)

    def test_failure_shows_the_first_line_cut_to_fit(self):
        status, was_stop = generation.error_status("x" * 100 + "\ntraceback")
        self.assertFalse(was_stop)
        excerpt = status[status.index("(") + 1:-1]
        self.assertEqual(len(excerpt), generation.STATUS_ERROR_CHARS)
        self.assertTrue(excerpt.endswith("..."))
        short, _ = generation.error_status("Out of memory.\nmore")
        self.assertTrue(short.endswith("(Out of memory.)"))

    def test_elapsed_time_is_minutes_and_seconds(self):
        owner = SimpleNamespace(generation_started_at=None)
        self.assertIsNone(Generation.elapsed_generation_text(owner))
        owner.generation_started_at = 100.0
        with mock.patch.object(generation.time, "monotonic", return_value=100.0 + 125.4):
            self.assertEqual(Generation.elapsed_generation_text(owner), "02:05")

    def test_section_span(self):
        self.assertEqual(generation.section_span(3, 3), "3")
        self.assertEqual(generation.section_span(3, 5), "3–5")


class _Control:
    def __init__(self):
        self.enabled, self.text, self.visible = False, "", False

    def setEnabled(self, value):
        self.enabled = bool(value)

    def setText(self, text):
        self.text = text

    def setVisible(self, value):
        self.visible = bool(value)

    def isVisible(self):
        return self.visible

    def clear(self):
        self.text = ""


class FinishedRender(unittest.TestCase):
    def owner(self, outcome_shown):
        owner = Generation.__new__(type("Owner", (Generation,), {}))
        owner.__dict__.update(is_generating=True, model_is_loading=False, messages=[],
                              generation_outcome_shown=outcome_shown,
                              generation_timer=mock.Mock(isActive=mock.Mock(return_value=True)),
                              update_model_details=lambda: None, update_text_stats=lambda: None)
        owner.set_status_message = owner.messages.append
        for name in ("generate_button", "preview_button", "open_document_button", "model_repo_combo",
                     "generation_progress", "keep_take_button", "activity_label"):
            setattr(owner, name, _Control())
        return owner

    def test_unlocks_speech_and_stops_the_timer(self):
        owner = self.owner(outcome_shown=True)
        owner.on_render_thread_finished()
        self.assertFalse(owner.is_generating)
        owner.generation_timer.stop.assert_called_once()
        self.assertEqual(owner.generate_button.text, generation.IDLE_LABEL)
        self.assertTrue(owner.generate_button.enabled and owner.model_repo_combo.enabled)
        self.assertEqual(owner.messages, [], "the complete/error status stays")

    def test_without_an_outcome_the_status_returns_to_ready(self):
        owner = self.owner(outcome_shown=False)
        owner.on_render_thread_finished()
        self.assertEqual(owner.messages, ["Status: Ready."])


class Seeding(unittest.TestCase):
    def draw(self, seed):
        threads.seed_everything(seed)
        return random.random(), float(np.random.rand()), float(torch.rand(1))

    def test_same_take_number_same_random_streams(self):
        self.assertEqual(self.draw(1234), self.draw(1234))
        self.assertNotEqual(self.draw(1234), self.draw(1235))

    def test_device_choice_reports_why_cuda_was_refused(self):
        with mock.patch.object(threads.torch.cuda, "is_available", return_value=True), \
                mock.patch.object(threads, "probe_usable_torch_cuda", return_value=(False, "too old")):
            self.assertEqual(threads.pick_device(), ("cpu", "too old"))
        with mock.patch.object(threads.torch.cuda, "is_available", return_value=False):
            self.assertEqual(threads.pick_device(), ("cpu", None))


if __name__ == "__main__":
    unittest.main()
