"""Real WAV reads and tamper cases, always using isolated scratch directories."""
import hashlib
from pathlib import Path
import tempfile
import unittest

import numpy as np

from this_voice_thing.core.audio_project_media import ProjectMedia
from this_voice_thing.core.soundscape.assets import AssetLibrary


class ProjectMediaTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.sounds = AssetLibrary(str(self.root))
        self.media = ProjectMedia(self.root, self.sounds)
        self.audio = np.sin(2 * np.pi * 220 * np.arange(4800) / 48000).astype(np.float32) * 0.1

    def tearDown(self):
        self.folder.cleanup()

    def test_voice_take_content_addressed_and_reopenable(self):
        voice_id = self.media.import_voice_take(self.audio, 48000)
        self.assertTrue(voice_id.startswith("voice_"))
        self.assertEqual(self.media.import_voice_take(self.audio, 48000), voice_id)
        fresh = ProjectMedia(self.root, AssetLibrary(str(self.root)))
        pcm, rate = fresh.resolve(voice_id)
        self.assertEqual((len(pcm), rate), (4800, 48000))
        self.assertEqual(pcm.shape, (4800, 2))
        self.assertTrue(np.max(np.abs(pcm)) > 0.05)

    def test_sound_asset_resolves_only_verified_master(self):
        asset = self.sounds.add(self.audio, 48000, "Ocean", "procedural", loop=False)
        resolved, rate = self.media.resolve("sound_" + asset.id)
        self.assertEqual((len(resolved), rate), (4800, 48000))
        path = Path(self.sounds.path(asset))
        with path.open("ab") as output:
            output.write(b"tamper")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.media.resolve("sound_" + asset.id)

    def test_missing_unknown_and_unsafe_references_fail(self):
        for asset_id in ("../../etc/passwd", "voice_../evil", "sound_missing", "voice_notahash"):
            with self.subTest(asset_id=asset_id), self.assertRaisesRegex(ValueError, "Unknown project asset namespace"):
                self.media.resolve(asset_id)
        with self.assertRaises(FileNotFoundError):
            self.media.resolve("voice_" + "0" * 64)
        with self.assertRaises(FileNotFoundError):
            self.media.resolve("sound_" + "0" * 12)

    def test_reject_metadata_path_escape(self):
        asset = self.sounds.add(self.audio, 48000, "Ocean", "procedural", loop=False)
        asset.file = "../secrets.wav"
        with self.assertRaisesRegex(ValueError, "Unsafe Sound Library filename"):
            self.media.resolve("sound_" + asset.id)

    def test_voice_tamper_is_detected_and_never_overwritten(self):
        identifier = self.media.import_voice_take(self.audio, 48000)
        target = self.media.voice_root / (identifier[6:] + ".wav")
        with target.open("ab") as output:
            output.write(b"tamper")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.media.resolve(identifier)
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.media.import_voice_take(self.audio, 48000)

    def test_invalid_pcm_never_persists(self):
        with self.assertRaises(ValueError):
            self.media.import_voice_take([float("nan")], 48000)
        self.assertFalse(self.media.voice_root.exists())


if __name__ == "__main__":
    unittest.main()
