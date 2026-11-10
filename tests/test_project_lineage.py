"""Per-clip creation-event identity: version-one projects stay untouched.

The ledger holds *unsigned local assertions*. These tests prove safe identity,
binding and fail-closed persistence, not trusted C2PA authentication.
"""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from this_voice_thing.core.audio_project import (
    AudioProject, Clip, Track, read_project, save_project,
)
from this_voice_thing.core.audio_project_session import ProjectSession
from this_voice_thing.core.project_lineage import (
    ProjectLineage, load_lineage, save_lineage, sidecar_path,
)

DIGEST = "a" * 64
MEDIA = "voice_" + DIGEST
OTHER = "voice_" + "b" * 64


def make_project():
    return AudioProject(
        "scene", "Origins",
        tracks=[Track("voice-track", "voice", "Narration", [
            Clip("generated", "voice", 0, 200, asset_id=MEDIA),
            Clip("imported", "voice", 300, 200, asset_id=MEDIA),
        ])])


def capture_two(project):
    lineage = ProjectLineage(project)
    gen = lineage.capture(
        project, "generated", origin="ai_generated",
        observer="studio_generator", media_sha256=DIGEST, engine="studio_tts_worker")
    imported = lineage.capture(
        project, "imported", origin="unknown",
        observer="import_unknown", media_sha256=DIGEST)
    return lineage, gen, imported


class ProjectLineageTests(unittest.TestCase):
    def test_identical_voice_bytes_keep_distinct_creation_events(self):
        project = make_project()
        ledger, gen, imported = capture_two(project)
        self.assertNotEqual(gen, imported)
        self.assertEqual(ledger.event_for_clip(project, "generated")["origin"], "ai_generated")
        self.assertEqual(ledger.event_for_clip(project, "imported")["origin"], "unknown")
        self.assertEqual(ledger.event_for_clip(project, "generated")["asset_id"], MEDIA)
        self.assertEqual(ledger.event_for_clip(project, "imported")["media_sha256"], DIGEST)
        self.assertEqual(len(ledger.events), 2)
        self.assertEqual(len(ledger.bindings), 2)

    def test_version_one_project_save_reopen_and_separate_sidecar(self):
        project = make_project()
        ledger, gen, imported = capture_two(project)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mix.sonicrift.json"
            save_project(path, project)
            original = path.read_bytes()
            output = save_lineage(path, ledger)
            self.assertEqual(output, sidecar_path(path))
            self.assertEqual(path.read_bytes(), original)
            raw = json.loads(original)
            self.assertEqual(raw["schema_version"], 1)
            self.assertNotIn("creation_event_id", json.dumps(raw))
            reopened_project = read_project(path)
            loaded = load_lineage(path)
            self.assertEqual(loaded.to_dict(reopened_project), ledger.to_dict(project))
            self.assertNotEqual(loaded.bindings["generated"], loaded.bindings["imported"])
            self.assertEqual(loaded.event_for_clip(reopened_project, "generated")["event_id"], gen)
            self.assertEqual(loaded.event_for_clip(reopened_project, "imported")["event_id"], imported)
            self.assertEqual(path.read_bytes(), original)

    def test_nonexistent_sidecar_proves_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mix.sonicrift.json"
            save_project(path, make_project())
            self.assertIsNone(load_lineage(path))

    def test_split_and_copy_reuse_original_event_only_when_explicitly_bound(self):
        project = make_project()
        ledger, original_event, _ = capture_two(project)
        session = ProjectSession(project)
        start = deepcopy(session.project)
        session.add_clip("voice-track", Clip("split", "voice", 125, 75,
                                             asset_id=MEDIA, source_offset_frames=125))
        updated = ledger.advance(start, session.project)
        self.assertIsNone(updated.event_for_clip(session.project, "split"))
        updated.bind_existing(session.project, "split", original_event)
        self.assertEqual(updated.event_for_clip(session.project, "split")["event_id"],
                         original_event)
        self.assertEqual(updated.event_for_clip(session.project, "generated")["event_id"],
                         original_event)
        self.assertNotEqual(updated.event_for_clip(session.project, "imported")["event_id"],
                            original_event)

    def test_replacing_source_drops_stale_binding_without_relabeling(self):
        project = make_project()
        ledger, _, _ = capture_two(project)
        session = ProjectSession(project)
        old = deepcopy(session.project)
        session.update_clip("imported", asset_id=OTHER)
        updated = ledger.advance(old, session.project)
        self.assertIsNone(updated.event_for_clip(session.project, "imported"))
        self.assertEqual(updated.event_for_clip(session.project, "generated")["origin"],
                         "ai_generated")
        self.assertRaisesRegex(
            ValueError, "does not match target clip",
            updated.bind_existing, session.project, "imported", ledger.bindings["generated"])
        with self.assertRaisesRegex(ValueError, "Stale"):
            ledger.event_for_clip(session.project, "generated")

    def test_undo_redo_only_retain_matching_event_bindings(self):
        project = make_project()
        ledger, gen, _ = capture_two(project)
        session = ProjectSession(project)
        original = deepcopy(session.project)
        session.update_clip("generated", gain_db=-6.0)
        edited = deepcopy(session.project)
        current = ledger.advance(original, edited)
        self.assertTrue(session.undo())
        undone = deepcopy(session.project)
        current = current.advance(edited, undone)
        self.assertEqual(current.event_for_clip(undone, "generated")["event_id"], gen)
        self.assertEqual(undone.tracks[0].clips[0].gain_db, 0.0)
        self.assertTrue(session.redo())
        redone = deepcopy(session.project)
        current = current.advance(undone, redone)
        self.assertEqual(current.event_for_clip(redone, "generated")["event_id"], gen)
        self.assertEqual(redone.tracks[0].clips[0].gain_db, -6.0)

    def test_unsigned_ledger_cannot_assert_human_capture(self):
        project = make_project()
        ledger = ProjectLineage(project)
        with self.assertRaises((ValueError, TypeError)):
            ledger.capture(project, "generated", origin="human_capture",
                           observer="studio_generator", media_sha256=DIGEST,
                           engine="studio_tts_worker")
        with self.assertRaises((ValueError, TypeError)):
            ledger.capture(project, "generated", origin="ai_generated",
                           observer="import_unknown", media_sha256=DIGEST)
        self.assertEqual(ledger.events, {})
        self.assertEqual(ledger.bindings, {})

    def test_bad_media_digest_and_wrong_asset_refuse_binding(self):
        project = make_project()
        ledger = ProjectLineage(project)
        with self.assertRaisesRegex(ValueError, "content address"):
            ledger.capture(project, "generated", origin="ai_generated",
                           observer="studio_generator", media_sha256="b" * 64,
                           engine="studio_tts_worker")
        recorded = ledger.capture(project, "generated", origin="ai_generated",
                                  observer="studio_generator", media_sha256=DIGEST,
                                  engine="studio_tts_worker")
        session = ProjectSession(project)
        session.update_clip("imported", asset_id=OTHER)
        current = ledger.advance(project, session.project)
        with self.assertRaisesRegex(ValueError, "does not match target clip"):
            current.bind_existing(session.project, "imported", recorded)

    def test_tampered_sidecar_and_stale_project_must_not_upgrade_origin(self):
        project = make_project()
        ledger, _, _ = capture_two(project)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mix.sonicrift.json"
            save_project(path, project)
            sidecar = save_lineage(path, ledger)
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            data["bindings"]["generated"] = "f" * 32
            sidecar.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_lineage(path)
            with self.assertRaisesRegex(ValueError, "corrupted"):
                save_lineage(path, ledger)
            # Restore a valid sidecar on a new scratch project.
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mix.sonicrift.json"
            save_project(path, project)
            save_lineage(path, ledger)
            session = ProjectSession(project)
            session.update_clip("generated", gain_db=-12)
            save_project(path, session.project)
            with self.assertRaisesRegex(ValueError, "Stale"):
                load_lineage(path)

    def test_valid_revision_advance_keeps_content_mapping_and_persists_new_snapshot(self):
        project = make_project()
        ledger, _, _ = capture_two(project)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mix.sonicrift.json"
            save_project(path, project)
            save_lineage(path, ledger)
            session = ProjectSession(project)
            previous = deepcopy(session.project)
            session.update_clip("generated", gain_db=-6.0)
            advanced = ledger.advance(previous, session.project)
            save_project(path, session.project)
            save_lineage(path, advanced)
            loaded = load_lineage(path)
            self.assertEqual(loaded.event_for_clip(session.project, "generated")["origin"],
                             "ai_generated")
            self.assertEqual(loaded.project_revision, session.project.revision)

    def test_event_history_cannot_be_erased_on_sidecar_update(self):
        project = make_project()
        ledger, first, second = capture_two(project)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mix.sonicrift.json"
            save_project(path, project)
            saved = save_lineage(path, ledger)
            original = saved.read_bytes()
            removed = deepcopy(ledger)
            del removed.events[first]
            del removed.bindings["generated"]
            with self.assertRaisesRegex(ValueError, "discard or rewrite"):
                save_lineage(path, removed)
            self.assertEqual(saved.read_bytes(), original)
            self.assertEqual(load_lineage(path).event_for_clip(
                project, "imported")["event_id"], second)

    def test_untrusted_event_payloads_cannot_be_imported_as_human_or_validated(self):
        project = make_project()
        ledger, _, _ = capture_two(project)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mix.sonicrift.json"
            save_project(path, project)
            saved = save_lineage(path, ledger)
            payload = json.loads(saved.read_text(encoding="utf-8"))
            payload["events"][0]["origin"] = ["human_capture"]
            saved.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises((ValueError, TypeError)):
                load_lineage(path)
            self.assertFalse(hasattr(ledger, "signature"))
            self.assertNotIn("prompt", saved.read_text(encoding="utf-8"))

    def test_corrupt_replacement_and_cross_project_overwrite_refused(self):
        project = make_project()
        ledger, _, _ = capture_two(project)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mix.sonicrift.json"
            save_project(path, project)
            output = save_lineage(path, ledger)
            output.write_text("{not json", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "corrupted"):
                save_lineage(path, ledger)
            output.unlink()
            ledger.project_id = "wrong"
            with self.assertRaisesRegex(ValueError, "Stale"):
                save_lineage(path, ledger)


if __name__ == "__main__":
    unittest.main()
