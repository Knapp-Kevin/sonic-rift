"""End-to-end project document, asset, PCM and WAV export in scratch directories."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from threading import Event

import numpy as np
import soundfile as sf

from this_voice_thing.core.audio_project import AudioProject, Clip, Track, read_project, save_project
from this_voice_thing.core.audio_project_export import export_project
from this_voice_thing.core.audio_project_media import ProjectMedia
from this_voice_thing.core.soundscape.assets import AssetLibrary


class ProjectExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.sounds = AssetLibrary(str(self.root))
        self.media = ProjectMedia(self.root, self.sounds)
        sr = 48000
        t = np.arange(sr) / sr
        voice = (np.sin(t * 2 * np.pi * 240) * 0.1).astype(np.float32)
        ocean = (np.sin(t * 2 * np.pi * 90) * 0.05).astype(np.float32)
        self.voice_id = self.media.import_voice_take(voice, sr)
        ocean_asset = self.sounds.add(ocean, sr, "Waves", "procedural", loop=True, metrics={"verified": True})
        self.sound_id = "sound_" + ocean_asset.id
        self.project = AudioProject("wind-down", "Wind-down", tracks=[
            Track("narrator", "voice", "Reader", [Clip("v", "voice", 0, sr, asset_id=self.voice_id)]),
            Track("ocean", "sound", "Waves", [Clip("s", "sound", 0, sr * 2, asset_id=self.sound_id, loop=True)])
        ])
        save_project(self.root / "project.sonicrift.json", self.project)

    def tearDown(self):
        self.tmp.cleanup()

    def test_reopened_project_produces_master_and_premaster_stems(self):
        project = read_project(self.root / "project.sonicrift.json")
        manifest_path = export_project(project, ProjectMedia(self.root, AssetLibrary(str(self.root))), self.root / "render")
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(manifest["project_id"], "wind-down")
        self.assertEqual(manifest["stem_stage"], "post_duck_pre_master")
        audio, sr = sf.read(self.root / "render" / "master.wav", dtype="float32", always_2d=True)
        self.assertEqual((len(audio), sr, audio.shape[1]), (96000, 48000, 2))
        self.assertLess(np.max(np.abs(audio)), 1)
        for path in manifest["stems"].values():
            self.assertTrue((self.root / "render" / path).is_file())
        self.assertEqual(len(manifest["stems"]), 2)
        self.assertLessEqual(manifest["metrics"]["true_peak_db"], -1.0)
        self.assertAlmostEqual(manifest["metrics"]["integrated_lufs"], -16.0, delta=0.4)

    def test_export_discloses_ai_and_unknown_without_private_source_metadata(self):
        from this_voice_thing.core.music.catalog import ACE_STEP_15
        sr = self.project.sample_rate
        t = np.arange(sr, dtype=np.float32) / sr
        music = (0.03 * np.sin(2 * np.pi * 110 * t)).astype(np.float32)
        asset = self.sounds.add(
            music, sr, "Private track", "ace_step_15", False,
            kind="music", model=ACE_STEP_15.repo_id,
            prompt="a secret prompt that must not be disclosed",
            metrics={"test": True}, source_event={
                "origin": "ai_generated", "engine": "ace_step_15",
                "model_id": ACE_STEP_15.repo_id,
                "model_revision": ACE_STEP_15.model_revision,
            })
        self.project.tracks[1].clips.append(
            Clip("music", "sound", 0, sr, asset_id="sound_" + asset.id))
        before = self.media.resolve("sound_" + asset.id)[0].copy()
        target = self.root / "provenance-render"
        manifest_path = export_project(self.project, self.media, target)
        exported = json.loads(manifest_path.read_text(encoding="utf-8"))
        disclosure = exported["provenance_disclosure"]
        self.assertEqual(disclosure["disclosure_status"], "unsigned_local_claims_not_c2pa")
        self.assertFalse(disclosure["c2pa_signed"])
        self.assertFalse(disclosure["c2pa_embedded"])
        self.assertTrue(disclosure["contains_ai"])
        self.assertTrue(disclosure["contains_unknown"])  # imported narration has no origin event
        self.assertEqual(disclosure["classification"], "mixed_ai_and_other")
        self.assertIn(ACE_STEP_15.repo_id, disclosure["model_ids"])
        self.assertEqual(disclosure["clip_source_counts"]["ai_generated"], 1)
        self.assertGreaterEqual(disclosure["clip_source_counts"]["unknown"], 1)
        self.assertNotIn("secret prompt", manifest_path.read_text(encoding="utf-8"))
        self.assertNotIn("media_sha256", str(disclosure))
        np.testing.assert_array_equal(self.media.resolve("sound_" + asset.id)[0], before)

    def test_provenance_failure_stops_export_before_publishing(self):
        with patch("this_voice_thing.core.audio_project_export.project_origin_inventory",
                   side_effect=ValueError("Provenance cannot be assessed")):
            with self.assertRaisesRegex(ValueError, "Provenance cannot"):
                export_project(self.project, self.media, self.root / "blocked-provenance")
        self.assertFalse((self.root / "blocked-provenance").exists())
        self.assertEqual(list(self.root.glob(".sonicrift-export-*")), [])

    def test_optional_wav_ogg_mp3_encoders_produce_readable_audio(self):
        path = export_project(self.project, self.media, self.root / "formats", formats=("wav", "ogg", "mp3"))
        data = json.loads(path.read_text())
        self.assertEqual(set(data["master_files"]), {"wav", "ogg", "mp3"})
        for fmt in ("wav", "ogg", "mp3"):
            info = sf.info(str(path.parent / f"master.{fmt}"))
            self.assertEqual(info.samplerate, 48000)
            self.assertEqual(info.channels, 2)
            self.assertAlmostEqual(info.duration, 2.0, delta=0.02)

    def test_destination_never_overwrites_existing_files(self):
        root = self.root / "render"
        root.mkdir()
        (root / "keep.txt").write_text("keep")
        with self.assertRaises(FileExistsError):
            export_project(self.project, self.media, root)
        self.assertEqual((root / "keep.txt").read_text(), "keep")

    def test_missing_asset_yields_no_export_folder(self):
        self.project.tracks[1].clips[0].asset_id = "sound_000000000000"
        with self.assertRaisesRegex(ValueError, "Cannot resolve"):
            export_project(self.project, self.media, self.root / "not-created")
        self.assertFalse((self.root / "not-created").exists())

    def test_invalid_formats_and_gain_fail_before_side_effects(self):
        for formats in (("wav", "wav"), ("flac",), ()): 
            with self.assertRaisesRegex(ValueError, "formats"):
                export_project(self.project, self.media, self.root / "invalid", formats=formats)
        with self.assertRaisesRegex(ValueError, "loudness"):
            export_project(self.project, self.media, self.root / "invalid", target_lufs=float("nan"))
        self.assertFalse((self.root / "invalid").exists())

    def test_failed_export_cleans_temporary_directory(self):
        with patch("this_voice_thing.core.audio_project_export.mastering.write_audio", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                export_project(self.project, self.media, self.root / "failed")
        self.assertFalse((self.root / "failed").exists())
        self.assertEqual(list(self.root.glob(".sonicrift-export-*")), [])

    def test_export_cancellation_never_publishes_partial_folder(self):
        from this_voice_thing.core.audio_project_export import ExportCancelled
        cancelled = Event()
        cancelled.set()
        with self.assertRaises(ExportCancelled):
            export_project(self.project, self.media, self.root / "cancelled",
                           should_cancel=cancelled.is_set)
        self.assertFalse((self.root / "cancelled").exists())

    def test_cancel_after_first_format_discards_staging(self):
        from this_voice_thing.core.audio_project_export import ExportCancelled
        from this_voice_thing.core.soundscape import mastering
        cancelled = Event()
        original = mastering.write_audio
        def write_and_cancel(*args, **kwargs):
            result = original(*args, **kwargs)
            cancelled.set()
            return result
        with patch("this_voice_thing.core.audio_project_export.mastering.write_audio",
                   side_effect=write_and_cancel):
            with self.assertRaises(ExportCancelled):
                export_project(self.project, self.media, self.root / "cancelled",
                               should_cancel=cancelled.is_set)
        self.assertFalse((self.root / "cancelled").exists())
        self.assertEqual(list(self.root.glob(".sonicrift-export-*")), [])

    def test_short_project_manifest_has_valid_json_not_infinity(self):
        self.project.tracks[0].clips[0].frame_count = 100
        self.project.tracks[1].clips[0].frame_count = 100
        manifest_path = export_project(self.project, self.media, self.root / "short")
        self.assertNotIn("Infinity", manifest_path.read_text())
        self.assertIsNone(json.loads(manifest_path.read_text())["metrics"]["integrated_lufs"])


if __name__ == "__main__":
    unittest.main()
