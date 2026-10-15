"""Pure-Python configuration read/write regression checks.

Run without Qt or any speech engines: python -m unittest tests.test_core_config_io
"""
import json
from pathlib import Path
import tempfile
import unittest

from this_voice_thing.core import config_io


class ConfigIOTests(unittest.TestCase):
    def test_absent_settings_are_not_an_error(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(
                config_io.read_json(Path(folder) / "settings.json"),
                (None, None),
            )

    def test_absent_model_config_preserves_diagnostic(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "models.json"
            self.assertEqual(
                config_io.read_json(
                    path,
                    missing_error=f"Model config '{path}' not found.",
                    error_label=f"model config '{path}'",
                ),
                (None, f"Model config '{path}' not found."),
            )

    def test_corrupted_configuration_keeps_context(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "models.json"
            path.write_text("{bad json", encoding="utf-8")
            value, error = config_io.read_json(
                path, error_label=f"model config '{path}'",
            )
            self.assertIsNone(value)
            self.assertIn("Failed to read model config", error)
            self.assertIn(str(path), error)

    def test_settings_error_does_not_claim_missing_models(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "app_settings.json"
            path.write_text("invalid", encoding="utf-8")
            result, error = config_io.read_json(path)
            self.assertIsNone(result)
            self.assertIn("Failed to read", error)
            self.assertNotIn("Model config", error)

    def test_round_trip_unicode_nested_values_and_indentation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            original = {"label": "Français", "settings": {"engine": "kokoro"}, "models": [1, True]}
            config_io.write_json(path, original)
            text = path.read_text(encoding="utf-8")
            self.assertIn("Français", text)
            self.assertIn('\n  "label":', text)
            self.assertEqual(json.loads(text), original)
            self.assertEqual(config_io.read_json(path), (original, None))

    def test_read_only_operation_does_not_create_missing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "missing.json"
            config_io.read_json(path)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
