"""Sonic Rift's code stays independent of the Chatterbox-TTS-UI it was forked from.

The inherited code was rewritten in November 2026 (the independence work). This keeps it that way:
no function may closely resemble an upstream function, and only a handful of short lines (public
names, Qt calls and file names that any implementation shares) may match upstream verbatim.
"""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_upstream_similarity as audit  # noqa: E402

MAX_FUNCTION_SIMILARITY = 0.8    # the highest after the rewrite was 0.73 (a one-line getattr)
MAX_SHARED_LINES = 60            # 51 after the rewrite, all short API calls, names and file names


def upstream_available():
    return subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", audit.UPSTREAM + "^{commit}"],
                          capture_output=True).returncode == 0


@unittest.skipUnless(upstream_available(), "the upstream commit isn't in this clone's history")
class UpstreamIndependence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = audit.audit("HEAD")

    def test_no_function_closely_resembles_upstream(self):
        close = [row for row in self.result["functions"] if row["ratio"] >= MAX_FUNCTION_SIMILARITY]
        self.assertEqual(close, [], "rewrite these instead of adapting upstream code")

    def test_only_a_few_short_lines_match_upstream(self):
        lines = self.result["lines"]
        self.assertLessEqual(len(lines), MAX_SHARED_LINES,
                             "\n".join(f"{l['path']}:{l['line']} {l['text']}" for l in lines))

    def test_upstream_files_are_not_in_the_tree(self):
        tree = subprocess.run(["git", "-C", str(ROOT), "ls-tree", "-r", "--name-only", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.split()
        for name in ("launch_app.py", "model_backends.py", "docs/screenshots/upstream_original.png"):   # main.py is our own launcher
            self.assertNotIn(name, tree)


if __name__ == "__main__":
    unittest.main()
