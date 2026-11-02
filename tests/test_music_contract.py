"""Music contract, service and library: requests are checked, takes validated, keeps atomic.

The fake engine here writes synthetic tones. It exercises Sonic Rift's own code paths;
it is not evidence that any real model generates music.
"""

import json
import os
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from this_voice_thing.core.music import catalog, contract, service  # noqa: E402
from this_voice_thing.core.music.contract import MusicRequest, MusicRequestError  # noqa: E402
from this_voice_thing.core.soundscape.assets import AssetLibrary  # noqa: E402
from this_voice_thing.engines import music_models  # noqa: E402

CAPS = catalog.ACE_STEP_15.capabilities


def request(**changes):
    base = MusicRequest(engine="ace_step_15", prompt="warm piano and strings underscore", seconds=12.0,
                        candidates=2, seed=40)
    return replace(base, **changes)


class FakeMusicModel:
    """Writes a 48 kHz stereo chord of the asked length; can be told to misbehave."""

    key, device = "ace_step_15", "cuda"

    def __init__(self, length_factor=1.0, silent=False, fail_on=None):
        self.length_factor, self.silent, self.fail_on = length_factor, silent, fail_on
        self.calls = []

    def generate_take(self, out_path, caption, seconds, seed, **options):
        self.calls.append((caption, seconds, seed, options))
        if self.fail_on == seed:
            raise RuntimeError("CUDA out of memory")
        rate = 48000
        t = np.arange(int(seconds * self.length_factor * rate)) / rate
        tone = 0.2 * (np.sin(2 * np.pi * 220 * t) + np.sin(2 * np.pi * 277 * t)) * (0.0 if self.silent else 1.0)
        sf.write(out_path, np.stack([tone, tone], axis=1).astype(np.float32), rate, subtype="FLOAT")
        return {"path": out_path, "elapsed": 1.5, "chosen": {"bpm": 92, "keyscale": "A minor"},
                "memory": {"peak_mb": 9100 + seed}}


class Contract(unittest.TestCase):
    def test_a_plain_instrumental_request_is_valid(self):
        self.assertEqual(contract.validate(request(), CAPS), [])

    def test_each_problem_is_reported_in_plain_words(self):
        problems = contract.validate(request(prompt=" ", seconds=5, candidates=9, seed=-1, bpm=400,
                                             key="H minor", time_signature=5), CAPS)
        self.assertEqual(len(problems), 7, problems)
        self.assertIn("Describe the music first.", problems)

    def test_lyrics_only_with_vocals_and_vocals_need_lyrics(self):
        self.assertTrue(contract.validate(request(lyrics="la la"), CAPS))
        self.assertIn("lyrics", " ".join(contract.validate(request(instrumental=False), CAPS)))
        self.assertEqual(contract.validate(request(instrumental=False, lyrics="[verse]\nmy own words"), CAPS), [])

    def test_unsupported_controls_are_refused_with_the_engines_reason(self):
        caps = replace(CAPS, bpm=False, key=False, vocals=False,
                       unsupported={"bpm": "No tempo control on this engine.", "vocals": "No singing."})
        problems = contract.validate(request(bpm=100, key="C major", instrumental=False, lyrics="x"), caps)
        self.assertIn("No tempo control on this engine.", problems)
        self.assertIn("No singing.", problems)
        self.assertIn("This engine doesn't take a key.", problems)

    def test_caption_carries_style_fields_and_instrumental_intent(self):
        text = request(genre="cinematic", mood="hopeful", instrumentation="piano, cello").caption()
        self.assertEqual(text, "warm piano and strings underscore, genre: cinematic, mood: hopeful, "
                               "instrumentation: piano, cello, instrumental, no vocals")
        self.assertNotIn("instrumental", request(instrumental=False, lyrics="x").caption())

    def test_seeds_are_consecutive_and_deterministic(self):
        self.assertEqual(request(candidates=3, seed=contract.MAX_SEED).seeds(), [contract.MAX_SEED, 0, 1])

    def test_plan_first_needs_an_engine_with_a_planner(self):
        self.assertEqual(contract.validate(request(plan=True), CAPS), [])
        problems = contract.validate(request(plan=True), replace(CAPS, planner=False))
        self.assertIn("planner", problems[0])

    def test_plan_is_passed_to_the_engine_and_recorded(self):
        svc = service.MusicService(FakeMusicModel())
        result = svc.generate(request(candidates=1, plan=True))
        self.assertTrue(svc.model.calls[0][3]["plan"])
        library = AssetLibrary(svc.work_dir)
        self.assertTrue(service.keep(library, result, result.takes[0], "x").settings["plan"])
        svc.close()

    def test_a_newer_contract_version_is_refused(self):
        self.assertIn("version", contract.validate(request(contract_version=2), CAPS)[0])

    def test_check_raises_with_every_problem(self):
        with self.assertRaises(MusicRequestError) as raised:
            contract.check(request(prompt="", seconds=1000), CAPS)
        self.assertEqual(len(raised.exception.problems), 2)


class Service(unittest.TestCase):
    def setUp(self):
        self.svc = service.MusicService(FakeMusicModel())

    def tearDown(self):
        self.svc.close()

    def test_generates_validated_mastered_takes_with_provenance(self):
        result = self.svc.generate(request())
        self.assertEqual([take.seed for take in result.takes], [40, 41])
        self.assertEqual((result.model_revision, result.source_revision),
                         (catalog.ACE_STEP_15.model_revision, catalog.ACE_STEP_15.source_revision))
        take = result.takes[0]
        self.assertTrue(os.path.isfile(take.path))
        self.assertAlmostEqual(take.metrics["integrated_lufs"], service.MUSIC_LUFS, delta=0.5)
        self.assertLessEqual(take.metrics["true_peak_db"], -0.9)
        self.assertEqual(take.engine_notes, {"bpm": 92, "keyscale": "A minor"})
        self.assertEqual(result.peak_vram_mb, 9141)
        json.dumps(result.to_dict())                     # serialisable for an agent adapter

    def test_invalid_request_never_reaches_the_engine(self):
        with self.assertRaises(MusicRequestError):
            self.svc.generate(request(prompt=""))
        self.assertEqual(self.svc.model.calls, [])

    def test_a_missing_seed_is_chosen_and_recorded(self):
        result = self.svc.generate(request(seed=None, candidates=1))
        self.assertIsInstance(result.request.seed, int)
        self.assertEqual(result.takes[0].seed, result.request.seed)

    def test_wrong_length_or_silent_takes_are_rejected_and_leave_no_files(self):
        for model in (FakeMusicModel(length_factor=0.5), FakeMusicModel(silent=True)):
            svc = service.MusicService(model)
            with self.assertRaises(RuntimeError):
                svc.generate(request(candidates=1))
            self.assertEqual(os.listdir(svc.work_dir), [])
            svc.close()

    def test_engine_failure_propagates_and_keeps_earlier_takes_out_of_the_result(self):
        svc = service.MusicService(FakeMusicModel(fail_on=41))
        with self.assertRaisesRegex(RuntimeError, "out of memory"):
            svc.generate(request())
        self.assertEqual([n for n in os.listdir(svc.work_dir) if n.startswith("raw_")], [])
        svc.close()

    def test_cancel_between_takes_returns_what_finished(self):
        flags = iter([False, True])
        result = self.svc.generate(request(candidates=3), cancelled=lambda: next(flags, True))
        self.assertTrue(result.cancelled)
        self.assertEqual(len(result.takes), 1)

    def test_a_take_killed_mid_way_counts_as_cancelled(self):
        state = {"cancel": False}

        class Killed(FakeMusicModel):
            def generate_take(self, *args, **kwargs):
                state["cancel"] = True
                raise RuntimeError("The acestep worker stopped unexpectedly.")
        svc = service.MusicService(Killed())
        result = svc.generate(request(), cancelled=lambda: state["cancel"])
        self.assertTrue(result.cancelled)
        self.assertEqual(result.takes, [])
        svc.close()

    def test_progress_reports_each_take(self):
        seen = []
        self.svc.generate(request(candidates=2), progress=lambda done, total: seen.append((done, total)))
        self.assertEqual(seen, [(0, 2), (1, 2), (2, 2)])


class Library(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.library = AssetLibrary(self.tmp.name)
        self.svc = service.MusicService(FakeMusicModel())

    def tearDown(self):
        self.svc.close()
        self.tmp.cleanup()

    def test_keep_stores_a_verified_music_asset_with_full_provenance(self):
        result = self.svc.generate(request(candidates=1, bpm=92, key="A minor", genre="cinematic"))
        asset = service.keep(self.library, result, result.takes[0], "Opening theme")
        self.assertEqual((asset.kind, asset.engine, asset.model, asset.seed, asset.loop),
                         ("music", "ace_step_15", "ACE-Step/Ace-Step1.5", 40, False))
        self.assertTrue(self.library.verify(asset))
        self.assertEqual(asset.settings["model_revision"], catalog.ACE_STEP_15.model_revision)
        self.assertEqual((asset.settings["bpm"], asset.settings["key"]), (92, "A minor"))
        self.assertEqual(asset.metrics["sample_rate"], 48000)
        reopened = AssetLibrary(self.tmp.name)
        self.assertEqual(reopened.get(asset.id).kind, "music")

    def test_older_index_entries_read_as_sounds(self):
        os.makedirs(self.library.root, exist_ok=True)
        entry = {"id": "abc123abc123", "name": "Rain", "file": "Rain_abc123abc123.wav", "engine": "procedural",
                 "loop": True, "seconds": 2.0, "sample_rate": 48000, "sha256": "0", "created": 1.0}
        Path(self.library.index_path).write_text(json.dumps({"schema": 1, "assets": [entry]}), encoding="utf-8")
        self.assertEqual(AssetLibrary(self.tmp.name).assets[0].kind, "sound")

    def test_a_failed_index_write_leaves_no_orphaned_master(self):
        result = self.svc.generate(request(candidates=1))
        with mock.patch.object(AssetLibrary, "save", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                service.keep(self.library, result, result.takes[0], "Theme")
        self.assertEqual(self.library.assets, [])
        self.assertEqual(os.listdir(self.library.audio_dir), [])

    def test_keeping_a_vanished_take_fails_cleanly(self):
        result = self.svc.generate(request(candidates=1))
        os.remove(result.takes[0].path)
        with self.assertRaisesRegex(RuntimeError, "gone"):
            service.keep(self.library, result, result.takes[0], "Theme")


class EngineInstallState(unittest.TestCase):
    def test_not_installed_until_environment_worker_and_every_weight_exist(self):
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.object(music_models.engine_worker, "BASE_DIR", root):
            key = "ace_step_15"
            self.assertFalse(music_models.is_installed(key))
            python = music_models.engine_worker.venv_python("acestep")
            os.makedirs(os.path.dirname(python))
            Path(python).write_text("")
            Path(music_models.worker_path(key)).write_text("")
            self.assertEqual(len(music_models.missing_files(key)), 4)
            for name in music_models.SPECS[key].required_files:
                path = os.path.join(music_models.checkpoints_dir(key), name)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                Path(path).write_text("")
            self.assertTrue(music_models.is_installed(key))

    def test_starting_an_uninstalled_engine_says_so(self):
        with tempfile.TemporaryDirectory() as root, mock.patch.object(music_models.engine_worker, "BASE_DIR", root):
            with self.assertRaisesRegex(RuntimeError, "isn't installed"):
                music_models.MusicModel("ace_step_15")

    def test_cancel_ends_the_whole_worker_tree_on_windows(self):
        """The venv's python.exe is a launcher; killing only it left the model on the GPU."""
        model = music_models.MusicModel.__new__(music_models.MusicModel)
        process = mock.Mock(pid=4242)
        process.poll.return_value = None
        model.worker = mock.Mock(process=process)
        with mock.patch.object(music_models.os, "name", "nt"), \
                mock.patch.object(music_models.subprocess, "run") as run:
            model.terminate()
        self.assertEqual(run.call_args[0][0], ["taskkill", "/T", "/F", "/PID", "4242"])
        process.wait.assert_called_once()

    def test_job_estimate_counts_takes_length_planner_and_start(self):
        engine = catalog.ACE_STEP_15
        one = engine.take_seconds + 30 * engine.seconds_per_second
        self.assertAlmostEqual(catalog.job_seconds(engine, 30, 2, False, True), 2 * one)
        self.assertAlmostEqual(catalog.job_seconds(engine, 30, 2, True, True), 2 * (one + engine.plan_seconds))
        self.assertAlmostEqual(catalog.job_seconds(engine, 30, 1, False, False), one + engine.start_seconds)
        self.assertGreater(engine.vram_gb, 0)

    def test_consent_names_exact_revisions_license_and_size(self):
        text = catalog.consent_text(catalog.ACE_STEP_15)
        for fact in ("19671f4", "ca1e85f", "MIT License", "10 GB", "7 GB"):
            self.assertIn(fact, text)


if __name__ == "__main__":
    unittest.main()
