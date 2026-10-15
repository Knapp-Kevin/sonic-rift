"""Synthetic audio and source immutability tests for speech-aware ambience ducking."""
import unittest
import numpy as np

from this_voice_thing.core.audio_project import AudioProject, Clip, Track
from this_voice_thing.core.audio_timeline_mix import TimelineMix, render_timeline
from this_voice_thing.core.audio_project_duck import duck_ambience


class SpeechDuckTests(unittest.TestCase):
    def setUp(self):
        sr = 48000
        self.sr = sr
        self.project = AudioProject("p", "Calm", tracks=[
            Track("voice", "voice", "Narrator", [Clip("v", "voice", 0, sr, asset_id="v")]),
            Track("waves", "sound", "Ocean", [Clip("s", "sound", 0, sr*2, asset_id="s")]),
            Track("fx", "effect", "Effects", [Clip("e", "effect", 0, sr*2, asset_id="e")]),
        ])
        voice = np.concatenate([np.zeros(sr//2),np.ones(sr//2)*0.2]).astype(np.float32)
        wave = np.ones(2*sr,dtype=np.float32)*0.25
        fx = np.ones(2*sr,dtype=np.float32)*0.05
        self.source = {"v":(voice,sr),"s":(wave,sr),"e":(fx,sr)}
        self.raw = render_timeline(self.project,self.source.__getitem__)

    def test_ambience_quiets_under_voice_and_recovers_after(self):
        result = duck_ambience(self.project,self.raw,attack_ms=10,release_ms=100)
        wave = result.stems["waves"][:,0]
        self.assertAlmostEqual(float(wave[5000]),0.25,places=3)
        self.assertLess(wave[40000],0.14)
        self.assertGreater(wave[78000],0.23)
        np.testing.assert_array_equal(result.stems["voice"],self.raw.stems["voice"])
        np.testing.assert_array_equal(result.stems["fx"],self.raw.stems["fx"])
        self.assertFalse(np.array_equal(result.audio,self.raw.audio))

    def test_does_not_mutate_original_mix_or_stems(self):
        original = {key: arr.copy() for key,arr in self.raw.stems.items()}
        mixed = self.raw.audio.copy()
        duck_ambience(self.project,self.raw)
        for key,prior in original.items():
            np.testing.assert_array_equal(self.raw.stems[key],prior)
        np.testing.assert_array_equal(self.raw.audio,mixed)

    def test_muted_voice_does_not_trigger_duck(self):
        self.project.tracks[0].muted=True
        raw=render_timeline(self.project,self.source.__getitem__)
        done=duck_ambience(self.project,raw)
        np.testing.assert_allclose(done.stems["waves"],raw.stems["waves"],atol=1e-6)

    def test_zero_attenuation_is_no_op(self):
        result=duck_ambience(self.project,self.raw,attenuation_db=0)
        np.testing.assert_allclose(result.audio,self.raw.audio)

    def test_reject_invalid_parameters_and_malformed_mix(self):
        for options in ({"attenuation_db": -100}, {"attack_ms":0}, {"release_ms":float('nan')}, {"threshold_db":True}):
            with self.assertRaisesRegex(ValueError,"Invalid duck"):
                duck_ambience(self.project,self.raw,**options)
        bogus=TimelineMix(self.raw.audio,self.sr,{"waves":self.raw.stems["waves"]})
        with self.assertRaisesRegex(ValueError,"stem is missing"):
            duck_ambience(self.project,bogus)


if __name__ == "__main__":
    unittest.main()
