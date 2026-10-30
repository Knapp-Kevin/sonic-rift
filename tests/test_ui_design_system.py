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
            if index == w.PAGE_PROJECT:      # the Studio fits itself: a splitter, its timeline scrolls
                continue
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

    def test_wheel_scrolls_the_page_not_an_unfocused_combo(self):
        """Regression: with scrolling pages, wheeling over Live's Source combo switched it."""
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtWidgets import QApplication, QComboBox, QScrollArea, QVBoxLayout, QWidget
        from this_voice_thing.ui.widgets import install_wheel_guard
        app = QApplication.instance() or QApplication([])
        guard = install_wheel_guard(app)
        try:
            page = QWidget()
            combo = QComboBox(page)
            combo.addItems(["Live Speak", "Mic Effects"])
            QVBoxLayout(page).addWidget(combo)
            area = QScrollArea()
            area.setWidget(page)

            def wheel():
                event = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, -120),
                                    Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                                    Qt.ScrollPhase.NoScrollPhase, False)
                QApplication.sendEvent(combo, event)

            wheel()
            self.assertEqual(combo.currentIndex(), 0)     # unfocused: the page gets the wheel
            area.show(); combo.setFocus(); QApplication.processEvents()
            if combo.hasFocus():                          # focus needs a shown, active window
                wheel()
                self.assertEqual(combo.currentIndex(), 1)
            area.close()
        finally:
            app.removeEventFilter(guard)

    def test_spin_boxes_and_scrollbars_are_styled(self):
        from this_voice_thing.ui import theme
        for colors in (theme.DARK, theme.LIGHT):
            sheet = theme._stylesheet(colors)
            self.assertIn("QAbstractSpinBox::up-arrow", sheet)
            self.assertIn("QScrollBar:vertical", sheet)
            self.assertTrue(os.path.exists(colors["chevron_up"]))


if __name__ == "__main__":
    unittest.main()


class KeyboardReach(unittest.TestCase):
    """#61 acceptance: Tab typed a tab in Create's text, so 4 of its controls were reachable."""

    def test_tab_leaves_every_text_box(self):
        from PySide6.QtWidgets import QApplication, QPlainTextEdit, QTextEdit
        from this_voice_thing import paths
        from this_voice_thing.ui import main_window
        app = QApplication.instance() or QApplication([])
        tmp = tempfile.mkdtemp()
        with patch.object(paths, "ROOT", tmp), \
                patch.object(main_window.SonicRiftApp, "start_default_model_load", lambda self: None), \
                patch.object(main_window.SonicRiftApp, "restart_api_server", lambda self: None):
            window = main_window.SonicRiftApp()
        try:
            editors = window.findChildren(QPlainTextEdit) + window.findChildren(QTextEdit)
            self.assertTrue(editors)
            self.assertTrue(all(editor.tabChangesFocus() for editor in editors),
                            [editor.objectName() or type(editor).__name__ for editor in editors
                             if not editor.tabChangesFocus()])
            self.assertTrue(window.text_input.tabChangesFocus())
            self.assertTrue(window.live_text_input.tabChangesFocus())
        finally:
            window.close()
            app.processEvents()
