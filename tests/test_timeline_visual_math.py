"""No-Qt unit tests for timeline ticks and complete waveform representation."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np

LIB = Path(__file__).resolve().parents[1] / "this_voice_thing" / "core" / "timeline_visual_math.py"
SPEC = importlib.util.spec_from_file_location("timeline_visual_math", LIB)
mathlib = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mathlib)


class RulerTicks(unittest.TestCase):
    def test_short_and_standard_projects(self):
        self.assertEqual(mathlib.ruler_tick_step(10), 1)
        self.assertEqual(mathlib.ruler_tick_step(60), 5)
        self.assertEqual(mathlib.ruler_tick_step(600), 60)
        self.assertEqual(mathlib.ruler_tick_step(4800), 300)

    def test_arbitrarily_long_supported_duration(self):
        for duration in (4801, 60 * 60 * 24, 1e8):
            step = mathlib.ruler_tick_step(duration)
            self.assertGreater(step, 0)
            self.assertLessEqual(duration / step, 16)
            self.assertTrue(any(step == n * (10 ** magnitude)
                                for magnitude in range(12) for n in (1, 2, 5)))

    def test_invalid_duration_and_tick_budget(self):
        for value in (float('nan'), float('inf'), -1, True, '3600'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                mathlib.ruler_tick_step(value)
        for budget in (0, -1, 2.5, True):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                mathlib.ruler_tick_step(300, budget)


class WaveformEnvelope(unittest.TestCase):
    def test_trailing_partial_bucket_is_not_dropped(self):
        data = np.zeros(961, np.float32)
        data[-1] = 0.9
        peaks = mathlib.envelope(data, 48000, per_second=50)
        np.testing.assert_array_equal(peaks, [0, 1])

    def test_partial_only_and_empty_inputs(self):
        self.assertEqual(mathlib.envelope(np.array([0.3], dtype=np.float32), 48000).tolist(), [1])
        self.assertEqual(mathlib.envelope(np.empty(0, dtype=np.float32), 48000).tolist(), [0])
        self.assertEqual(mathlib.envelope(np.zeros(3, dtype=np.float32), 48000).tolist(), [0])

    def test_stereo_and_complete_bucket_parity(self):
        audio = np.zeros((1920, 2), dtype=np.float32)
        audio[:, 1] = [0.25] * 960 + [0.5] * 960
        peaks = mathlib.envelope(audio, 48000)
        np.testing.assert_allclose(peaks, [0.5, 1.0])

    def test_nonfinite_and_invalid_audio_format_rejected(self):
        with self.assertRaises(ValueError):
            mathlib.envelope(np.array([float('nan')]), 48000)
        with self.assertRaises(ValueError):
            mathlib.envelope(np.zeros((8, 3)), 48000)
        with self.assertRaises(ValueError):
            mathlib.envelope(np.ones(8), 0)
        with self.assertRaises(ValueError):
            mathlib.envelope(np.ones(8), 48000, per_second=0)


if __name__ == '__main__':
    unittest.main()
