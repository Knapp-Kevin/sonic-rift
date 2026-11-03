"""The Windows installer script keeps what is the user's: an upgrade over an existing copy must
not reset files the app writes, such as the model list (models.json)."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ISS = ROOT / "packaging" / "windows" / "SonicRift.iss"


def file_entries():
    text = ISS.read_text(encoding="utf-8")
    section = re.search(r"^\[Files\]\s*$(.*?)^\[", text, re.M | re.S).group(1)
    return [line for line in section.splitlines() if line.startswith("Source:")]


class InstallerKeepsUserFiles(unittest.TestCase):
    def test_the_bulk_copy_leaves_out_the_model_list(self):
        bulk = [line for line in file_entries() if 'StageDir}\\*"' in line]
        self.assertEqual(len(bulk), 1)
        self.assertIn('Excludes: "\\models.json"', bulk[0])

    def test_the_model_list_is_only_written_when_missing_and_survives_uninstall(self):
        models = [line for line in file_entries() if line.split(";")[0].endswith('\\models.json"')]
        self.assertEqual(len(models), 1)
        self.assertIn("onlyifdoesntexist", models[0])
        self.assertIn("uninsneveruninstall", models[0])
        self.assertNotIn("ignoreversion", models[0])


if __name__ == "__main__":
    unittest.main()
