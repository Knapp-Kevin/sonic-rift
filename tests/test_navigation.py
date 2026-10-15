"""Journey-based navigation (Phase 1): grouped sidebar, Voices tabs, finishing on Create."""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.argv = ["main.py"]


class NavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        from this_voice_thing.ui import main_window
        cls.app = QApplication.instance() or QApplication([])
        from this_voice_thing import paths
        cls.tmp = tempfile.mkdtemp()
        # The window keeps its data (settings, voices, pronunciations, models.json) in the
        # project folder and saves settings when it closes. Point it at a scratch folder so
        # the suite never overwrites the owner's real settings, even while the app is running.
        with patch.object(paths, "ROOT", cls.tmp), \
                patch.object(main_window.ChatterboxApp, "start_default_model_load", lambda self: None), \
                patch.object(main_window.ChatterboxApp, "restart_api_server", lambda self: None):
            cls.window = main_window.ChatterboxApp()
        cls.window.output_directory = cls.tmp

    @classmethod
    def tearDownClass(cls):
        cls.window.close()

    def test_window_data_stays_out_of_the_project_folder(self):
        from this_voice_thing import paths
        for path in (self.window.app_settings_path, self.window.model_config_path, self.window.script_dir):
            self.assertTrue(os.path.abspath(path).startswith(os.path.abspath(self.tmp)), path)
        self.assertNotEqual(os.path.abspath(self.window.script_dir), os.path.abspath(paths.ROOT))

    def sidebar_labels(self):
        return [self.window.sidebar.item(i).text() for i in range(self.window.sidebar.count())]

    def test_sidebar_is_grouped_by_task(self):
        self.assertEqual(self.sidebar_labels(),
                         ["Create", "Voices", "Sounds", "TOOLS", "Transcribe", "SETUP", "Models", "Settings"])
        from PySide6.QtCore import Qt
        for i, label in enumerate(self.sidebar_labels()):
            selectable = bool(self.window.sidebar.item(i).flags() & Qt.ItemFlag.ItemIsSelectable)
            self.assertEqual(selectable, label not in ("TOOLS", "SETUP"), label)

    def test_show_page_reaches_every_page_and_the_new_voice_tab(self):
        w = self.window
        for page in (w.PAGE_GENERATE, w.PAGE_VOICE, w.PAGE_SOUNDSCAPE, w.PAGE_TRANSCRIBE, w.PAGE_MODEL, w.PAGE_ADVANCED):
            w.show_page(page)
            self.assertEqual(w.pages.currentIndex(), page)
        w.show_page(w.PAGE_STUDIO)
        self.assertEqual(w.pages.currentIndex(), w.PAGE_VOICE)
        self.assertEqual(w.voices_stack.currentIndex(), 1)
        w.show_page(w.PAGE_VOICE)
        self.assertEqual(w.voices_stack.currentIndex(), 0)

    def test_finishing_on_create_holds_speed_pitch_mp3_and_subtitle_format(self):
        w = self.window
        self.assertIn("MP3", [w.output_format_combo.itemText(i) for i in range(w.output_format_combo.count())])
        for widget in (w.speed_slider, w.pitch_slider, w.subtitle_format_combo):
            self.assertTrue(w.finishing_panel.isAncestorOf(widget))
        w.output_format_combo.setCurrentText("MP3")
        w.speed_slider.set_value(1.2)
        settings = w.current_finishing_settings()
        self.assertEqual((settings.output_format, settings.speed), ("MP3", 1.2))
        w.reset_finishing()
        self.assertEqual(w.current_finishing_settings().speed, 1.0)

    def test_models_page_has_a_sounds_tab_with_every_sound_model(self):
        w = self.window
        w.show_sound_models()
        self.assertEqual(w.pages.currentIndex(), w.PAGE_MODEL)
        self.assertEqual(w.current_capability(), "sound")
        self.assertEqual(len(w.your_tiles.findChildren(type(w.sound_engine_tile(w.sound_model_engines()[0])))),
                         len(w.sound_model_engines()))
        self.assertTrue(w.discover_section.isHidden())
        w.show_capability("clone")
        self.assertFalse(w.discover_section.isHidden())

    def test_settings_holds_the_log(self):
        w = self.window
        settings_page = w.pages.widget(w.PAGE_ADVANCED)
        self.assertTrue(settings_page.isAncestorOf(w.console_log_view))


if __name__ == "__main__":
    unittest.main()
