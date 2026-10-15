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
        cls.tmp = tempfile.mkdtemp()
        with patch.object(main_window.ChatterboxApp, "start_default_model_load", lambda self: None), \
                patch.object(main_window.ChatterboxApp, "restart_api_server", lambda self: None):
            cls.window = main_window.ChatterboxApp()
        cls.window.output_directory = cls.tmp

    @classmethod
    def tearDownClass(cls):
        cls.window.close()

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

    def test_settings_holds_the_log(self):
        w = self.window
        settings_page = w.pages.widget(w.PAGE_ADVANCED)
        self.assertTrue(settings_page.isAncestorOf(w.console_log_view))


if __name__ == "__main__":
    unittest.main()
