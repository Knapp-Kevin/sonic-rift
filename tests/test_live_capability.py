"""A model's declared live-audio capability survives models.json and stays conservative."""

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from this_voice_thing.core import model_registry  # noqa: E402


class LiveCapabilityTests(unittest.TestCase):
    def test_saving_models_json_keeps_live_audio(self):
        """Every save rewrites models.json through entry_to_json; dropping the key there
        would silently turn Live streaming off for Kokoro and VoxCPM2."""
        entry = {"repo_id": "hexgrad/Kokoro-82M", "label": "Kokoro", "backend": "kokoro",
                 "live_audio": {"mode": "segmented", "response_format": "pcm", "sample_rate": 24000}}
        saved = model_registry.entry_to_json(entry)
        self.assertEqual(saved["live_audio"], entry["live_audio"])
        self.assertEqual(model_registry.live_audio_capability(saved)["audio"], "segmented")

    def test_shipped_models_declare_live_audio(self):
        with open(os.path.join(ROOT, "models.json"), encoding="utf-8") as handle:
            entries = json.load(handle)
        entries = entries.get("models", entries) if isinstance(entries, dict) else entries
        modes = {(e.get("backend"), e.get("mode")): model_registry.live_audio_capability(e)["audio"]
                 for e in entries}
        self.assertEqual(modes.get(("kokoro", None)), "segmented")
        self.assertEqual(modes.get(("voxcpm", "clone")), "native")
        self.assertEqual(modes.get(("voxcpm", "design")), "native")

    def test_undeclared_or_malformed_means_no_live_audio(self):
        for value in (None, "native", {"mode": "magic"}, {}):
            entry = {"repo_id": "someone/model"}
            if value is not None:
                entry["live_audio"] = value
            self.assertEqual(model_registry.live_audio_capability(entry)["audio"], "none")
        odd_rate = {"live_audio": {"mode": "native", "sample_rate": "fast"}}
        self.assertIsNone(model_registry.live_audio_capability(odd_rate)["sample_rate"])


if __name__ == "__main__":
    unittest.main()
