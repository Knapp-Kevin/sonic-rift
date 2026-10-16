"""Synthetic PCM tests for sample-accurate Sonic Rift track rendering."""
import unittest

import numpy as np
from this_voice_thing.core.audio_project import AudioProject, Clip, Track
from this_voice_thing.core.audio_timeline_mix import render_timeline


class TimelineMixTests(unittest.TestCase):
    def project(self, tracks, rate=48000):
        return AudioProject("project1", "Wind-down", sample_rate=rate, tracks=tracks)

    def test_voice_and_sound_overlap_at_exact_frames(self):
        sr = 48000
        project = self.project([
            Track("narration", "voice", "Voice", [Clip("v1", "voice", sr, sr, asset_id="spoken")]),
            Track("waves", "sound", "Sea", [Clip("s1", "sound", 0, 3*sr, asset_id="ocean")]),
        ])
        sources = {"spoken": (np.ones(sr, dtype=np.float32)*0.2, sr),
                   "ocean": (np.ones(sr*3, dtype=np.float32)*0.1, sr)}
        output = render_timeline(project, sources.__getitem__)
        self.assertEqual(output.audio.shape, (3*sr, 2))
        np.testing.assert_allclose(output.audio[0], [0.1, 0.1])
        np.testing.assert_allclose(output.audio[sr], [0.3, 0.3], atol=1e-6)
        np.testing.assert_allclose(output.audio[2*sr], [0.1, 0.1])
        np.testing.assert_allclose(sources["spoken"][0], 0.2)

    def test_sound_loop_repeats_and_mute_silences(self):
        project = self.project([Track("waves", "sound", "Ocean", [
            Clip("s", "sound", 0, 6, asset_id="short", loop=True)])],rate=48000)
        data = np.array([0.1,0.2,0.3],dtype=np.float32)
        result = render_timeline(project,lambda _: (data,48000))
        np.testing.assert_allclose(result.audio[:,0],[0.1,0.2,0.3,0.1,0.2,0.3])
        project.tracks[0].muted = True
        np.testing.assert_array_equal(render_timeline(project,lambda _: (_ for _ in ()).throw(AssertionError())).audio, 0)

    def test_fades_and_gain_apply_without_mutating_source(self):
        source = np.ones(5,dtype=np.float32)
        project = self.project([Track("t", "sound", "S", [Clip("a", "sound", 0, 5, asset_id="id",gain_db=-6,
                                                        fade_in_frames=3,fade_out_frames=2)])])
        output = render_timeline(project, lambda _: (source,48000))
        self.assertEqual(output.audio[0,0],0)
        self.assertGreater(output.audio[2,0],0)
        self.assertEqual(output.audio[-1,0],0)
        np.testing.assert_array_equal(source,np.ones(5))

    def test_resample_mono_to_stereo_and_stems_sum_to_mix(self):
        s = np.sin(2*np.pi*220*np.arange(4410)/44100).astype(np.float32)
        project = self.project([Track("v", "voice", "Voice", [Clip("c","voice",0,4800,asset_id="voice")])])
        m = render_timeline(project,lambda _: (s,44100))
        self.assertEqual(m.audio.shape,(4800,2))
        np.testing.assert_allclose(m.audio[:,0],m.audio[:,1])
        np.testing.assert_array_equal(m.stems["v"],m.audio)

    def test_fractional_resample_length_matches_import_clip_duration(self):
        import math
        source = np.linspace(-0.2, 0.2, 1000, dtype=np.float32)
        expected = math.ceil(1000 * 48000 / 44100)
        self.assertEqual(expected, 1089)
        project = self.project([
            Track("voice", "voice", "Narration",
                  [Clip("take", "voice", 0, expected, asset_id="take")])
        ])
        result = render_timeline(project, lambda _: (source, 44100))
        self.assertEqual(result.audio.shape, (expected, 2))
        self.assertNotEqual(result.audio[-1, 0], 0)

    def test_unrendered_or_missing_asset_fails_loudly(self):
        p = self.project([Track("voice","voice","N",[Clip("text","voice",0,0,text="Hello")]),
                          Track("sound","sound","S",[Clip("id","sound",0,400,asset_id="gone")])])
        with self.assertRaisesRegex(ValueError,"Unrendered"):
            render_timeline(p,lambda _: (np.ones(400),48000))
        p.tracks[0].clips.clear()
        with self.assertRaisesRegex(ValueError,"Cannot resolve clip asset"):
            render_timeline(p,lambda _: (_ for _ in ()).throw(KeyError("gone")))

    def test_reject_short_nonlooping_source_and_invalid_samples(self):
        p = self.project([Track("sound","sound","S",[Clip("id","sound",0,600,asset_id="short")])])
        with self.assertRaisesRegex(ValueError,"shorter"):
            render_timeline(p,lambda _: (np.ones(200),48000))
        with self.assertRaisesRegex(ValueError,"nonfinite"):
            render_timeline(p,lambda _: (np.array([float('nan')]*600),48000))
        with self.assertRaisesRegex(ValueError,"sample rate"):
            render_timeline(p,lambda _: (np.ones(600),True))

    def test_bound_mix_memory_before_resolving_assets(self):
        p = self.project([Track("sound","sound","S",[Clip("id","sound",0,48000000,asset_id="large")])])
        with self.assertRaisesRegex(ValueError,"memory budget"):
            render_timeline(p,lambda _: (_ for _ in ()).throw(AssertionError()), max_mix_bytes=10240)


if __name__ == "__main__":
    unittest.main()
