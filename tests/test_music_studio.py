"""Kept music in Studio: a music asset mixes under narration and sound effects as a v1
`sound` clip, with trim, fades, gain and ducking, and survives save, reopen and export."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from this_voice_thing.core import audio_project  # noqa: E402
from this_voice_thing.core.audio_project import AudioProject, Clip, Track, read_project, save_project  # noqa: E402
from this_voice_thing.core.audio_project_export import export_project  # noqa: E402
from this_voice_thing.core.audio_project_media import ProjectMedia  # noqa: E402
from this_voice_thing.core.audio_project_session import ProjectSession  # noqa: E402
from this_voice_thing.core.music import contract, service  # noqa: E402
from this_voice_thing.core.soundscape.assets import AssetLibrary  # noqa: E402

SR = 48000


class ToneMusic:
    key, device = "ace_step_15", "cuda"

    def generate_take(self, out_path, caption, seconds, seed, **_options):
        t = np.arange(int(seconds * SR)) / SR
        chord = 0.15 * (np.sin(2 * np.pi * 196 * t) + np.sin(2 * np.pi * 247 * t) + np.sin(2 * np.pi * 294 * t))
        sf.write(out_path, np.stack([chord, chord], axis=1).astype(np.float32), SR, subtype="FLOAT")
        return {"elapsed": 0.0, "chosen": {}, "memory": {}}


class MusicInStudio(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.library = AssetLibrary(str(self.root))
        svc = service.MusicService(ToneMusic())
        result = svc.generate(contract.MusicRequest(engine="ace_step_15", prompt="soft theme", seconds=12.0,
                                                    candidates=1, seed=3))
        self.music = service.keep(self.library, result, result.takes[0], "Soft theme")
        svc.close()
        t = np.arange(4 * SR) / SR
        speech = (0.2 * np.sin(2 * np.pi * 220 * t) * (t > 1.0) * (t < 3.0)).astype(np.float32)
        self.media = ProjectMedia(self.root, self.library)
        self.voice_id = self.media.import_voice_take(speech, SR)
        hit = (0.3 * np.random.default_rng(1).standard_normal(SR // 4)).astype(np.float32)
        self.effect = self.library.add(hit, SR, "Door", "procedural", loop=False)

    def tearDown(self):
        self.tmp.cleanup()

    def test_schema_stays_v1_and_music_is_a_sound_clip(self):
        self.assertEqual(audio_project.SCHEMA_VERSION, 1)
        self.assertNotIn("music", audio_project.TRACK_KINDS)

    def test_music_under_narration_saves_reopens_and_exports(self):
        music_clip = Clip("m", "sound", 0, 6 * SR, asset_id="sound_" + self.music.id, gain_db=-6.0,
                          fade_in_frames=SR // 2, fade_out_frames=SR, source_offset_frames=2 * SR)
        project = AudioProject("scene", "Scene", tracks=[
            Track("voice", "voice", "Narrator", [Clip("v", "voice", SR, 4 * SR, asset_id=self.voice_id)]),
            Track("music", "sound", "Soft theme", [music_clip]),
            Track("fx", "effect", "Effects", [Clip("e", "effect", 3 * SR, SR // 4, asset_id="sound_" + self.effect.id)]),
        ])
        path = self.root / "scene.sonicrift.json"
        save_project(path, project)
        session = ProjectSession.open(path)
        session.update_clip("m", gain_db=-8.0)
        session.save()
        reopened = read_project(path)
        clip = reopened.tracks[1].clips[0]
        self.assertEqual((clip.gain_db, clip.source_offset_frames, clip.fade_out_frames), (-8.0, 2 * SR, SR))
        manifest = json.loads(export_project(reopened, ProjectMedia(self.root, AssetLibrary(str(self.root))),
                                             self.root / "render").read_text())
        self.assertTrue(manifest["ducking_enabled"])
        self.assertEqual(manifest["asset_ids"]["music"], ["sound_" + self.music.id])
        master, rate = sf.read(self.root / "render" / "master.wav", dtype="float32", always_2d=True)
        self.assertEqual((rate, master.shape[1], len(master)), (SR, 2, 6 * SR))
        stem, _ = sf.read(self.root / "render" / manifest["stems"]["music"], dtype="float32", always_2d=True)

        def rms(a, start, end):
            return float(np.sqrt(np.mean(a[int(start * SR):int(end * SR)] ** 2)))
        self.assertLess(rms(stem, 0.0, 0.05), rms(stem, 0.6, 0.9) * 0.5)         # fade in
        self.assertLess(rms(stem, 2.3, 2.9), rms(stem, 0.6, 0.9) * 0.6)          # ducked under speech
        self.assertGreater(rms(stem, 5.2, 5.4), 0)                                # still playing in the fade
        self.assertLess(rms(stem, 5.95, 6.0), rms(stem, 4.6, 4.9))               # fade out

    def test_a_changed_music_master_is_refused_at_export(self):
        project = AudioProject("scene", "Scene", tracks=[
            Track("music", "sound", "Theme", [Clip("m", "sound", 0, 2 * SR, asset_id="sound_" + self.music.id)])])
        with open(self.library.path(self.music), "r+b") as handle:
            handle.seek(2000)
            handle.write(b"\x7f" * 64)
        with self.assertRaises(Exception):
            export_project(project, ProjectMedia(self.root, AssetLibrary(str(self.root))), self.root / "render")
        self.assertFalse((self.root / "render").exists())


if __name__ == "__main__":
    unittest.main()
