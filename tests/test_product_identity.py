"""Public product branding must not replace legally required provenance.

Pure standard-library tests; no Qt, model download or GPU needed.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProductIdentityTests(unittest.TestCase):
    def test_application_tooltip_does_not_advertise_original_fork(self):
        source = (ROOT / "this_voice_thing/ui/main_window.py").read_text(encoding="utf-8")
        self.assertNotIn("Began as a fork", source)
        self.assertNotIn("AcTePuKc/Chatterbox-TTS-UI", source)
        self.assertIn("ui_theme.TAGLINE", source)

    def test_public_readme_uses_current_product_and_clone_path(self):
        readme = (ROOT / "Readme.md").read_text(encoding="utf-8")
        self.assertIn("# Sonic Rift", readme)
        self.assertIn("cd sonic-rift", readme)
        self.assertNotIn("Download This Voice Thing", readme)
        self.assertNotIn("start This Voice Thing", readme)
        self.assertIn("THIRD_PARTY_NOTICES.md", readme)

    def test_upstream_notices_remain_identifiable(self):
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        self.assertIn("AcTePuKc", license_text)
        self.assertIn("Copyright (c) 2025", license_text)
        self.assertIn("Chatterbox-TTS-UI", notices)
        self.assertIn("LICENSE", notices)

    def test_contributor_workflow_references_correct_repository(self):
        contributors = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        self.assertIn("Knapp-Kevin/sonic-rift", contributors)
        self.assertNotIn("Knapp-Kevin/this-voice-thing", contributors)


if __name__ == "__main__":
    unittest.main()
