"""VoxCPM's worker reads reference clips without Numba (Smart App Control can block it),
and gives the same results as the librosa calls it replaces."""

import importlib.util
import os
import tempfile
import unittest

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "voxcpm_worker", os.path.join(ROOT, "engines", "voxcpm", "voxcpm_worker.py"))
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)

try:
    import librosa
    librosa.effects.trim(np.zeros(4096, dtype=np.float32))   # imports Numba; may be blocked
except Exception:
    librosa = None


def speech_like(rng):
    quiet = lambda n: 1e-4 * rng.standard_normal(n)
    return np.concatenate([quiet(rng.integers(1000, 20000)), 0.3 * rng.standard_normal(rng.integers(5000, 40000)),
                           quiet(rng.integers(1000, 20000))]).astype(np.float32)


class NumbaFreeAudio(unittest.TestCase):
    def test_trim_finds_the_loud_part(self):
        y = np.concatenate([np.zeros(8000), 0.3 * np.sin(np.arange(16000) / 5), np.zeros(8000)]).astype(np.float32)
        trimmed, (start, end) = worker.numba_free_trim(y, top_db=60)
        self.assertEqual((start, end), (7168, 25088))     # librosa's centred 2048/512 frames
        self.assertEqual(len(trimmed), end - start)
        # Pure silence is all at the reference level, so librosa keeps it whole; so do we.
        self.assertEqual(worker.numba_free_trim(np.zeros(5000, dtype=np.float32))[1], (0, 5000))

    @unittest.skipIf(librosa is None, "librosa/Numba unavailable here")
    def test_trim_matches_librosa(self):
        rng = np.random.default_rng(0)
        for _ in range(5):
            y = speech_like(rng)
            for top_db in (30, 60):
                expected = librosa.effects.trim(y, top_db=top_db, ref=np.max, frame_length=2048, hop_length=512)[1]
                self.assertEqual(tuple(int(v) for v in expected),
                                 worker.numba_free_trim(y, top_db=top_db, ref=np.max)[1])

    def test_resampled_length_matches_librosa(self):
        with tempfile.TemporaryDirectory() as folder:
            for frames in (1, 100, 44101):
                path = os.path.join(folder, f"short{frames}.wav")
                sf.write(path, np.full(frames, 0.1, dtype=np.float32), 44100)
                audio, _rate = worker.numba_free_load(path, sr=16000)
                self.assertEqual(len(audio), int(np.ceil(frames * 16000 / 44100)), frames)

    def test_load_downmixes_and_resamples(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "clip.wav")
            t = np.arange(48000) / 48000
            stereo = np.stack([np.sin(2 * np.pi * 220 * t), np.sin(2 * np.pi * 220 * t)], axis=1) * 0.5
            sf.write(path, stereo.astype(np.float32), 48000)
            audio, rate = worker.numba_free_load(path, sr=16000, mono=True)
            self.assertEqual((rate, audio.dtype, audio.ndim), (16000, np.float32, 1))
            self.assertEqual(len(audio), 16000)
            if librosa is not None:
                expected, _ = librosa.load(path, sr=16000, mono=True)
                self.assertLess(float(np.max(np.abs(expected[:len(audio)] - audio[:len(expected)]))), 1e-5)


if __name__ == "__main__":
    unittest.main()
