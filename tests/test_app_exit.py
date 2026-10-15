"""A clean window close must give exit code 0 (it gave 120: a flush into the closed log)."""

import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AppExitTests(unittest.TestCase):
    def run_main(self, window_code):
        """Run app.main() with the window replaced by `window_code`; logs go to a temp folder."""
        script = "\n".join((
            "import runpy, sys",
            "from this_voice_thing import app",
            f"app.LOG_PATH = {os.path.join(tempfile.mkdtemp(), 'startup.log')!r}",
            "def fake_window(*args, **kwargs):",
            *("    " + line for line in window_code),
            "runpy.run_module = fake_window",
            "app.main()",
        ))
        return subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True,
                              timeout=120)

    def test_clean_close_exits_zero(self):
        result = self.run_main(["print('window ran')", "sys.exit(0)"])
        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
        self.assertIn("window ran", result.stdout)

    def test_window_exit_code_is_kept(self):
        self.assertEqual(self.run_main(["sys.exit(3)"]).returncode, 3)

    def test_late_print_after_the_log_closes_does_not_fail(self):
        result = self.run_main([
            "import atexit",
            "atexit.register(lambda: print('a background thread printing during shutdown'))",
            "sys.exit(0)"])
        self.assertEqual(result.returncode, 0, result.stderr[-1500:])


if __name__ == "__main__":
    unittest.main()
