"""No-production-key checks for Sonic Rift C2PA format lab acceptance."""
from pathlib import Path
import runpy
import tempfile
import unittest
import numpy as np
import soundfile as sf

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "provenance_c2pa_audio_roundtrip.py"
LAB = runpy.run_path(str(SCRIPT))


class C2paAudioLabContractTests(unittest.TestCase):
    def test_generic_fixture_is_not_a_false_ai_or_trusted_claim(self):
        value = LAB["generic_test_manifest"]("audio/wav")
        self.assertEqual(value["format"], "audio/wav")
        self.assertEqual(value["ingredients"], [])
        self.assertEqual(value["assertions"][0]["label"], "c2pa.actions")
        action = value["assertions"][0]["data"]["actions"][0]
        self.assertEqual(action["action"], "c2pa.created")
        self.assertTrue(action["digitalSourceType"].endswith("/digitalCreation"))
        self.assertNotIn("ai-disclosure", str(value))
        self.assertNotIn("humanOversightLevel", str(value))

    def test_wav_comparison_is_sample_exact_and_detects_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            first = Path(folder) / "original.wav"
            second = Path(folder) / "metadata-only.wav"
            rate = 48000
            samples = np.linspace(-0.5, 0.5, 720, dtype=np.float32)
            sf.write(first, samples, rate, subtype="PCM_16")
            sf.write(second, samples, rate, subtype="PCM_16")
            meta = LAB["compare_decoded_audio"](first, second, "wav")
            self.assertEqual(meta["frames"], len(samples))
            self.assertEqual(meta["sample_rate"], rate)
            self.assertTrue(meta["decoded_audio_equal"])
            sf.write(second, samples * 0.5, rate, subtype="PCM_16")
            with self.assertRaises(AssertionError):
                LAB["compare_decoded_audio"](first, second, "wav")

    def test_missing_signing_keys_are_no_go_and_input_stays_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source.wav"
            target = root / "output"
            target.mkdir()
            sf.write(source, np.zeros(256, dtype=np.float32), 48000)
            original = source.read_bytes()
            try:
                LAB["qualify"](source=source, output_dir=target,
                               test_cert=root / "absent.pem",
                               test_key=root / "absent.key")
            except (ImportError, FileNotFoundError, ValueError, OSError):
                pass
            else:
                self.fail("Missing native library/credentials must never sign")
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(list(target.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
