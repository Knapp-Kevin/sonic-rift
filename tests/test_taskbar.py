"""The Windows taskbar identity: the icon file and relaunch command it points at."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from this_voice_thing import paths  # noqa: E402
from this_voice_thing.ui import taskbar  # noqa: E402


class TaskbarTests(unittest.TestCase):
    def test_icon_file_is_a_real_ico(self):
        with open(taskbar.ICON_FILE, "rb") as handle:
            self.assertEqual(handle.read(4), b"\x00\x00\x01\x00")  # ICO header

    def test_ico_carries_every_windows_size(self):
        """Taskbar, title bar, Alt+Tab and Explorer each ask for a different size."""
        import struct
        with open(taskbar.ICON_FILE, "rb") as handle:
            data = handle.read()
        count = struct.unpack_from("<H", data, 4)[0]
        sizes = {struct.unpack_from("<B", data, 6 + 16 * i)[0] or 256 for i in range(count)}
        self.assertTrue({16, 20, 24, 32, 40, 48, 64, 128, 256} <= sizes, sizes)
        for i in range(count):
            side = struct.unpack_from("<B", data, 6 + 16 * i)[0] or 256
            length, offset = struct.unpack_from("<II", data, 6 + 16 * i + 8)
            self.assertEqual(data[offset:offset + 8], b"\x89PNG\r\n\x1a\n")   # each entry is a PNG
            self.assertLessEqual(offset + length, len(data))
            width, height = struct.unpack_from(">II", data, offset + 16)       # the PNG's IHDR
            self.assertEqual((width, height), (side, side))

    def test_falls_back_to_the_old_icon_if_the_new_set_is_missing(self):
        from unittest import mock
        self.assertEqual(taskbar.icon_file(), taskbar.ICON_FILE)
        with mock.patch.object(taskbar, "ICON_FILE", os.path.join(paths.ROOT, "missing.ico")):
            self.assertEqual(taskbar.icon_file(), taskbar.LEGACY_ICON_FILE)
        self.assertTrue(os.path.exists(taskbar.LEGACY_ICON_FILE))

    def test_taskbar_icon_is_the_sonic_rift_icon(self):
        self.assertEqual(os.path.basename(taskbar.ICON_FILE), "sonic-rift.ico")
        # The AppUserModelID stays, so users' pinned taskbar buttons keep working.
        self.assertEqual(taskbar.APP_ID, "KnappKevin.ThisVoiceThing")

    def test_relaunch_runs_main_py_from_the_project(self):
        command = taskbar.relaunch_command()
        self.assertIn(os.path.join(paths.ROOT, "main.py"), command)
        self.assertTrue(command.startswith('"'))

    @unittest.skipUnless(sys.platform == "win32", "Windows only")
    def test_identity_attaches_before_show(self):
        from PySide6.QtWidgets import QApplication, QWidget
        app = QApplication.instance() or QApplication([])
        window = QWidget()
        self.assertTrue(taskbar.set_window_identity(window))
        self.assertFalse(window.isVisible())
        window.deleteLater()
        app.processEvents()


if __name__ == "__main__":
    unittest.main()


class TaskbarNameTests(unittest.TestCase):
    def test_taskbar_shows_the_product_name_but_keeps_its_id(self):
        from this_voice_thing import APP_NAME as PACKAGE_NAME
        from this_voice_thing.ui import taskbar
        self.assertEqual(taskbar.APP_NAME, PACKAGE_NAME)
        # Changing the AppUserModelID would detach users' existing pinned taskbar buttons.
        self.assertEqual(taskbar.APP_ID, "KnappKevin.ThisVoiceThing")
