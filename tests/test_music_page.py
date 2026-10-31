"""The Music page in a real window: controls follow the engine, jobs run off the UI thread,
cancel and shutdown don't leave takes behind, and kept music reaches the library and Studio.

The engine is a fake that writes tones; this tests Sonic Rift's page, not a music model.
"""

import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np
import soundfile as sf

sys.argv = ["main.py"]


class FakeMusicModel:
    key, device, load_seconds = "ace_step_15", "cuda", 0.0

    def __init__(self, delay=0.0):
        self.delay, self.closed, self.killed, self.calls = delay, False, False, []

    def generate_take(self, out_path, caption, seconds, seed, **options):
        self.calls.append((caption, seconds, seed, options))
        deadline = time.monotonic() + self.delay
        while time.monotonic() < deadline:
            if self.killed:
                raise RuntimeError("The acestep worker stopped unexpectedly.")
            time.sleep(0.01)
        t = np.arange(int(seconds * 48000)) / 48000
        tone = (0.2 * np.sin(2 * np.pi * 330 * t)).astype(np.float32)
        sf.write(out_path, np.stack([tone, tone], axis=1), 48000, subtype="FLOAT")
        return {"elapsed": 0.1, "chosen": {"bpm": 100}, "memory": {"peak_mb": 9000}}

    def alive(self):
        return not (self.closed or self.killed)

    def terminate(self):
        self.killed = True

    def close(self):
        self.closed = True


class MusicPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        from this_voice_thing import paths
        from this_voice_thing.ui import main_window
        cls.app = QApplication.instance() or QApplication([])
        cls.tmp = tempfile.mkdtemp()
        with patch.object(paths, "ROOT", cls.tmp), \
                patch.object(main_window.ChatterboxApp, "start_default_model_load", lambda self: None), \
                patch.object(main_window.ChatterboxApp, "restart_api_server", lambda self: None):
            cls.window = main_window.ChatterboxApp()
        cls.window.output_directory = cls.tmp
        cls.window.start_discover = lambda: None

    @classmethod
    def tearDownClass(cls):
        cls.window.close()

    def setUp(self):
        from this_voice_thing.core.music import service
        w = self.window
        w.show_page(w.PAGE_MUSIC)
        self.model = FakeMusicModel()
        w.music_model = self.model
        w.music_service = service.MusicService(self.model, w.music_work_dir)
        w.music_prompt_input.setPlainText("calm piano theme")
        w.music_instrumental_checkbox.setChecked(True)
        w.music_seconds_spin.setValue(10)
        w.music_takes_spin.setValue(2)
        w.music_seed_spin.setValue(7)
        self.installed = patch("this_voice_thing.engines.music_models.is_installed", return_value=True)
        self.installed.start()

    def tearDown(self):
        self.installed.stop()

    def wait_for_job(self, seconds=20):
        deadline = time.monotonic() + seconds
        while self.window.music_job is not None and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.01)
        self.app.processEvents()
        self.assertIsNone(self.window.music_job, "the music job didn't finish")

    def test_page_is_in_the_sidebar_and_reachable(self):
        w = self.window
        self.assertTrue(w.pages.currentWidget().isAncestorOf(w.music_generate_button))

    def test_lyrics_show_only_for_songs_and_tempo_follows_its_checkbox(self):
        w = self.window
        self.assertFalse(w.music_lyrics_input.isVisibleTo(w))
        w.music_instrumental_checkbox.setChecked(False)
        self.assertTrue(w.music_lyrics_input.isVisibleTo(w))
        w.music_bpm_checkbox.setChecked(False)
        self.assertFalse(w.music_bpm_spin.isEnabled())
        w.music_bpm_checkbox.setChecked(True)
        self.assertTrue(w.music_bpm_spin.isEnabled())
        w.music_bpm_checkbox.setChecked(False)

    def test_unsupported_controls_are_disabled_with_the_engines_reason(self):
        from dataclasses import replace
        from this_voice_thing.core.music import catalog
        engine = catalog.ACE_STEP_15
        limited = replace(engine, capabilities=replace(engine.capabilities, key=False, vocals=False,
                                                       unsupported={"key": "No key control here."}))
        with patch.dict(catalog.ENGINES, {"ace_step_15": limited}):
            self.window.refresh_music_controls()
            self.assertFalse(self.window.music_key_combo.isEnabled())
            self.assertEqual(self.window.music_key_combo.toolTip(), "No key control here.")
            self.assertFalse(self.window.music_instrumental_checkbox.isEnabled())
        self.window.refresh_music_controls()
        self.assertTrue(self.window.music_key_combo.isEnabled())

    def test_an_invalid_request_is_explained_and_nothing_runs(self):
        w = self.window
        w.music_prompt_input.setPlainText("")
        with patch("this_voice_thing.ui.pages.music.QMessageBox.information") as told:
            w.start_music()
        self.assertIn("Describe the music first.", told.call_args[0][2])
        self.assertIsNone(w.music_job)
        self.assertEqual(self.model.calls, [])

    def test_generate_runs_off_the_ui_thread_and_lists_takes(self):
        w = self.window
        self.model.delay = 0.3
        started = time.monotonic()
        w.start_music()
        self.assertLess(time.monotonic() - started, 0.25, "Generate blocked the UI")
        self.assertFalse(w.music_generate_button.isEnabled())
        self.wait_for_job()
        self.assertEqual(w.music_take_list.count(), 2)
        self.assertIn("Take A · seed 7", w.music_take_list.item(0).text())
        self.assertIn("100 BPM", w.music_take_list.item(0).text())
        self.assertTrue(w.music_generate_button.isEnabled())
        self.assertEqual(self.model.calls[0][0], "calm piano theme, instrumental, no vocals")

    def test_cancel_stops_mid_take_and_leaves_no_files(self):
        w = self.window
        self.model.delay = 5.0
        w.start_music()
        time.sleep(0.05)
        w.cancel_music()
        self.wait_for_job(10)
        self.assertEqual(w.music_take_list.count(), 0)
        self.assertIn("Cancelled", w.music_status.text())
        self.assertIsNone(w.music_model)            # the worker ended; it restarts next time
        self.assertEqual([n for n in os.listdir(w.music_work_dir) if n.endswith(".wav")], [])

    def test_a_new_generation_replaces_the_previous_takes_on_disk(self):
        w = self.window
        w.start_music()
        self.wait_for_job()
        first = [take.path for take in w.music_takes()]
        w.start_music()
        self.wait_for_job()
        self.assertFalse(any(os.path.exists(path) for path in first))
        self.assertEqual(len(os.listdir(w.music_work_dir)), 2)

    def test_keep_puts_a_music_asset_in_the_library_and_can_add_it_to_studio(self):
        w = self.window
        w.start_music()
        self.wait_for_job()
        w.music_take_list.setCurrentRow(1)
        with patch("this_voice_thing.ui.pages.music.QInputDialog.getText", return_value=("Theme B", True)), \
                patch.object(type(w), "open_project_editor") as editor:
            w.keep_music_take(to_studio=True)
        asset = w.sound_library.assets[0]
        self.assertEqual((asset.name, asset.kind, asset.seed), ("Theme B", "music", 8))
        self.assertTrue(w.sound_library.verify(asset))
        editor.return_value.add_sound.assert_called_once_with(asset)
        self.assertIn("Theme B", w.music_asset_list.item(0).text())

    def test_starting_a_sound_model_unloads_the_music_model(self):
        w = self.window
        from this_voice_thing.core.soundscape import catalog
        self.assertTrue(w.free_gpu_for(catalog.MOSS_SFX_V2) in (True, False))
        self.assertIsNone(w.music_model)
        self.assertTrue(self.model.closed)

    def test_music_waits_for_a_busy_sound_job(self):
        w = self.window
        with patch.object(type(w), "sound_busy", return_value=True), \
                patch("this_voice_thing.ui.pages.music.QMessageBox.information") as told:
            w.sound_model = object()
            try:
                self.assertFalse(w.free_gpu_for_music(w.current_music_engine()))
            finally:
                w.sound_model = None
        told.assert_called_once()


if __name__ == "__main__":
    unittest.main()
