"""Source-origin assessment uses evidence rather than AI-content guessing.

No PySide6, model execution, network or media mutation.
"""
from copy import deepcopy
from types import SimpleNamespace
from pathlib import Path
import tempfile
import unittest

import numpy as np

from this_voice_thing.core.audio_project import AudioProject, Clip, Track
from this_voice_thing.core.media_provenance import project_origin_inventory


def _asset(engine, model="", revision=None, recorded=False):
    settings = {"model_revision": revision} if revision is not None else {}
    source_event = ({
        "origin": "non_ai_synthesis" if engine == "procedural" else "ai_generated",
        "engine": engine,
        "model_id": model,
        "model_revision": revision or "",
        "media_sha256": "f" * 64,
        "evidence_status": "unsigned_local_generation_event",
    } if recorded else {})
    return SimpleNamespace(
        engine=engine, model=model, settings=settings, sha256="f" * 64,
        source_event=source_event)


class Library:
    def __init__(self, assets=None, verified=True):
        self.assets = assets or {}
        self.verified = verified
        self.checked = []

    def get(self, key):
        return self.assets.get(key)

    def verify(self, asset):
        self.checked.append(asset)
        return self.verified


def _project(*clips):
    tracks = []
    for kind, items in (("sound", [c for c in clips if c.kind == "sound"]),
                        ("voice", [c for c in clips if c.kind == "voice"])):
        if items:
            tracks.append(Track(kind + "-track", kind, kind.title(), items))
    return AudioProject("mix", "Provenance", tracks=tracks)


class OriginInventoryTests(unittest.TestCase):
    def test_ai_music_claim_includes_exact_recorded_model_revision(self):
        from this_voice_thing.core.music.catalog import ACE_STEP_15
        id_ = "a" * 12
        library = Library({id_: _asset(
            "ace_step_15", ACE_STEP_15.repo_id, ACE_STEP_15.model_revision, recorded=True)})
        project = _project(Clip("music", "sound", 0, 480, asset_id="sound_" + id_))
        original = deepcopy(project)
        inventory = project_origin_inventory(project, library)

        self.assertEqual(inventory["classification"], "ai_generated")
        self.assertTrue(inventory["contains_ai"])
        self.assertFalse(inventory["contains_unknown"])
        self.assertEqual(inventory["model_ids"], [ACE_STEP_15.repo_id])
        self.assertEqual(inventory["ingredients"][0]["model_revision"],
                         ACE_STEP_15.model_revision)
        self.assertEqual(inventory["evidence_status"],
                         "unsigned_unverified_local_inventory")
        self.assertEqual(project, original)
        self.assertEqual(len(library.checked), 1)

    def test_multiple_engines_and_unknown_voice_yield_honest_mixed_status(self):
        from this_voice_thing.core.music.catalog import ACE_STEP_15
        model_ids = ["a" * 12, "b" * 12]
        library = Library({
            model_ids[0]: _asset(
                "ace_step_15", ACE_STEP_15.repo_id,
                ACE_STEP_15.model_revision, recorded=True),
            model_ids[1]: _asset("moss_sfx_v2", "OpenMOSS-Team/MOSS-SoundEffect-v2.0", recorded=True),
        })
        project = _project(
            Clip("music", "sound", 0, 250, asset_id="sound_" + model_ids[0]),
            Clip("sound", "sound", 10, 100, asset_id="sound_" + model_ids[1]),
            Clip("voice", "voice", 20, 90, asset_id="voice_" + "c" * 64))
        inventory = project_origin_inventory(project, library)
        self.assertEqual(inventory["classification"], "mixed_ai_and_other")
        self.assertTrue(inventory["contains_unknown"])
        self.assertEqual(len(inventory["model_ids"]), 2)
        self.assertEqual(inventory["ingredients"][-1]["origin"], "unknown")
        self.assertEqual(inventory["ingredients"][-1]["evidence"],
                         "voice_origin_unrecorded")
        self.assertIsNone(inventory["ingredients"][-1]["media_sha256"])
        self.assertNotIn("prompt", str(inventory))
        self.assertNotIn("seed", str(inventory))

    def test_procedural_synthesis_is_not_misreported_as_human_capture(self):
        library = Library({"a" * 12: _asset("procedural", recorded=True)})
        project = _project(Clip("waves", "sound", 0, 10, asset_id="sound_" + "a" * 12))
        inventory = project_origin_inventory(project, library)
        self.assertEqual(inventory["classification"], "non_ai_synthesis")
        self.assertEqual(inventory["ingredients"][0]["origin"], "non_ai_synthesis")
        self.assertFalse(inventory["contains_ai"])

    def test_missing_and_tampered_sources_must_not_claim_ai(self):
        id_ = "a" * 12
        project = _project(Clip("waves", "sound", 0, 10, asset_id="sound_" + id_))
        self.assertEqual(project_origin_inventory(project, Library())[
            "classification"], "unknown")
        library = Library({id_: _asset("ace_step_15")}, verified=False)
        inventory = project_origin_inventory(project, library)
        self.assertFalse(inventory["contains_ai"])
        self.assertEqual(inventory["ingredients"][0]["evidence"],
                         "media_missing_or_modified")

    def test_conflicting_model_claim_refuses_classification(self):
        id_ = "a" * 12
        project = _project(Clip("waves", "sound", 0, 10, asset_id="sound_" + id_))
        library = Library({id_: _asset("ace_step_15", model="someone-else/fake", recorded=True)})
        inventory = project_origin_inventory(project, library)
        self.assertEqual(inventory["classification"], "unknown")
        self.assertEqual(inventory["ingredients"][0]["evidence"],
                         "conflicting_local_generation_event")

    def test_recognized_legacy_engine_labels_are_still_unknown_without_events(self):
        from this_voice_thing.core.music.catalog import ACE_STEP_15
        for engine, model in (
                ("ace_step_15", ACE_STEP_15.repo_id),
                ("moss_sfx_v2", "OpenMOSS-Team/MOSS-SoundEffect-v2.0"),
                ("procedural", "")):
            with self.subTest(engine=engine):
                project = _project(Clip(
                    "old", "sound", 0, 100, asset_id="sound_" + "a" * 12))
                library = Library({"a" * 12: _asset(engine, model)})
                report = project_origin_inventory(project, library)
                self.assertEqual(report["classification"], "unknown")
                self.assertFalse(report["contains_ai"])
                self.assertEqual(report["ingredients"][0]["evidence"],
                                 "legacy_engine_label_without_event")

    def test_malformed_origin_index_is_unknown_not_crash_or_ai(self):
        source_id = "a" * 12
        project = _project(Clip("bad", "sound", 0, 100,
                                asset_id="sound_" + source_id))
        for event in (["invalid", {"untrusted": ["nested"]}, "free text"):
            with self.subTest(event=event):
                asset = _asset("ace_step_15", "ACE-Step/Ace-Step1.5")
                asset.source_event = event
                inventory = project_origin_inventory(
                    project, Library({source_id: asset}))
                self.assertEqual(inventory["classification"], "unknown")
                self.assertFalse(inventory["contains_ai"])
                self.assertEqual(inventory["ingredients"][0]["evidence"],
                                 "invalid_local_generation_event")

    def test_same_byte_voice_origin_collision_stays_unknown_in_final_inventory(self):
        from this_voice_thing.core.audio_project_media import ProjectMedia
        from this_voice_thing.core.soundscape.assets import AssetLibrary
        with tempfile.TemporaryDirectory() as dirname:
            library = AssetLibrary(dirname)
            media = ProjectMedia(Path(dirname), library)
            source = np.linspace(-0.1, 0.1, 480, dtype=np.float32)
            generated = media.import_generated_voice_take(source, 48000)
            project = _project(Clip(
                "spoken", "voice", 0, 480, asset_id=generated))
            self.assertTrue(project_origin_inventory(
                project, library, voice_media=media)["contains_ai"])
            self.assertEqual(media.import_voice_take(source, 48000), generated)
            report = project_origin_inventory(project, library, voice_media=media)
            self.assertEqual(report["classification"], "unknown")
            self.assertFalse(report["contains_ai"])
            self.assertTrue(report["contains_unknown"])
            self.assertIsNone(report["ingredients"][0]["media_sha256"])

    def test_legacy_engine_and_unrendered_clips_remain_unknown(self):
        id_ = "a" * 12
        project = _project(
            Clip("legacy", "sound", 0, 2, asset_id="sound_" + id_),
            Clip("draft", "voice", 10, 0, text="A private sentence"))
        inventory = project_origin_inventory(project, Library({id_: _asset("old-engine")}))
        self.assertTrue(inventory["contains_unknown"])
        self.assertFalse(inventory["contains_ai"])
        self.assertEqual(inventory["ingredients"][-1]["evidence"], "not_rendered")
        self.assertNotIn("A private sentence", str(inventory))

    def test_duplicate_uses_same_source_reference_but_distinct_clip_identity(self):
        id_ = "a" * 12
        project = _project(
            Clip("a", "sound", 0, 10, asset_id="sound_" + id_),
            Clip("b", "sound", 20, 10, asset_id="sound_" + id_,
                 source_offset_frames=2))
        inventory = project_origin_inventory(project, Library({id_: _asset("procedural")}))
        self.assertEqual(len(inventory["ingredients"]), 2)
        self.assertEqual([row["clip_id"] for row in inventory["ingredients"]], ["a", "b"])
        self.assertEqual([row["source_offset_frames"] for row in inventory["ingredients"]], [0, 2])

    def test_sound_generation_event_is_bound_to_audio_and_exposes_no_prompt(self):
        from this_voice_thing.core.soundscape.assets import AssetLibrary
        from this_voice_thing.core.music.catalog import ACE_STEP_15
        with tempfile.TemporaryDirectory() as dirname:
            library = AssetLibrary(dirname)
            audio = np.zeros((480, 2), dtype=np.float32)
            generated = library.add(
                audio, 48000, "Private piece", "ace_step_15", False,
                kind="music", model=ACE_STEP_15.repo_id,
                settings={"model_revision": ACE_STEP_15.model_revision},
                prompt="secret private writing prompt",
                metrics={"test": True}, source_event={
                    "origin": "ai_generated", "engine": "ace_step_15",
                    "model_id": ACE_STEP_15.repo_id,
                    "model_revision": ACE_STEP_15.model_revision,
                })
            self.assertEqual(generated.source_event["media_sha256"], generated.sha256)
            self.assertNotIn("secret", str(generated.source_event))
            project = _project(Clip(
                "piece", "sound", 0, 480, asset_id="sound_" + generated.id))
            original = project_origin_inventory(project, library)
            self.assertEqual(original["classification"], "ai_generated")
            self.assertEqual(original["ingredients"][0]["evidence"],
                             "unsigned_local_generation_event")
            self.assertNotIn("secret", str(original))
            # Index edits alone must not permit fabricated identity to pass
            # an internally consistent event/engine crosscheck.
            generated.source_event["model_id"] = "forged/model"
            self.assertEqual(project_origin_inventory(project, library)["classification"], "unknown")
            generated.source_event["model_id"] = ACE_STEP_15.repo_id
            generated.source_event["media_sha256"] = "0" * 64
            self.assertEqual(project_origin_inventory(project, library)["classification"], "unknown")

    def test_studio_generated_voice_is_ai_but_file_import_remains_unknown(self):
        from this_voice_thing.core.audio_project_media import ProjectMedia
        from this_voice_thing.core.soundscape.assets import AssetLibrary
        with tempfile.TemporaryDirectory() as dirname:
            library = AssetLibrary(dirname)
            media = ProjectMedia(Path(dirname), library)
            source = np.linspace(-0.2, 0.2, 480, dtype=np.float32)
            generated = media.import_generated_voice_take(source, 48000)
            imported = media.import_voice_take(source * 0.5, 48000)
            project = _project(
                Clip("spoken", "voice", 0, 480, asset_id=generated),
                Clip("unknown", "voice", 480, 480, asset_id=imported))
            without_media = project_origin_inventory(project, library)
            self.assertTrue(without_media["contains_unknown"])
            self.assertFalse(without_media["contains_ai"])
            inventory = project_origin_inventory(project, library, voice_media=media)
            self.assertTrue(inventory["contains_ai"])
            self.assertTrue(inventory["contains_unknown"])
            self.assertEqual(inventory["classification"], "mixed_ai_and_other")
            self.assertEqual(inventory["ingredients"][0]["origin"], "ai_generated")
            self.assertEqual(inventory["ingredients"][1]["origin"], "unknown")
            self.assertEqual(inventory["ingredients"][0]["engine"], "studio_tts_worker")
            self.assertEqual(inventory["ingredients"][0]["evidence"],
                             "unsigned_local_generation_event")

    def test_invalid_event_rejected_at_library_creation(self):
        from this_voice_thing.core.soundscape.assets import AssetLibrary
        with tempfile.TemporaryDirectory() as dirname:
            library = AssetLibrary(dirname)
            with self.assertRaisesRegex(ValueError, "Invalid local generation"):
                library.add(np.zeros(100, dtype=np.float32), 48000, "Bad", "procedural",
                            False, metrics={"test": True},
                            source_event={"origin": "ai_generated"})
            self.assertEqual(library.assets, [])

    def test_empty_project_is_not_declared_human(self):
        inventory = project_origin_inventory(AudioProject("e", "Empty"), Library())
        self.assertEqual(inventory["classification"], "unknown")
        self.assertEqual(inventory["ingredients"], [])


if __name__ == "__main__":
    unittest.main()
