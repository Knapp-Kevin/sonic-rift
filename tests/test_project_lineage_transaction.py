"""Crash-window tests for the opt-in project+lineage journal prototype.

All tests use private, disposable files. No Qt, model runtime or native C2PA.
A recoverable journal is not an atomic two-file filesystem transaction.
"""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from this_voice_thing.core.audio_project import AudioProject, Clip, Track, save_project, read_project
from this_voice_thing.core.audio_project_session import ProjectSession
from this_voice_thing.core.project_lineage import ProjectLineage, load_lineage, save_lineage, sidecar_path
from this_voice_thing.core.project_lineage_transaction import (
    journal_path, recover_pair, save_pair,
)

DIGEST = "b" * 64


def project():
    return AudioProject(
        "tx-project", "Provenance transaction",
        tracks=[Track("voice-lane", "voice", "Narration",
                      [Clip("clip", "voice", 0, 128, asset_id="voice_" + DIGEST)])])


def ledger_with_event(doc):
    ledger = ProjectLineage(doc)
    ledger.capture(
        doc, "clip", origin="ai_generated", observer="studio_generator",
        media_sha256=DIGEST, engine="studio_tts_worker")
    return ledger


class TransactionJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "scene.sonicrift.json"
        self.first = project()
        save_project(self.path, self.first)
        self.ledger = ledger_with_event(self.first)

    def next_revision(self):
        session = ProjectSession(self.first)
        session.update_clip("clip", gain_db=-5.0)
        return session.project, self.ledger.advance(self.first, session.project)

    def test_atomic_like_install_has_readable_project_and_matching_lineage(self):
        revised, revised_ledger = self.next_revision()
        self.assertEqual(save_pair(self.path, self.first, revised, revised_ledger), "committed")
        self.assertEqual(read_project(self.path), revised)
        self.assertEqual(load_lineage(self.path).to_dict(revised),
                         revised_ledger.to_dict(revised))
        self.assertFalse(journal_path(self.path).exists())
        self.assertEqual(recover_pair(self.path), "no_pending_transaction")
        self.assertEqual(list(Path(self.tmp.name).glob("*.stage")), [])

    def test_crashes_at_each_boundary_allow_explicit_hash_guarded_rollforward(self):
        for marker in ("journal", "project", "lineage"):
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "mix.sonicrift.json"
                original = project()
                save_project(path, original)
                initial_lineage = ledger_with_event(original)
                save_lineage(path, initial_lineage)
                session = ProjectSession(original)
                session.update_clip("clip", gain_db=-3.0)
                revised = session.project
                next_lineage = initial_lineage.advance(original, revised)

                with self.assertRaisesRegex(RuntimeError, "Injected crash"):
                    save_pair(path, original, revised, next_lineage,
                              fail_after=marker)
                self.assertTrue(journal_path(path).is_file())
                if marker == "journal":
                    self.assertEqual(read_project(path), original)
                else:
                    self.assertEqual(read_project(path), revised)

                self.assertEqual(recover_pair(path), "committed")
                self.assertEqual(read_project(path), revised)
                self.assertEqual(load_lineage(path).to_dict(revised),
                                 next_lineage.to_dict(revised))
                self.assertFalse(journal_path(path).exists())
                self.assertEqual(recover_pair(path), "no_pending_transaction")

    def test_missing_previous_lineage_can_be_initialized_at_same_revision(self):
        self.assertFalse(sidecar_path(self.path).exists())
        self.assertEqual(save_pair(self.path, self.first, self.first, self.ledger),
                         "committed")
        self.assertEqual(load_lineage(self.path).event_for_clip(
            self.first, "clip")["origin"], "ai_generated")
        self.assertEqual(read_project(self.path).schema_version, 1)

    def test_conflicting_project_edit_blocks_recovery_without_overwrite(self):
        revised, next_ledger = self.next_revision()
        with self.assertRaises(RuntimeError):
            save_pair(self.path, self.first, revised, next_ledger,
                      fail_after="journal")
        external = deepcopy(self.first)
        external.tracks[0].clips[0].gain_db = -11.0
        save_project(self.path, external)
        original_bytes = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "conflict"):
            recover_pair(self.path)
        self.assertEqual(self.path.read_bytes(), original_bytes)
        self.assertTrue(journal_path(self.path).exists())

    def test_modified_or_missing_staged_files_block_recovery(self):
        revised, next_ledger = self.next_revision()
        with self.assertRaises(RuntimeError):
            save_pair(self.path, self.first, revised, next_ledger,
                      fail_after="journal")
        staged = list(Path(self.tmp.name).glob("*.stage"))
        self.assertEqual(len(staged), 2)
        staged[0].unlink()
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "Missing or altered staged"):
            recover_pair(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_concurrent_writer_cannot_start_a_new_transaction_over_journal(self):
        revised, next_ledger = self.next_revision()
        with self.assertRaises(RuntimeError):
            save_pair(self.path, self.first, revised, next_ledger,
                      fail_after="journal")
        with self.assertRaisesRegex(ValueError, "Pending lineage transaction"):
            save_pair(self.path, self.first, revised, next_ledger)
        self.assertEqual(read_project(self.path), self.first)

    def test_prior_events_cannot_be_removed_from_transaction(self):
        save_lineage(self.path, self.ledger)
        revised, valid_ledger = self.next_revision()
        invalid = deepcopy(valid_ledger)
        invalid.events.clear()
        invalid.bindings.clear()
        with self.assertRaisesRegex(ValueError, "delete or rewrite"):
            save_pair(self.path, self.first, revised, invalid)
        self.assertFalse(journal_path(self.path).exists())
        self.assertEqual(read_project(self.path), self.first)
        self.assertIsNotNone(load_lineage(self.path))

    def test_project_mutation_at_same_revision_is_refused_without_stages(self):
        modified = deepcopy(self.first)
        modified.tracks[0].clips[0].gain_db = -9.0
        original = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "newer revision"):
            save_pair(self.path, self.first, modified, self.ledger)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(journal_path(self.path).exists())
        self.assertEqual(list(Path(self.tmp.name).glob("*.stage")), [])

    def test_external_edit_during_candidate_validation_is_never_clobbered(self):
        from this_voice_thing.core import project_lineage_transaction as txn
        revised, new_ledger = self.next_revision()
        with self.assertRaises(RuntimeError):
            save_pair(self.path, self.first, revised, new_ledger,
                      fail_after="journal")
        original_parser = txn._lineage_from_bytes
        inserted = b"third-party changed the document during verification"

        def mutate_during_validation(encoded, candidate):
            ledger = original_parser(encoded, candidate)
            self.path.write_bytes(inserted)
            return ledger

        with patch.object(txn, "_lineage_from_bytes", side_effect=mutate_during_validation):
            with self.assertRaisesRegex(ValueError, "conflict"):
                recover_pair(self.path)
        self.assertEqual(self.path.read_bytes(), inserted)
        self.assertTrue(journal_path(self.path).is_file())

    def test_invalid_or_symlinked_journal_never_auto_recovers(self):
        marker = journal_path(self.path)
        marker.write_text('{"transaction_id": "../../elsewhere"}', encoding="utf-8")
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "invalid"):
            recover_pair(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_pending_transaction_does_not_expose_a_trusted_c2pa_claim(self):
        revised, next_ledger = self.next_revision()
        with self.assertRaises(RuntimeError):
            save_pair(self.path, self.first, revised, next_ledger,
                      fail_after="project")
        # A project can be on the new revision while the lineage file is
        # missing. No automatic AI claim may be inferred from this state.
        self.assertIsNone(load_lineage(self.path))
        self.assertTrue(journal_path(self.path).exists())
        self.assertEqual(recover_pair(self.path), "committed")
        self.assertEqual(load_lineage(self.path).to_dict(revised),
                         next_ledger.to_dict(revised))


if __name__ == "__main__":
    unittest.main()
