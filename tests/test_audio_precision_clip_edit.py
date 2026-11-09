"""Precision clip edits: deterministic sample ranges, PCM parity, and safe revisions.

Uses synthetic samples only. No Qt, models, network, or owner media.
"""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

import numpy as np

from this_voice_thing.core.audio_project import AudioProject, Clip
from this_voice_thing.core.audio_project_session import ProjectSession
from this_voice_thing.core.audio_timeline_mix import render_timeline


class PrecisionClipEditTests(unittest.TestCase):
    def setUp(self):
        self.session = ProjectSession(AudioProject("p", "Precision test"))
        self.track = self.session.add_track("sound", "Wave")
        self.clip = Clip("source", "sound", 20, 12, asset_id="synth",
                         source_offset_frames=2, fade_in_frames=3,
                         fade_out_frames=4, gain_db=-3)
        self.session.add_clip(self.track, self.clip)
        self.source = np.linspace(-0.4, 0.4, 64, dtype=np.float32)
        self.resolver = lambda asset_id: (self.source, 48000)

    def clips(self):
        return self.session.project.tracks[0].clips

    def mixed(self):
        return render_timeline(self.session.project, self.resolver).audio

    def test_split_preserves_every_sample_and_metadata(self):
        before = self.mixed().copy()
        original_revision = self.session.project.revision
        right_id = self.session.split_clip("source", 26)
        left, right = self.clips()
        self.assertNotEqual(right_id, left.id)
        self.assertEqual(right.id, right_id)
        self.assertEqual((left.start_frame, left.frame_count, left.source_offset_frames),
                         (20, 6, 2))
        self.assertEqual((right.start_frame, right.frame_count, right.source_offset_frames),
                         (26, 6, 8))
        self.assertEqual((left.fade_in_frames, left.fade_out_frames), (3, 0))
        self.assertEqual((right.fade_in_frames, right.fade_out_frames), (0, 4))
        self.assertEqual(left.asset_id, right.asset_id)
        self.assertEqual(self.session.project.revision, original_revision + 1)
        np.testing.assert_allclose(before, self.mixed(), atol=1e-7, rtol=1e-6)
        self.assertTrue(self.session.undo())
        self.assertEqual(len(self.clips()), 1)
        np.testing.assert_allclose(before, self.mixed(), atol=1e-7, rtol=1e-6)
        self.assertTrue(self.session.redo())
        self.assertEqual([c.id for c in self.clips()], ["source", right_id])
        np.testing.assert_allclose(before, self.mixed(), atol=1e-7, rtol=1e-6)

    def test_split_loop_source_offset_wraps_without_changing_audio(self):
        self.session.update_clip("source", source_offset_frames=3,
                                 fade_in_frames=0, fade_out_frames=0,
                                 frame_count=17, loop=True)
        short = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        self.resolver = lambda _: (short, 48000)
        original = self.mixed().copy()
        self.session.split_clip("source", 28)
        self.assertEqual(self.clips()[1].source_offset_frames, 11)
        np.testing.assert_allclose(original, self.mixed(), atol=1e-7)

    def test_split_rejections_do_not_touch_revision_or_history(self):
        original = deepcopy(self.session.project)
        undo = len(self.session._undo)
        redo = len(self.session._redo)
        for frame in (True, -1, 20, 21, 22, 29, 30, 31, 32, 100, 26.5):
            with self.subTest(frame=frame), self.assertRaises(ValueError):
                self.session.split_clip("source", frame)
            self.assertEqual(self.session.project, original)
            self.assertEqual((len(self.session._undo), len(self.session._redo)), (undo, redo))
        with self.assertRaises(KeyError):
            self.session.split_clip("missing", 25)
        self.assertEqual(self.session.project, original)

    def test_unrendered_voice_cannot_split_or_duplicate(self):
        voice = self.session.add_track("voice", "Script")
        self.session.add_clip(voice, Clip("draft", "voice", 0, 0, text="Hello"))
        snapshot = deepcopy(self.session.project)
        with self.assertRaisesRegex(ValueError, "rendered"):
            self.session.split_clip("draft", 1)
        with self.assertRaisesRegex(ValueError, "rendered"):
            self.session.duplicate_clip("draft")
        self.assertEqual(self.session.project, snapshot)

    def test_duplicate_reuses_source_without_changing_source_data(self):
        original_source = self.source.copy()
        prior = self.mixed().copy()
        original_revision = self.session.project.revision
        duplicate_id = self.session.duplicate_clip("source")
        self.assertEqual(self.session.project.revision, original_revision + 1)
        left, right = self.clips()
        self.assertEqual(right.id, duplicate_id)
        self.assertEqual(right.start_frame, 32)
        self.assertEqual(right.source_offset_frames, left.source_offset_frames)
        self.assertEqual(right.asset_id, left.asset_id)
        after = self.mixed()
        np.testing.assert_allclose(after[:32], prior, atol=1e-7)
        np.testing.assert_allclose(after[32:44], prior[20:32], atol=1e-7)
        np.testing.assert_array_equal(self.source, original_source)
        self.session.undo()
        self.assertEqual(len(self.clips()), 1)

    def test_duplicate_explicit_position_rejects_bad_types(self):
        self.session.duplicate_clip("source", 0)
        self.assertEqual(self.clips()[1].start_frame, 0)
        baseline = deepcopy(self.session.project)
        for position in (-1, 1.25, True, "0"):
            with self.subTest(position=position), self.assertRaises(ValueError):
                self.session.duplicate_clip("source", position)
        with self.assertRaises(KeyError):
            self.session.duplicate_clip("missing", 1)
        self.assertEqual(self.session.project, baseline)

    def test_split_and_duplicate_survive_save_reopen(self):
        right_id = self.session.split_clip("source", 26)
        self.session.duplicate_clip(right_id, 50)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "project.sonicrift.json"
            self.session.save(target)
            loaded = ProjectSession.open(target)
            self.assertEqual(loaded.project, self.session.project)
            self.assertEqual([c.start_frame for c in loaded.project.tracks[0].clips],
                             [20, 26, 50])


if __name__ == "__main__":
    unittest.main()
