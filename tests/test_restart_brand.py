"""Prevent desktop rebrands from silently breaking the restart helper.

Runs without PySide6 or a display server:
    python -m unittest tests.test_restart_brand
"""

import unittest

from scripts import restart_app
from this_voice_thing import APP_NAME


class RestartBrandTests(unittest.TestCase):
    def test_restart_looks_for_current_product_name(self):
        self.assertEqual(restart_app.TITLE, APP_NAME)
        self.assertEqual(APP_NAME, "Sonic Rift")


if __name__ == "__main__":
    unittest.main()
