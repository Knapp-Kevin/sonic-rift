"""Project-local Studio clipboard: multi-clip atomic edits and waveform parity.

Synthetic audio only; no Qt, model loading, subprocesses or user media.
"""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

import numpy as np

from this_voice_thing.core.audio_project import AudioProject, Clip
from this_voice_thing.core.audio_project_session import (
    ClipClipboard, MAX_CLIPBOARD_CLIPS, ProjectSession,
)
from this_voice_thing.core.audio_timeline_mix import render_timeline


class ClipClipboardTests(unittest.TestCase):
    def setUp(self):
        self.session = ProjectSession(AudioProject("scene", "Clipboard"))
        self.wave_track = self.session.add_track("sound", "Waves")
        self.speech_track = self.session.add_track("voice", "Narration")
        self.session.add_clip(self.wave_track, Clip(
            "wave", "sound", 8, 12, asset_id="sound_wave", gain_db=-3.0,
            fade_in_frames=2, fade_out_frames=3, source_offset_frames=2))
        self.session.add_clip(self.speech_track, Clip(
            "narration", "voice", 13, 9, asset_id="voice_take", text="A short story"))
        self.wave = np.linspace(-0.25, 0.25, 100, dtype=np.float32)
        self.voice = np.linspace(0.15, -0.15, 100, dtype=np.float32)
        self.resolve = lambda asset_id: (
            self.wave if asset_id == "sound_wave" else self.voice, 48000)

    def snapshot(self):
        return (deepcopy(self.session.project), len(self.session._undo), len(self.session._redo))

    def clips(self, track_id):
        return next(t.clips for t in self.session.project.tracks if t.id == track_id)

    def test_copy_is_read_only_and_snapshots_selected_audio(self):
        before = self.snapshot()
        copied = self.session.copy_clips(["narration", "wave"])
        self.assertIsInstance(copied, ClipClipboard)
        self.assertEqual((copied.origin_frame, copied.project_id), (8, "scene"))
        self.assertEqual([clip.id for _, clip in copied.items], ["wave", "narration"])
        self.assertEqual(self.snapshot(), before)
        self.session.update_clip("wave", gain_db=-18.0)
        self.assertEqual(copied.items[0][1].gain_db, -3.0)

    def test_paste_preserves_track_lanes_and_relative_offsets_in_one_revision(self):
        copied = self.session.copy_clips(["narration", "wave"])
        revision = self.session.project.revision
        pasted = self.session.paste_clips(copied, 100, expected_revision=revision)
        self.assertEqual(len(pasted), 2)
        self.assertEqual(self.session.project.revision, revision + 1)
        sound = self.clips(self.wave_track)[1]
        speech = self.clips(self.speech_track)[1]
        self.assertEqual((sound.id, sound.start_frame, sound.source_offset_frames),
                         (pasted[0], 100, 2))
        self.assertEqual((speech.id, speech.start_frame, speech.text),
                         (pasted[1], 105, "A short story"))
        self.assertEqual(sound.asset_id, "sound_wave")
        self.assertTrue(self.session.undo())
        self.assertEqual([c.id for c in self.clips(self.wave_track)], ["wave"])
        self.assertEqual([c.id for c in self.clips(self.speech_track)], ["narration"])
        self.assertTrue(self.session.redo())
        self.assertEqual([c.id for c in self.clips(self.wave_track)][-1], pasted[0])

    def test_paste_audio_matches_original_at_new_location(self):
        clipboard = self.session.copy_clips(["wave"])
        # Compare the selected track's stem, not the master: narration overlaps
        # the original sound and must not be accidentally counted as copied audio.
        before = render_timeline(self.session.project, self.resolve).stems[self.wave_track].copy()
        self.session.paste_clips(clipboard, 48)
        after = render_timeline(self.session.project, self.resolve).stems[self.wave_track]
        np.testing.assert_allclose(after[8:20], before[8:20], atol=1e-7)
        np.testing.assert_allclose(after[48:60], before[8:20], atol=1e-7)
        np.testing.assert_array_equal(self.wave, np.linspace(-0.25, 0.25, 100, dtype=np.float32))

    def test_paste_at_target_lane_only_matching_single_lane(self):
        other_sound = self.session.add_track("sound", "Second wave")
        clip = self.session.copy_clips(["wave"])
        pasted = self.session.paste_clips(clip, 30, target_track_id=other_sound)
        self.assertEqual(self.clips(other_sound)[0].id, pasted[0])
        self.assertEqual(self.clips(other_sound)[0].start_frame, 30)
        snapshot = self.snapshot()
        with self.assertRaisesRegex(ValueError, "different track kind"):
            self.session.paste_clips(clip, 30, target_track_id=self.speech_track)
        with self.assertRaisesRegex(ValueError, "multi-track selection"):
            self.session.paste_clips(self.session.copy_clips(["wave", "narration"]),
                                     30, target_track_id=other_sound)
        self.assertEqual(self.snapshot(), snapshot)

    def test_stale_revision_and_different_project_fail_without_side_effects(self):
        clipboard = self.session.copy_clips(["wave"])
        revision = self.session.project.revision
        self.session.update_track(self.wave_track, name="Updated")
        baseline = self.snapshot()
        with self.assertRaisesRegex(ValueError, "changed before paste"):
            self.session.paste_clips(clipboard, 33, expected_revision=revision)
        another = ProjectSession(AudioProject("another", "Other"))
        another.add_track("sound", "Waves")
        with self.assertRaisesRegex(ValueError, "another project"):
            another.paste_clips(clipboard, 33)
        self.assertEqual(self.snapshot(), baseline)

    def test_removed_target_and_bad_tampered_clipboard_fail_atomically(self):
        clipboard = self.session.copy_clips(["wave", "narration"])
        self.session.remove_track(self.speech_track)
        before = self.snapshot()
        with self.assertRaisesRegex(KeyError, "Destination track"):
            self.session.paste_clips(clipboard, 100)
        self.assertEqual(self.snapshot(), before)
        invalid = self.session.copy_clips(["wave"])
        invalid.items[0][1].asset_id = "../untrusted"
        with self.assertRaisesRegex(ValueError, "Invalid asset"):
            self.session.paste_clips(invalid, 100)
        self.assertEqual(self.snapshot(), before)

    def test_invalid_identifiers_positions_and_selection_bounds(self):
        baseline = self.snapshot()
        for ids in ([], ["wave", "wave"], [True], ["missing"], "wave"):
            with self.subTest(ids=ids), self.assertRaises((ValueError, KeyError)):
                self.session.copy_clips(ids)
        clipboard = self.session.copy_clips(["wave"])
        for frame in (-1, 2.0, True, None, 36000 * 48000):
            with self.subTest(frame=frame), self.assertRaises(ValueError):
                self.session.paste_clips(clipboard, frame)
        for invalid_revision in (True, -1, "0"):
            with self.subTest(revision=invalid_revision), self.assertRaises(ValueError):
                self.session.paste_clips(clipboard, 30, expected_revision=invalid_revision)
        self.assertEqual(self.snapshot(), baseline)

    def test_reject_unrendered_script_and_excessive_selection(self):
        self.session.add_clip(self.speech_track, Clip(
            "script", "voice", 0, 0, text="Not yet rendered"))
        with self.assertRaisesRegex(ValueError, "rendered"):
            self.session.copy_clips(["script"])
        with self.assertRaisesRegex(ValueError, "1-32"):
            self.session.copy_clips(["a" + str(n) for n in range(MAX_CLIPBOARD_CLIPS + 1)])

    def test_repeat_paste_new_ids_and_save_reopen(self):
        clipboard = self.session.copy_clips(["wave"])
        first = self.session.paste_clips(clipboard, 32)
        second = self.session.paste_clips(clipboard, 52)
        self.assertNotEqual(first, second)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "track.sonicrift.json"
            self.session.save(path)
            opened = ProjectSession.open(path)
            self.assertEqual(opened.project, self.session.project)
            self.assertEqual(len(opened.project.tracks[0].clips), 3)


if __name__ == "__main__":
    unittest.main()
