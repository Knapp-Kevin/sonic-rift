"""Do not silently install a moving Chatterbox source from the main requirements input.

The source-run setup recompiles the lock when its input is newer. A floating
Git branch would silently change upstream source during a later install.
"""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
DIRECT_URL = re.compile(
    r"^chatterbox-tts\s*@\s*git\+https://github\.com/resemble-ai/chatterbox\.git@(.+?)\s*$",
    re.MULTILINE,
)


class ChatterboxSourcePinTests(unittest.TestCase):
    def test_input_and_lock_use_the_same_full_commit(self):
        input_text = (ROOT / "requirements.in").read_text(encoding="utf-8")
        lock_text = (ROOT / "requirements.lock.txt").read_text(encoding="utf-8")
        input_refs = DIRECT_URL.findall(input_text)
        lock_refs = DIRECT_URL.findall(lock_text)
        self.assertEqual(len(input_refs), 1, "Expected one direct Chatterbox source in requirements.in")
        self.assertEqual(len(lock_refs), 1, "Expected one locked Chatterbox source")
        full_sha = re.compile(r"^[0-9a-f]{40}$")
        self.assertRegex(input_refs[0], full_sha, "Chatterbox requirement must pin a full commit SHA")
        self.assertEqual(input_refs[0], lock_refs[0], "Update the lock and source input together")

    def test_explicitly_rejects_floating_refs(self):
        for ref in ("master", "main", "HEAD", "develop", "v3"):
            with self.subTest(ref=ref):
                self.assertNotRegex(ref, r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
