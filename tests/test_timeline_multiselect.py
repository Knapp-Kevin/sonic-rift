"""Qt offscreen interactions for timeline Ctrl-click multi-selection."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from this_voice_thing.core.audio_project import AudioProject, Clip, Track
from this_voice_thing.ui.project_timeline import TimelineView


class TimelineMultiSelectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.view = TimelineView(lambda clip: clip.id)
        self.view.resize(1100, 240)
        self.view.set_project(AudioProject(
            "p", "Multi-selection", tracks=[
                Track("track1", "sound", "Music", [
                    Clip("a", "sound", 0, 2 * 48000, asset_id="sound_a"),
                    Clip("b", "sound", 3 * 48000, 2 * 48000, asset_id="sound_b"),
                ]),
            ],
        ))
        self.view.grab()

    def tearDown(self):
        self.view.close()

    def hit(self, seconds, modifiers=Qt.KeyboardModifier.NoModifier):
        x = round(self.view._x(seconds))
        y = int(self.view.RULER + self.view.LANE / 2)
        QTest.mouseClick(self.view, Qt.MouseButton.LeftButton, modifiers, QPoint(x, y))

    def test_ctrl_click_add_toggle_without_dragging(self):
        emitted = []
        placements = []
        self.view.clipsSelectionChanged.connect(lambda ids: emitted.append(ids))
        self.view.clipPlaced.connect(lambda *args: placements.append(args))
        self.hit(1.0)
        self.assertEqual(self.view.selected_clips, ["a"])
        self.hit(4.0, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(self.view.selected_clips, ["a", "b"])
        self.assertEqual(emitted[-1], ("a", "b"))
        self.assertEqual(placements, [])
        self.assertIsNone(self.view._drag)
        self.hit(1.0, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(self.view.selected_clips, ["b"])
        self.assertEqual(emitted[-1], ("b",))

    def test_plain_click_collapses_selection(self):
        self.view.set_selected_clips(["a", "b"])
        self.hit(1.0)
        self.assertEqual(self.view.selected_clips, ["a"])
        self.assertEqual(self.view.selected, "a")

    def test_set_project_discards_stale_selected_ids(self):
        self.view.set_selected_clips(["a", "b", "a", "missing"])
        self.assertEqual(self.view.selected_clips, ["a", "b"])
        self.view.set_project(AudioProject("p", "Empty", tracks=[]))
        self.assertEqual(self.view.selected_clips, [])
        self.assertIsNone(self.view.selected)


if __name__ == "__main__":
    unittest.main()
