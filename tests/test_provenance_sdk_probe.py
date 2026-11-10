"""C2PA capability probe contracts without installing or loading the native SDK."""
from pathlib import Path
import runpy
from types import SimpleNamespace
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "provenance_c2pa_sdk_probe.py"


class CapabilityProbeTests(unittest.TestCase):
    def test_report_distinguishes_reader_and_builder(self):
        method = runpy.run_path(str(SCRIPT))["capability_report"]

        class Reader:
            @staticmethod
            def get_supported_mime_types():
                return ["audio/wav", "audio/mpeg", "audio/ogg"]

        class Builder:
            @staticmethod
            def get_supported_mime_types():
                return ["audio/wav", "audio/mpeg"]

        fake = SimpleNamespace(Reader=Reader, Builder=Builder, sdk_version=lambda: "test-native")
        result = method(fake)
        self.assertEqual(result["native_sdk_version"], "test-native")
        self.assertEqual(result["status"], "probe_only_not_qualified")
        self.assertEqual(result["audio_format_candidates"]["wav"], {"reader": True, "builder": True})
        self.assertEqual(result["audio_format_candidates"]["mp3"], {"reader": True, "builder": True})
        self.assertEqual(result["audio_format_candidates"]["ogg"], {"reader": True, "builder": False})
        self.assertNotIn("qualified", result["status"].replace("not_qualified", ""))

    def test_empty_lists_cannot_claim_wav_support(self):
        method = runpy.run_path(str(SCRIPT))["capability_report"]

        class Empty:
            @staticmethod
            def get_supported_mime_types():
                return []

        result = method(SimpleNamespace(Reader=Empty, Builder=Empty))
        self.assertFalse(result["audio_format_candidates"]["wav"]["builder"])
        self.assertFalse(result["audio_format_candidates"]["wav"]["reader"])


if __name__ == "__main__":
    unittest.main()
