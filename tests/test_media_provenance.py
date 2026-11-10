"""Source-origin assessment uses evidence rather than AI-content guessing.

No PySide6, model execution, network or media mutation.
"""
from copy import deepcopy
from types import SimpleNamespace
import unittest

from this_voice_thing.core.audio_project import AudioProject, Clip, Track
from this_voice_thing.core.media_provenance import project_origin_inventory


def _asset(engine, model="", revision=None):
    settings = {"model_revision": revision} if revision is not None else {}
    return SimpleNamespace(engine=engine, model=model, settings=settings, sha256="f" * 64)


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
            "ace_step_15", ACE_STEP_15.repo_id, ACE_STEP_15.model_revision)})
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
            model_ids[0]: _asset("ace_step_15", ACE_STEP_15.repo_id),
            model_ids[1]: _asset("moss_sfx_v2", "OpenMOSS-Team/MOSS-SoundEffect-v2.0"),
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
        library = Library({"a" * 12: _asset("procedural")})
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
        library = Library({id_: _asset("ace_step_15", model="someone-else/fake")})
        inventory = project_origin_inventory(project, library)
        self.assertEqual(inventory["classification"], "unknown")
        self.assertEqual(inventory["ingredients"][0]["evidence"],
                         "conflicting_local_engine_claim")

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

    def test_empty_project_is_not_declared_human(self):
        inventory = project_origin_inventory(AudioProject("e", "Empty"), Library())
        self.assertEqual(inventory["classification"], "unknown")
        self.assertEqual(inventory["ingredients"], [])


if __name__ == "__main__":
    unittest.main()
