"""Procedural sounds and the shared mastering core (#63)."""

import os
import tempfile
import unittest

import numpy as np
import soundfile as sf

from this_voice_thing.core.soundscape import mastering, procedural

SR = procedural.SAMPLE_RATE
LOOPS = [key for key, preset in procedural.PRESETS.items() if preset.loop]
ONE_SHOTS = [key for key, preset in procedural.PRESETS.items() if not preset.loop]


class ProceduralTests(unittest.TestCase):
    def test_same_seed_same_sound_different_seed_different_sound(self):
        a = procedural.generate("rain", seconds=8, seed=4)
        b = procedural.generate("rain", seconds=8, seed=4)
        c = procedural.generate("rain", seconds=8, seed=5)
        np.testing.assert_array_equal(a, b)
        self.assertFalse(np.allclose(a, c))

    def test_shape_and_type(self):
        for key in LOOPS + ONE_SHOTS:
            seconds = 8 if key in LOOPS else None
            x = procedural.generate(key, seconds=seconds, seed=1)
            expected = seconds or procedural.PRESETS[key].default_seconds
            self.assertEqual(x.shape, (int(round(expected * SR)), 2), key)
            self.assertEqual(x.dtype, np.float32)
            self.assertTrue(np.all(np.isfinite(x)), key)

    def test_every_loop_is_seamless_after_mastering(self):
        for key in LOOPS:
            x = procedural.generate(key, seconds=20, seed=7, intensity=0.8)
            x = mastering.normalize(x, SR, procedural.PRESETS[key].target_lufs)
            report = mastering.seam_report(x, SR)
            self.assertTrue(report["seamless"], f"{key}: {report}")

    def test_width_zero_is_mono(self):
        x = procedural.generate("wind", seconds=6, seed=2, width=0.0)
        np.testing.assert_allclose(x[:, 0], x[:, 1], atol=1e-6)

    def test_loops_must_be_long_enough(self):
        with self.assertRaises(ValueError):
            procedural.generate("ocean", seconds=2)


class MasteringTests(unittest.TestCase):
    def test_normalize_hits_target_and_keeps_true_peak_headroom(self):
        x = procedural.generate("ocean", seconds=20, seed=3)
        out = mastering.normalize(x, SR, -20.0)
        self.assertAlmostEqual(mastering.integrated_lufs(out, SR), -20.0, delta=0.5)
        self.assertLessEqual(mastering.true_peak_db(out), mastering.TRUE_PEAK_CEILING_DB + 0.05)

    def test_peak_limit_wins_over_loudness_target(self):
        x = procedural.generate("storm", seconds=20, seed=3, intensity=1.0)
        out = mastering.normalize(x, SR, -6.0)  # unreachable without clipping
        self.assertLessEqual(mastering.true_peak_db(out), mastering.TRUE_PEAK_CEILING_DB + 0.05)
        self.assertLess(mastering.integrated_lufs(out, SR), -6.0)

    def test_a_lone_transient_does_not_pull_the_clip_below_target(self):
        x = procedural.generate("rain", seconds=20, seed=3)
        x[SR * 10: SR * 10 + 200] *= 5.0           # one click, ~5 dB over the ceiling once at target
        out = mastering.normalize(x, SR, -20.0)
        self.assertAlmostEqual(mastering.integrated_lufs(out, SR), -20.0, delta=0.5)
        self.assertLessEqual(mastering.true_peak_db(out), mastering.TRUE_PEAK_CEILING_DB + 0.05)
        # the limiter only touches the neighbourhood of the click
        gain = 10 ** ((-20.0 - mastering.integrated_lufs(x, SR)) / 20)
        np.testing.assert_allclose(out[: SR * 9], x[: SR * 9] * gain, rtol=1e-4, atol=1e-6)

    def test_one_shot_is_peak_normalized(self):
        x = procedural.generate("ui_success", seed=0)
        out = mastering.normalize(x, SR, procedural.PRESETS["ui_success"].target_lufs)
        self.assertLessEqual(mastering.true_peak_db(out), mastering.TRUE_PEAK_CEILING_DB + 0.05)
        self.assertGreater(np.max(np.abs(out)), 0.5)

    def test_make_loop_heals_a_clip_that_does_not_loop(self):
        rng = np.random.default_rng(0)
        t = np.arange(SR * 12) / SR
        # brown-ish noise drifting in level and pitch: its two ends don't match at all
        x = np.cumsum(rng.standard_normal((len(t), 2)), axis=0)
        x -= np.convolve(x[:, 0], np.ones(4801) / 4801, "same")[:, None]
        x *= np.linspace(0.2, 1.0, len(t))[:, None]
        x = (x / np.max(np.abs(x))).astype(np.float32)
        self.assertFalse(mastering.seam_report(x, SR)["seamless"])
        looped = mastering.make_loop(x, SR, crossfade_seconds=2.0)
        self.assertEqual(len(looped), len(x) - 2 * SR)
        self.assertTrue(mastering.seam_report(looped, SR)["seamless"])

    def test_export_writes_every_format_readably(self):
        x = mastering.normalize(procedural.generate("rain", seconds=30, seed=1), SR, -22.0)
        with tempfile.TemporaryDirectory() as tmp:
            paths = mastering.export(x, SR, os.path.join(tmp, "out", "rain"), formats=("wav", "ogg", "mp3"))
            for fmt, path in paths.items():
                self.assertTrue(os.path.getsize(path) > 1000, fmt)
                info = sf.info(path)
                self.assertEqual(info.channels, 2, fmt)
                self.assertAlmostEqual(info.duration, 30.0, delta=0.2, msg=fmt)

    def test_measure_reports_seam_only_for_loops(self):
        loop = mastering.measure(procedural.generate("drone", seconds=8, seed=0), SR, loop=True)
        shot = mastering.measure(procedural.generate("ui_notify", seed=0), SR, loop=False)
        self.assertIn("seam", loop)
        self.assertNotIn("seam", shot)


if __name__ == "__main__":
    unittest.main()


class WidenTests(unittest.TestCase):
    def test_widen_keeps_the_mid_and_the_loop_seamless(self):
        mono = procedural.generate("rain", seconds=12, seed=4, width=0.0)
        self.assertTrue(mastering.is_mono(mono))
        nearly = mono.copy()
        nearly[:, 1] += 0.001 * np.random.default_rng(0).standard_normal(len(nearly))  # SA3-like
        self.assertTrue(mastering.is_mono(nearly))
        wide = mastering.widen(mono, SR, width=0.8, loop=True)
        self.assertFalse(mastering.is_mono(wide))
        np.testing.assert_allclose(wide.mean(axis=1), mono[:, 0], atol=1e-5)   # folds back to the source
        self.assertTrue(mastering.seam_report(mastering.normalize(wide, SR, -22.0), SR)["seamless"])
        correlation = np.corrcoef(wide[:, 0], wide[:, 1])[0, 1]
        self.assertLess(correlation, 0.9)

    def test_width_zero_stays_mono_and_bass_stays_centred(self):
        t = np.arange(SR * 4) / SR
        bass = np.stack([np.sin(2 * np.pi * 60 * t)] * 2, 1).astype(np.float32) * 0.5
        self.assertTrue(mastering.is_mono(mastering.widen(bass, SR, width=0.0)))
        wide = mastering.widen(bass, SR, width=1.0, loop=False)
        side = (wide[:, 0] - wide[:, 1]) / 2
        self.assertLess(np.sqrt(np.mean(side ** 2)), 0.05 * np.sqrt(np.mean(bass[:, 0] ** 2)))


class SeamDetectionTests(unittest.TestCase):
    def test_flags_real_seams(self):
        t = np.arange(SR * 12) / SR
        cases = {
            "level trend": procedural.generate("rain", seconds=12, seed=1) * np.linspace(0.25, 1, len(t))[:, None],
            "tone cut mid-cycle": np.stack([np.sin(2 * np.pi * 110.37 * t)] * 2, 1) * 0.3,
            "change of sound": np.concatenate([procedural.generate("rain", seconds=6, seed=1),
                                               procedural.generate("wind", seconds=6, seed=2)]),
        }
        for name, x in cases.items():
            report = mastering.seam_report(mastering.normalize(x, SR, -20.0), SR)
            self.assertFalse(report["seamless"], f"{name}: {report}")


class CatalogTests(unittest.TestCase):
    def test_every_model_engine_states_license_and_download(self):
        from this_voice_thing.core.soundscape import catalog
        for engine in catalog.ENGINES.values():
            if engine.kind != "model":
                continue
            text = catalog.consent_text(engine)
            for fact in (engine.repo_id, engine.license_name, engine.license_url):
                self.assertIn(fact, text)
            self.assertGreater(engine.download_gb, 0)
            self.assertGreater(engine.max_seconds, 0)
        self.assertIn("gated", catalog.consent_text(catalog.SA3_SMALL_SFX))
        self.assertNotIn("gated", catalog.consent_text(catalog.MOSS_SFX_V2))

    def test_every_model_engine_has_an_install_spec(self):
        from this_voice_thing.core.soundscape import catalog
        from this_voice_thing.engines import sound_models
        models = {k for k, e in catalog.ENGINES.items() if e.kind == "model"}
        self.assertEqual(models, set(sound_models.SPECS))


class LoadErrorTests(unittest.TestCase):
    def test_gated_access_error_says_what_to_do(self):
        from this_voice_thing.core.soundscape import catalog
        from this_voice_thing.engines import sound_models
        raw = ("GatedRepoError: 403 Client Error. Access to model stabilityai/stable-audio-3-small-sfx is "
               "restricted and you are not in the authorized list.")
        text = sound_models.explain_load_error(catalog.SA3_SMALL_SFX, raw)
        self.assertIn("accept the terms", text)
        self.assertIn(catalog.SA3_SMALL_SFX.repo_id, text)
        self.assertEqual(sound_models.explain_load_error(catalog.SA3_SMALL_SFX, "other"), "other")


class StitchTests(unittest.TestCase):
    def test_plan_covers_the_length(self):
        from this_voice_thing.engines import sound_models
        for seconds, maximum in ((20, 30), (60, 30), (75, 30), (300, 120)):
            lengths = sound_models.plan_chunks(seconds, maximum)
            self.assertTrue(all(length <= maximum for length in lengths))
            overlap = sound_models.STITCH_OVERLAP_SECONDS * (len(lengths) - 1)
            self.assertGreaterEqual(sum(lengths) - overlap, seconds - 1e-6, (seconds, lengths))

    def test_stitch_length_and_continuity(self):
        from this_voice_thing.engines import sound_models
        rng = np.random.default_rng(1)
        takes = [rng.standard_normal((SR * 10, 2)).astype(np.float32) * 0.1 for _ in range(3)]
        out = sound_models.stitch(takes, SR, overlap_seconds=2.0)
        self.assertEqual(len(out), SR * (30 - 4))


class _FakeModel:
    """Stands in for a running SoundModel: noise that does not loop by itself."""

    def __init__(self, can_inpaint):
        self.can_inpaint = can_inpaint
        self.calls = []

    def generate(self, prompt, seconds, seed=0, **options):
        self.calls.append(("generate", prompt, seconds, seed))
        rng = np.random.default_rng(seed)
        x = np.cumsum(rng.standard_normal((int(seconds * SR), 2)), axis=0)
        x *= np.linspace(0.3, 1.0, len(x))[:, None]
        return (x / np.max(np.abs(x))).astype(np.float32), SR

    def heal_loop(self, audio, sample_rate, prompt, seed=0):
        self.calls.append(("heal", prompt, len(audio), seed))
        return mastering.make_loop(audio, sample_rate), sample_rate


class SoundModelLoopTests(unittest.TestCase):
    """The real SoundModel.heal_loop, with the worker replaced (no model needed)."""

    def _model(self, key, take=None):
        from this_voice_thing.engines import sound_models
        model = sound_models.SoundModel.__new__(sound_models.SoundModel)
        model.key, model.spec = key, sound_models.SPECS[key]
        model._temp, model._count = tempfile.mkdtemp(), 0
        model._take = take
        return model

    def test_folding_engine_returns_audio_and_rate(self):
        x = procedural.generate("rain", seconds=10, seed=1) * np.linspace(0.3, 1, SR * 10)[:, None]
        audio, rate = self._model("moss_sfx_v2").heal_loop(x, SR, "rain")
        self.assertEqual(rate, SR)
        self.assertEqual(len(audio), SR * 8)

    def test_inpainting_engine_rotates_and_regenerates_the_seam(self):
        calls = {}

        def take(prompt, seconds, seed, **options):
            calls.update(options, seconds=seconds)
            rotated, _ = __import__("soundfile").read(options["inpaint_path"], dtype="float32")
            return rotated, SR
        x = procedural.generate("rain", seconds=10, seed=1)
        audio, rate = self._model("sa3_small_sfx", take).heal_loop(x, SR, "rain")
        self.assertEqual((len(audio), rate), (len(x), SR))
        self.assertAlmostEqual(calls["inpaint_start"], 5.0 - 1.5, places=3)  # old wrap is now mid-clip
        self.assertAlmostEqual(calls["inpaint_end"], 5.0 + 1.5, places=3)
        np.testing.assert_allclose(audio[: SR * 5], x[SR * 5:], atol=1e-6)


class RenderTests(unittest.TestCase):
    def test_procedural_candidates_differ_by_seed_and_are_mastered(self):
        from this_voice_thing.core.soundscape import render
        request = render.SoundRequest(engine="procedural", preset="rain", seconds=10, seed=40, candidates=2)
        results = render.render(request)
        self.assertEqual([c.seed for c in results], [40, 41])
        self.assertFalse(np.allclose(results[0].audio, results[1].audio))
        for candidate in results:
            self.assertAlmostEqual(candidate.metrics["integrated_lufs"], -22.0, delta=0.6)
            self.assertTrue(candidate.metrics["seam"]["seamless"])

    def test_model_loops_are_healed_and_one_shots_are_not(self):
        from this_voice_thing.core.soundscape import render
        model = _FakeModel(can_inpaint=False)
        loop = render.render(render.SoundRequest(engine="moss_sfx_v2", prompt="rain", seconds=12,
                                                 candidates=1), model=model)
        self.assertIn("heal", [c[0] for c in model.calls])
        self.assertIn("seam", loop[0].metrics)
        self.assertAlmostEqual(loop[0].metrics["seconds"], 12 - mastering.LOOP_FOLD_SECONDS, delta=0.01)
        model.calls.clear()
        model.loop_padding_seconds = mastering.LOOP_FOLD_SECONDS   # what a folding SoundModel sets
        padded = render.render(render.SoundRequest(engine="moss_sfx_v2", prompt="rain", seconds=12,
                                                   candidates=1), model=model)
        self.assertAlmostEqual(padded[0].metrics["seconds"], 12.0, delta=0.01)
        model.calls.clear()
        render.render(render.SoundRequest(engine="moss_sfx_v2", prompt="door slam", seconds=3,
                                          loop=False, candidates=1), model=model)
        self.assertNotIn("heal", [c[0] for c in model.calls])

    def test_cancel_stops_between_candidates(self):
        from this_voice_thing.core.soundscape import render
        calls = []
        results = render.render(render.SoundRequest(engine="procedural", preset="wind", seconds=6, candidates=3),
                                cancelled=lambda: len(calls) >= 1, progress=lambda d, t: calls.append(d))
        self.assertEqual(len(results), 1)

    def test_model_engine_without_a_running_model_fails_clearly(self):
        from this_voice_thing.core.soundscape import render
        with self.assertRaises(RuntimeError):
            render.render(render.SoundRequest(engine="sa3_small_sfx", prompt="x", seconds=5))


class AssetLibraryTests(unittest.TestCase):
    def test_keep_reload_rename_export_and_remove(self):
        from this_voice_thing.core.soundscape import assets
        audio = mastering.normalize(procedural.generate("ocean", seconds=8, seed=2), SR, -20.0)
        with tempfile.TemporaryDirectory() as tmp:
            library = assets.AssetLibrary(tmp)
            asset = library.add(audio, SR, "Gentle ocean", "procedural", True, preset="ocean", seed=2,
                                settings={"intensity": 0.5}, license="Your own work")
            self.assertTrue(library.verify(asset))
            self.assertIn("seam", asset.metrics)
            again = assets.AssetLibrary(tmp)             # persisted
            self.assertEqual(again.get(asset.id).sha256, asset.sha256)
            self.assertEqual(again.get(asset.id).settings, {"intensity": 0.5})
            again.rename(asset.id, "Ocean, calm")
            self.assertEqual(assets.AssetLibrary(tmp).get(asset.id).name, "Ocean, calm")
            out = again.export(asset.id, os.path.join(tmp, "exports", "ocean"), formats=("ogg", "mp3"))
            self.assertEqual(set(out), {"ogg", "mp3"})
            self.assertIn("preset ocean", again.provenance_text(again.get(asset.id)))
            master = again.path(again.get(asset.id))
            self.assertTrue(again.remove(asset.id))
            self.assertFalse(os.path.exists(master))
            self.assertEqual(assets.AssetLibrary(tmp).assets, [])

    def test_tampered_master_fails_verification(self):
        from this_voice_thing.core.soundscape import assets
        with tempfile.TemporaryDirectory() as tmp:
            library = assets.AssetLibrary(tmp)
            asset = library.add(procedural.generate("ui_notify", seed=0), SR, "Bell", "procedural", False)
            with open(library.path(asset), "ab") as handle:
                handle.write(b"x")
            self.assertFalse(library.verify(asset))
