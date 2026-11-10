"""Stage B agent queue: isolated SQLite and simulated workers; no model/Qt load."""
from pathlib import Path
import sqlite3
import tempfile
import unittest

from this_voice_thing.core.agent_queue import AgentQueue, AgentQueueError

PLAN = "a" * 64
PLAN2 = "b" * 64
MODEL = "ACE-Step/Ace-Step1.5"
WORKER = "c" * 32
WORKER2 = "d" * 32
KEY = "task-0001"


class Clock:
    def __init__(self):
        self.value = 1700000000.0

    def __call__(self):
        return self.value


class AgentQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.file = Path(self.temp.name) / "agent-jobs.sqlite"
        self.clock = Clock()
        self.auth = lambda owner, kind, model, plan, proof: proof == "locally-approved"
        self.models = lambda kind: [MODEL] if kind == "music.generate" else []
        self.queue = self.new_queue()
        self.addCleanup(self.queue.close)

    def new_queue(self, **changes):
        options = dict(authorize=self.auth, installed_models=self.models, clock=self.clock)
        options.update(changes)
        return AgentQueue(self.file, **options)

    def submit(self, **changes):
        options = dict(
            principal="owner", request_key=KEY, kind="music.generate",
            model_id=MODEL, plan_sha256=PLAN, grant_proof="locally-approved")
        options.update(changes)
        return self.queue.submit(**options)

    def test_default_deny_requires_real_registry_and_authority(self):
        with tempfile.TemporaryDirectory() as folder:
            q = AgentQueue(Path(folder) / "blocked.sqlite", installed_models=self.models)
            self.addCleanup(q.close)
            with self.assertRaisesRegex(AgentQueueError, "permission unavailable"):
                q.submit(principal="owner", request_key=KEY,
                         kind="music.generate", model_id=MODEL, plan_sha256=PLAN)
        with self.assertRaisesRegex(AgentQueueError, "permission refused"):
            self.submit(grant_proof="agent-says-yes")
        with self.assertRaisesRegex(AgentQueueError, "not installed"):
            self.submit(kind="sound.generate")
        self.assertEqual(self.queue.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 0)

    def test_idempotency_returns_same_job_without_echoing_secrets(self):
        first = self.submit()
        second = self.submit()
        self.assertEqual(first, second)
        self.assertEqual(first["state"], "queued")
        self.assertNotIn("principal", first)
        self.assertNotIn("request_key", first)
        self.assertNotIn("grant_proof", first)
        self.assertNotIn("lease_owner", first)
        with self.assertRaisesRegex(AgentQueueError, "another request"):
            self.submit(plan_sha256=PLAN2)
        rows = self.queue.db.execute("SELECT * FROM jobs").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertNotIn(KEY, str(tuple(rows[0])))
        self.assertNotIn("locally-approved", str(tuple(rows[0])))

    def test_one_running_job_even_across_two_worker_claims(self):
        first = self.submit()
        second = self.submit(request_key="task-0002", plan_sha256=PLAN2)
        running = self.queue.claim(worker_id=WORKER)
        self.assertEqual(running["state"], "running")
        self.assertEqual(running["job_id"], first["job_id"])
        self.assertIsNone(self.queue.claim(worker_id=WORKER2))
        self.assertTrue(self.queue.heartbeat(first["job_id"], WORKER))
        with self.assertRaisesRegex(AgentQueueError, "no active owner"):
            self.queue.finish(first["job_id"], worker_id=WORKER2,
                              state="completed", artifact_id="asset_valid",
                              artifact_sha256="e" * 64)
        self.queue.finish(first["job_id"], worker_id=WORKER,
                          state="completed", artifact_id="asset_valid",
                          artifact_sha256="e" * 64)
        self.assertEqual(self.queue.claim(worker_id=WORKER2)["job_id"], second["job_id"])

    def test_read_caller_isolation_and_cancel_queued(self):
        job = self.submit()
        with self.assertRaisesRegex(AgentQueueError, "unavailable"):
            self.queue.get(job["job_id"], principal="stranger")
        with self.assertRaisesRegex(AgentQueueError, "unavailable"):
            self.queue.cancel(job["job_id"], principal="stranger")
        cancelled = self.queue.cancel(job["job_id"], principal="owner")
        self.assertEqual(cancelled["state"], "cancelled")
        self.assertIsNone(self.queue.claim(worker_id=WORKER))

    def test_running_cancel_never_publishes_result(self):
        job = self.submit()
        self.queue.claim(worker_id=WORKER)
        self.assertEqual(
            self.queue.cancel(job["job_id"], principal="owner")["state"],
            "cancel_requested")
        self.assertFalse(self.queue.heartbeat(job["job_id"], WORKER))
        with self.assertRaisesRegex(AgentQueueError, "cannot publish"):
            self.queue.finish(job["job_id"], worker_id=WORKER,
                              state="completed", artifact_id="asset_valid",
                              artifact_sha256="e" * 64)
        stopped = self.queue.finish(job["job_id"], worker_id=WORKER,
                                    state="cancelled", error_code="owner_cancel")
        self.assertEqual(stopped["state"], "cancelled")
        self.assertIsNone(stopped["artifact_sha256"])

    def test_crash_restart_marks_queued_and_expired_incomplete(self):
        first = self.submit()
        self.submit(request_key="task-0002", plan_sha256=PLAN2)
        self.queue.claim(worker_id=WORKER)
        self.clock.value += 301
        # A second application instance must not replay secret prompts it
        # never persisted, and must not resume an orphaned GPU job.
        other = self.new_queue()
        self.addCleanup(other.close)
        self.assertEqual(other.get(first["job_id"], principal="owner")["state"],
                         "orphaned")
        self.assertIsNone(other.claim(worker_id=WORKER2))

    def test_other_instance_cannot_clobber_unexpired_gpu_lease(self):
        job = self.submit()
        self.queue.claim(worker_id=WORKER)
        other = self.new_queue()
        self.addCleanup(other.close)
        self.assertEqual(other.get(job["job_id"], principal="owner")["state"],
                         "running")
        self.assertIsNone(other.claim(worker_id=WORKER2))
        # Original worker can still complete while lease remains valid.
        self.queue.finish(job["job_id"], worker_id=WORKER, state="completed",
                          artifact_id="asset_valid", artifact_sha256="e" * 64)

    def test_expired_worker_must_not_publish_late(self):
        job = self.submit()
        self.queue.claim(worker_id=WORKER)
        self.clock.value += 301
        with self.assertRaisesRegex(AgentQueueError, "valid active owner lease"):
            self.queue.finish(job["job_id"], worker_id=WORKER, state="completed",
                              artifact_id="asset_valid", artifact_sha256="e" * 64)
        self.assertIsNone(self.queue.claim(worker_id=WORKER2))
        self.assertEqual(self.queue.get(job["job_id"], principal="owner")["state"],
                         "orphaned")

    def test_orphaned_gpu_blocks_next_job_until_verified_worker_stop(self):
        running = self.submit()
        other_job = self.submit(request_key="task-0002", plan_sha256=PLAN2)
        self.queue.claim(worker_id=WORKER)
        self.clock.value += 301
        self.assertIsNone(self.queue.claim(worker_id=WORKER2))
        self.assertEqual(self.queue.get(running["job_id"], principal="owner")["state"],
                         "orphaned")
        with self.assertRaisesRegex(AgentQueueError, "supervisor unavailable"):
            self.queue.reconcile_orphan(running["job_id"], supervisor_ticket="not-evidence")
        self.queue.supervisor_verify_stopped = lambda job, worker, ticket: False
        with self.assertRaisesRegex(AgentQueueError, "not verified"):
            self.queue.reconcile_orphan(running["job_id"], supervisor_ticket="not-evidence")
        self.assertIsNone(self.queue.claim(worker_id=WORKER2))

        # Test supervisor simulates an independently witnessed native worker
        # exit. This is NOT real Windows process termination acceptance.
        self.queue.supervisor_verify_stopped = (
            lambda job, worker, ticket:
                job == running["job_id"] and worker == WORKER
                and ticket == "actual-supervisor-proof")
        resolved = self.queue.reconcile_orphan(
            running["job_id"], supervisor_ticket="actual-supervisor-proof")
        self.assertEqual(resolved["state"], "interrupted")
        self.assertEqual(resolved["error_code"], "worker_terminated_verified")
        self.assertEqual(self.queue.claim(worker_id=WORKER2)["job_id"],
                         other_job["job_id"])

    def test_fail_closed_on_paths_unknown_engines_or_invalid_ids(self):
        for changes in (
                {"model_id": "../etc/passwd"},
                {"plan_sha256": "invalid"},
                {"kind": "shell.execute"},
                {"principal": "../../owner"},
                {"request_key": "/tmp/secret"},
                {"grant_proof": False},
        ):
            with self.subTest(changes=changes), self.assertRaises(AgentQueueError):
                self.submit(**changes)
        self.assertEqual(self.queue.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 0)

    def test_finished_receipt_never_claims_c2pa_verified(self):
        job = self.submit()
        self.queue.claim(worker_id=WORKER)
        done = self.queue.finish(job["job_id"], worker_id=WORKER, state="completed",
                                 artifact_id="voice_123456", artifact_sha256="e" * 64)
        self.assertEqual(done["state"], "completed")
        self.assertEqual(done["provenance_status"], "unverified_local")
        self.assertNotIn("path", str(done))
        self.assertEqual(self.queue.get(job["job_id"], principal="owner"), done)

    def test_queue_bound_denies_extra_jobs_without_deleting_receipts(self):
        self.queue.max_pending = 1
        self.submit()
        with self.assertRaisesRegex(AgentQueueError, "at capacity"):
            self.submit(request_key="task-0002", plan_sha256=PLAN2)
        self.assertEqual(self.queue.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
