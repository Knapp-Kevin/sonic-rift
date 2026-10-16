"""The shared design-system rules: the window fits small screens, and pages use shared parts."""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.argv = ["main.py"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class WindowFits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        from this_voice_thing import paths
        from this_voice_thing.ui import main_window
        cls.app = QApplication.instance() or QApplication([])
        cls.tmp = tempfile.mkdtemp()
        with patch.object(paths, "ROOT", cls.tmp), \
                patch.object(main_window.SonicRiftApp, "start_default_model_load", lambda self: None), \
                patch.object(main_window.SonicRiftApp, "restart_api_server", lambda self: None):
            cls.window = main_window.SonicRiftApp()
        cls.window.output_directory = cls.tmp

    @classmethod
    def tearDownClass(cls):
        cls.window.close()

    def test_window_fits_a_1366_by_768_laptop(self):
        """Regression: Live's page once forced a 1740 x 1515 minimum, taller than most screens."""
        w = self.window
        hint = w.minimumSizeHint().expandedTo(w.minimumSize())
        self.assertLessEqual(hint.width(), 1366 - 40)
        self.assertLessEqual(hint.height(), 768 - 80)
        w.resize(1366, 728)
        self.app.processEvents()
        self.assertEqual((w.width(), w.height()), (1366, 728))

    def test_every_page_scrolls_instead_of_growing_the_window(self):
        from PySide6.QtWidgets import QScrollArea
        w = self.window
        for index in range(w.pages.count()):
            self.assertIsInstance(w.pages.widget(index), QScrollArea, index)

    def test_status_bar_drops_the_status_prefix(self):
        self.window.set_status_message("Status: Kokoro voices is ready on the GPU.")
        self.assertEqual(self.window.status_bar.toolTip(), "Kokoro voices is ready on the GPU.")

    def test_live_keeps_rare_actions_in_menus_and_hides_mic_effects_for_typed_speech(self):
        from PySide6.QtWidgets import QPushButton
        from this_voice_thing.ui.widgets import MenuButton
        w = self.window
        live = w.pages.widget(w.PAGE_LIVE_VOICE)
        links = [b for b in live.findChildren(QPushButton) if b.isFlat() and b.isVisibleTo(live)]
        self.assertLessEqual(len(links), 6)                     # was 24 text links
        self.assertGreaterEqual(len(live.findChildren(MenuButton)), 4)
        w.live_source_mode_combo.setCurrentIndex(w.live_source_mode_combo.findData("tts"))
        self.assertTrue(w.live_mic_card.isHidden())
        w.live_source_mode_combo.setCurrentIndex(w.live_source_mode_combo.findData("mic_effects"))
        self.assertFalse(w.live_mic_card.isHidden())
        w.live_source_mode_combo.setCurrentIndex(w.live_source_mode_combo.findData("tts"))


class SharedParts(unittest.TestCase):
    def test_empty_state_follows_the_list_and_survives_teardown(self):
        from PySide6.QtWidgets import QApplication, QListWidget
        from this_voice_thing.ui.widgets import set_empty_text
        QApplication.instance() or QApplication([])
        view = QListWidget()
        state = set_empty_text(view, "Nothing here yet.")
        self.assertFalse(state.label.isHidden())
        view.addItem("one")
        self.assertTrue(state.label.isHidden())
        view.clear()
        self.assertFalse(state.label.isHidden())
        view.deleteLater()
        QApplication.processEvents()

    def test_menu_button_runs_its_actions(self):
        from PySide6.QtWidgets import QApplication
        from this_voice_thing.ui.widgets import MenuButton
        QApplication.instance() or QApplication([])
        calls = []
        button = MenuButton("More", [("First", lambda: calls.append(1)), None, ("Second", lambda: calls.append(2))])
        actions = [a for a in button.menu().actions() if not a.isSeparator()]
        self.assertEqual([a.text() for a in actions], ["First", "Second"])
        actions[1].trigger()
        self.assertEqual(calls, [2])

    def test_spin_boxes_and_scrollbars_are_styled(self):
        from this_voice_thing.ui import theme
        for colors in (theme.DARK, theme.LIGHT):
            sheet = theme._stylesheet(colors)
            self.assertIn("QAbstractSpinBox::up-arrow", sheet)
            self.assertIn("QScrollBar:vertical", sheet)
            self.assertTrue(os.path.exists(colors["chevron_up"]))


if __name__ == "__main__":
    unittest.main()
