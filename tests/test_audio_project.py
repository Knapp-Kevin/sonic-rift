"""Isolated standard-library tests for versioned Sonic Rift project documents."""
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest

from this_voice_thing.core.audio_project import (
    AudioProject, Clip, Track, from_dict, new_voice_project, read_project, save_project,
)


class AudioProjectTests(unittest.TestCase):
    def test_unrendered_legacy_narration_can_be_saved_and_reopened(self):
        project = new_voice_project("Ocean story", "A calm opening", voice_id="reader1")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "ocean.sonicrift.json"
            save_project(path, project)
            self.assertEqual(read_project(path), project)
            self.assertEqual(project.tracks[0].clips[0].text, "A calm opening")
            self.assertEqual(project.tracks[0].clips[0].frame_count, 0)

    def test_layered_sound_and_voice_frames_are_exact(self):
        a = new_voice_project("Ocean", "Calm voice", "reader1")
        a.tracks[0].clips[0].start_frame = 24000
        a.tracks.append(Track("ambience", "sound", "Ocean waves", clips=[
            Clip("clip-ocean", "sound", 0, 60 * 48000, asset_id="ocean-101", loop=True,
                 gain_db=-9.0, fade_in_frames=96000, fade_out_frames=48000),
        ]))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.json"
            save_project(path, a)
            self.assertEqual(read_project(path).tracks[1].clips[0].frame_count, 2880000)
            self.assertEqual(json.loads(path.read_text())["sample_rate"], 48000)

    def test_reject_unknown_future_schema_without_modifying_original(self):
        p = new_voice_project("Base", "Hello")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "project.json"
            save_project(path, p)
            original = path.read_bytes()
            future = json.loads(original)
            future["schema_version"] = 999
            path.write_text(json.dumps(future))
            with self.assertRaisesRegex(ValueError, "Unsupported project schema"):
                read_project(path)
            self.assertEqual(json.loads(path.read_text())["schema_version"], 999)
            with self.assertRaisesRegex(ValueError, "Unsupported project schema"):
                save_project(path, from_dict(future))

    def test_reject_duplicate_ids_and_kind_mismatches(self):
        p = new_voice_project("Base", "Hello")
        c = p.tracks[0].clips[0]
        p.tracks[0].clips.append(Clip(c.id, "voice", 0, 0, text="Another"))
        with self.assertRaisesRegex(ValueError, "duplicate ID"):
            p.validate()
        p.tracks[0].clips[-1].id = "different"
        p.tracks[0].clips[-1].kind = "sound"
        p.tracks[0].clips[-1].asset_id = "rendered-test"
        p.tracks[0].clips[-1].frame_count = 120
        with self.assertRaisesRegex(ValueError, "kind mismatch"):
            p.validate()

    def test_reject_unsafe_timing_types_and_nonfinite_gain(self):
        p = new_voice_project("Base", "Hello")
        c = p.tracks[0].clips[0]
        for bad in (True, -1, 3.5):
            c.start_frame = bad
            with self.assertRaisesRegex(ValueError, "Invalid clip start"):
                p.validate()
        c.start_frame = 0
        c.gain_db = float("nan")
        with self.assertRaisesRegex(ValueError, "Invalid clip gain"):
            p.validate()

    def test_asset_reference_cannot_be_missing_for_rendered_audio(self):
        p = new_voice_project("Base", "Hello")
        p.tracks[0].clips[0].frame_count = 120
        with self.assertRaisesRegex(ValueError, "requires a library asset"):
            p.validate()

    def test_asset_id_is_opaque_not_path(self):
        p = new_voice_project("Base", "Hello")
        c = p.tracks[0].clips[0]
        c.frame_count = 48000
        c.asset_id = "../outside.wav"
        with self.assertRaisesRegex(ValueError, "Invalid asset ID"):
            p.validate()

    def test_reject_invalid_nested_collections(self):
        p = asdict(new_voice_project("Base", "Hello"))
        p["tracks"] = "not-a-track-list"
        with self.assertRaisesRegex(ValueError, "Invalid tracks array"):
            from_dict(p)
        p["tracks"] = [{"clips": "not-a-clip-list"}]
        with self.assertRaisesRegex(ValueError, "Invalid clips array"):
            from_dict(p)

    def test_atomic_write_failure_preserves_original(self):
        from unittest.mock import patch
        p = new_voice_project("Base", "Hello")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "project.json"
            save_project(path, p)
            previous = path.read_bytes()
            p.title = "Changed"
            with patch("this_voice_thing.core.audio_project.os.replace", side_effect=OSError("disk error")):
                with self.assertRaises(OSError):
                    save_project(path, p)
            self.assertEqual(path.read_bytes(), previous)
            self.assertEqual(list(Path(folder).glob("*.tmp")), [])

    def test_existing_future_or_corrupt_project_is_never_overwritten(self):
        p = new_voice_project("Base", "Hello")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "project.json"
            path.write_text('{"schema_version":999}')
            original = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "Unsupported project schema"):
                save_project(path, p)
            self.assertEqual(path.read_bytes(), original)
            path.write_text("corrupted data")
            with self.assertRaises(json.JSONDecodeError):
                save_project(path, p)
            self.assertEqual(path.read_text(), "corrupted data")

    def test_other_project_or_stale_revision_is_not_overwritten(self):
        p = new_voice_project("Base", "Hello")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "project.json"
            save_project(path, p)
            original = path.read_bytes()
            other = new_voice_project("Other", "Different")
            with self.assertRaisesRegex(ValueError, "another project"):
                save_project(path, other)
            self.assertEqual(path.read_bytes(), original)
            updated = read_project(path)
            updated.revision = 2
            save_project(path, updated)
            with self.assertRaisesRegex(ValueError, "newer project revision"):
                save_project(path, p)

    def test_does_not_mutate_caller_when_parsing(self):
        original = asdict(new_voice_project("Base", "Bonjour"))
        from_dict(original)
        self.assertIsInstance(original["tracks"][0]["clips"][0], dict)


if __name__ == "__main__":
    unittest.main()
