"""The app's version follows Semantic Versioning and matches the newest CHANGELOG entry."""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from this_voice_thing import __version__  # noqa: E402

# semver.org's pattern, without build metadata
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
                    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?$")


class Version(unittest.TestCase):
    def test_version_is_semantic(self):
        self.assertRegex(__version__, SEMVER)

    def test_newest_changelog_entry_is_this_version(self):
        text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        newest = re.search(r"^## (\S+)", text, re.M).group(1)
        self.assertEqual(newest, __version__)


if __name__ == "__main__":
    unittest.main()
