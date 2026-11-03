"""Studio balancing: the project's ducking amount (saved, validated, used by ducking and
export) and Check balance's measurements on synthetic audio with known levels."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from this_voice_thing.core.audio_project import (
    DEFAULT_DUCK_DB, AudioProject, Clip, Track, from_dict, read_project, save_project, to_dict,
)
from this_voice_thing.core.audio_project_balance import balance_report, describe
from this_voice_thing.core.audio_project_duck import duck_ambience
from this_voice_thing.core.audio_timeline_mix import render_timeline

SR = 48000


def tone(seconds, amplitude, hz):
    t = np.arange(int(seconds * SR)) / SR
    return (amplitude * np.sin(2 * np.pi * hz * t)).astype(np.float32)


class Scene(unittest.TestCase):
    """Voice speaks 1-3 s; a steady sound bed runs 0-6 s."""

    def setUp(self):
        voice = np.concatenate([np.zeros(SR), tone(2, 0.3, 220)])
        self.source = {"v": (voice, SR), "bed": (tone(6, 0.3, 330), SR)}
        self.project = AudioProject("p", "Beacon", tracks=[
            Track("voice", "voice", "Dialogue", [Clip("v", "voice", 0, 3 * SR, asset_id="v")]),
            Track("music", "sound", "Music", [Clip("m", "sound", 0, 6 * SR, asset_id="bed")], gain_db=-14.0),
        ])

    def resolve(self, asset_id):
        return self.source[asset_id]


class DuckingAmountTests(Scene):
    def test_default_is_left_out_of_the_file_and_a_change_round_trips(self):
        self.assertEqual(self.project.duck_db, DEFAULT_DUCK_DB)
        self.assertNotIn("duck_db", to_dict(self.project))         # older builds still read it
        self.project.duck_db = -16.0
        self.assertEqual(to_dict(self.project)["duck_db"], -16.0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scene.sonicrift.json"
            save_project(path, self.project)
            self.assertEqual(read_project(path).duck_db, -16.0)
            self.assertEqual(json.loads(path.read_text())["schema_version"], 1)

    def test_out_of_range_or_bogus_amounts_are_refused(self):
        for bad in (3.0, -40.0, float("nan"), True, "-10"):
            data = {**to_dict(self.project), "duck_db": bad}
            with self.assertRaises(ValueError):
                from_dict(data)

    def test_ducking_follows_the_project_amount(self):
        raw = render_timeline(self.project, self.resolve)
        under = slice(int(1.8 * SR), int(2.2 * SR))
        level = lambda mix: float(np.sqrt(np.mean(mix.stems["music"][under] ** 2)))
        default = level(duck_ambience(self.project, raw))
        self.project.duck_db = -20.0
        deeper = level(duck_ambience(self.project, raw))
        self.project.duck_db = 0.0
        off = level(duck_ambience(self.project, raw))
        self.assertAlmostEqual(20 * np.log10(default / off), -10.0, delta=0.5)
        self.assertAlmostEqual(20 * np.log10(deeper / off), -20.0, delta=0.5)


class BalanceReportTests(Scene):
    def test_bed_is_measured_under_the_voice_by_gain_plus_ducking(self):
        report = balance_report(self.project, self.resolve)
        rows = {row["track_id"]: row for row in report["tracks"]}
        self.assertAlmostEqual(report["speaking_seconds"], 2.0, delta=0.1)
        self.assertIsNone(rows["voice"]["under_voice"])
        # Same amplitude sources: the gap is the track's -14 dB plus -10 dB of ducking
        self.assertAlmostEqual(rows["music"]["under_voice"], 24.0, delta=1.0)
        self.assertGreater(rows["music"]["without_voice"], rows["music"]["with_voice"] + 8)
        self.assertIn("dB under the voices", describe(rows["music"]))

    def test_lowering_the_track_or_ducking_deeper_widens_the_gap(self):
        before = balance_report(self.project, self.resolve)["tracks"][1]["under_voice"]
        self.project.tracks[1].gain_db = -20.0
        self.project.duck_db = -16.0
        after = balance_report(self.project, self.resolve)["tracks"][1]["under_voice"]
        self.assertAlmostEqual(after - before, 12.0, delta=1.0)

    def test_muted_tracks_read_as_muted_and_a_scene_without_voice_has_no_gap(self):
        self.project.tracks[1].muted = True
        row = balance_report(self.project, self.resolve)["tracks"][1]
        self.assertEqual(describe(row), "Muted")
        self.project.tracks[1].muted = False
        self.project.tracks[0].muted = True
        row = balance_report(self.project, self.resolve)["tracks"][1]
        self.assertIsNone(row["under_voice"])
        self.assertIn("no voice over it", describe(row))


if __name__ == "__main__":
    unittest.main()
