"""Stage B agent queue: isolated SQLite and simulated workers; no model/Qt load."""
from pathlib import Path
import sqlite3
import tempfile
import unittest

from this_voice_thing.core.agent_queue import AgentQueue, AgentQueueError
from this_voice_thing.core.agent_jobs import plan_request

MODEL = "ACE-Step/Ace-Step1.5"
REQUEST = {
    "kind": "music.generate", "model_id": MODEL,
    "prompt": "private music generation for a soundtrack",
    "duration_seconds": 12, "seed": 123, "instrumental": True,
}
REQUEST2 = dict(REQUEST, prompt="a second private audio prompt")
PLAN = plan_request(REQUEST)["plan_id"]
PLAN2 = plan_request(REQUEST2)["plan_id"]
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
        self.approve = lambda operation, principal, kind, model, plan, request: True
        self.models = lambda kind: [MODEL] if kind == "music.generate" else []
        self.payload = lambda job_id: True  # synthetic owned inputs in these tests
        self.grants = {}
        self.queue = self.new_queue()
        self.addCleanup(self.queue.close)

    def new_queue(self, **changes):
        options = dict(owner_approval=self.approve, installed_models=self.models,
                       queued_payload_available=self.payload, clock=self.clock)
        options.update(changes)
        return AgentQueue(self.file, **options)

    def mint(self, **kwargs):
        kwargs.setdefault("review_request",
                          REQUEST2 if kwargs.get("plan_sha256") == PLAN2 else REQUEST)
        return self.queue.issue_grant(**kwargs)

    def submit(self, **changes):
        options = dict(
            principal="owner", request_key=KEY, kind="music.generate",
            model_id=MODEL, plan_sha256=PLAN)
        options.update(changes)
        if "grant_proof" not in changes:
            key = options["request_key"]
            if key not in self.grants:
                self.grants[key] = self.mint(
                    principal=options["principal"], kind=options["kind"],
                    model_id=options["model_id"], plan_sha256=options["plan_sha256"])
            options["grant_proof"] = self.grants[key]
        return self.queue.submit(**options)

    def test_default_deny_requires_real_registry_and_authority(self):
        with tempfile.TemporaryDirectory() as folder:
            q = AgentQueue(Path(folder) / "blocked.sqlite", installed_models=self.models)
            self.addCleanup(q.close)
            with self.assertRaisesRegex(AgentQueueError, "approval unavailable"):
                q.issue_grant(principal="owner", kind="music.generate",
                              model_id=MODEL, plan_sha256=PLAN,
                              review_request=REQUEST)
            with self.assertRaisesRegex(AgentQueueError, "grant required"):
                q.submit(principal="owner", request_key=KEY,
                         kind="music.generate", model_id=MODEL, plan_sha256=PLAN)
        with self.assertRaisesRegex(AgentQueueError, "grant required"):
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
        self.assertNotIn("grant_hash", first)
        self.assertNotIn("lease_owner", first)
        mismatched_grant = self.mint(
            principal="owner", kind="music.generate",
            model_id=MODEL, plan_sha256=PLAN2)
        with self.assertRaisesRegex(AgentQueueError, "another request"):
            self.submit(plan_sha256=PLAN2, grant_proof=mismatched_grant)
        rows = self.queue.db.execute("SELECT * FROM jobs").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertNotIn(KEY, str(tuple(rows[0])))
        self.assertNotIn(self.grants[KEY], str(tuple(rows[0])))

    def test_owner_refusal_and_malformed_registry_never_issue_grants(self):
        self.queue.owner_approval = lambda *args: False
        with self.assertRaisesRegex(AgentQueueError, "approval unavailable"):
            self.mint(
                principal="owner", kind="music.generate",
                model_id=MODEL, plan_sha256=PLAN)
        self.queue.owner_approval = self.approve
        for bad_registry in (
                lambda kind: MODEL,  # string membership is not a registry
                lambda kind: {MODEL: "installed"},
                lambda kind: [None, MODEL],
                lambda kind: [],
        ):
            with self.subTest(registry=bad_registry):
                self.queue.installed_models = bad_registry
                with self.assertRaisesRegex(AgentQueueError, "not installed or registered"):
                    self.mint(
                        principal="owner", kind="music.generate",
                        model_id=MODEL, plan_sha256=PLAN)
        self.assertEqual(self.queue.db.execute(
            "SELECT COUNT(*) FROM execution_grants").fetchone()[0], 0)

    def test_missing_owner_payload_recovery_authority_is_denied(self):
        job = self.submit()
        observer = self.new_queue(queued_payload_available=None)
        self.addCleanup(observer.close)
        with self.assertRaisesRegex(AgentQueueError, "payload store unavailable"):
            observer.reconcile_missing_payloads()
        self.assertEqual(self.queue.get(job["job_id"], principal="owner")["state"],
                         "queued")

    def test_owner_reviews_the_exact_request_and_plaintext_is_not_persisted(self):
        observed = []

        def approve(operation, principal, kind, model, plan, review_request):
            if operation == "issue":
                observed.append(review_request)
            return True

        self.queue.owner_approval = approve
        with self.assertRaisesRegex(AgentQueueError, "does not match"):
            self.mint(principal="owner", kind="music.generate",
                      model_id=MODEL, plan_sha256=PLAN, review_request=REQUEST2)
        with self.assertRaisesRegex(AgentQueueError, "Invalid reviewable"):
            self.mint(principal="owner", kind="music.generate",
                      model_id=MODEL, plan_sha256=PLAN,
                      review_request=dict(REQUEST, shell_command="rm -rf /"))
        self.assertEqual(observed, [])
        token = self.mint(principal="owner", kind="music.generate",
                          model_id=MODEL, plan_sha256=PLAN)
        self.assertEqual(observed[0]["prompt"], REQUEST["prompt"])
        self.assertEqual(observed[0]["model_id"], MODEL)
        observed[0]["prompt"] = "tampered during display"
        self.assertEqual(REQUEST["prompt"], "private music generation for a soundtrack")
        self.assertNotIn(REQUEST["prompt"], str(
            tuple(self.queue.db.execute(
                "SELECT * FROM execution_grants").fetchone())))
        self.assertEqual(self.submit(grant_proof=token)["state"], "queued")

    def test_grant_expires_without_starting_work(self):
        token = self.mint(
            principal="owner", kind="music.generate",
            model_id=MODEL, plan_sha256=PLAN, ttl_seconds=1)
        self.clock.value += 1
        with self.assertRaisesRegex(AgentQueueError, "expired"):
            self.submit(grant_proof=token)
        self.assertEqual(self.queue.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 0)

    def test_grant_binding_cannot_cross_principal_kind_model_or_plan(self):
        token = self.mint(
            principal="owner", kind="music.generate",
            model_id=MODEL, plan_sha256=PLAN)
        for changed in (
                {"principal": "other"},
                {"kind": "sound.generate"},
                {"plan_sha256": PLAN2}):
            with self.subTest(changed=changed), self.assertRaises(AgentQueueError):
                self.submit(grant_proof=token, **changed)
        self.assertEqual(self.queue.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 0)
        self.assertEqual(self.submit(grant_proof=token)["state"], "queued")

    def test_one_grant_cannot_submit_two_distinct_jobs_or_leak_plaintext(self):
        token = self.mint(
            principal="owner", kind="music.generate",
            model_id=MODEL, plan_sha256=PLAN)
        first = self.submit(grant_proof=token)
        self.assertEqual(first["job_id"], self.submit(grant_proof=token)["job_id"])
        with self.assertRaisesRegex(AgentQueueError, "already consumed"):
            self.submit(request_key="task-0002", grant_proof=token)
        rows = self.queue.db.execute("SELECT * FROM execution_grants").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertNotIn(token, str(tuple(rows[0])))
        self.assertEqual(rows[0]["consumed_job_id"], first["job_id"])

    def test_parallel_queue_instances_cannot_double_consume_grant(self):
        other = self.new_queue()
        self.addCleanup(other.close)
        token = self.mint(
            principal="owner", kind="music.generate",
            model_id=MODEL, plan_sha256=PLAN)
        first = other.submit(principal="owner", request_key=KEY,
                             kind="music.generate", model_id=MODEL,
                             plan_sha256=PLAN, grant_proof=token)
        with self.assertRaisesRegex(AgentQueueError, "already consumed"):
            self.queue.submit(principal="owner", request_key="task-0002",
                              kind="music.generate", model_id=MODEL,
                              plan_sha256=PLAN, grant_proof=token)
        self.assertEqual(other.get(first["job_id"], principal="owner")["state"], "queued")

    def test_revocation_cancels_queued_and_requests_running_worker_stop(self):
        token = self.mint(
            principal="owner", kind="music.generate",
            model_id=MODEL, plan_sha256=PLAN)
        first = self.submit(grant_proof=token)
        self.assertTrue(self.queue.revoke_grant(token, principal="owner"))
        self.assertEqual(self.queue.get(first["job_id"], principal="owner")["state"],
                         "cancelled")
        self.assertIsNone(self.queue.claim(worker_id=WORKER))
        with self.assertRaisesRegex(AgentQueueError, "revoked"):
            self.queue.submit(principal="owner", request_key=KEY,
                              kind="music.generate", model_id=MODEL,
                              plan_sha256=PLAN, grant_proof=token)

        other_token = self.mint(
            principal="owner", kind="music.generate",
            model_id=MODEL, plan_sha256=PLAN2)
        second = self.submit(request_key="task-0002", plan_sha256=PLAN2,
                             grant_proof=other_token)
        self.queue.claim(worker_id=WORKER)
        with self.assertRaisesRegex(AgentQueueError, "unavailable"):
            self.queue.revoke_grant(other_token, principal="stranger")
        self.assertTrue(self.queue.revoke_grant(other_token, principal="owner"))
        self.assertEqual(self.queue.get(second["job_id"], principal="owner")["state"],
                         "cancel_requested")
        self.assertFalse(self.queue.heartbeat(second["job_id"], WORKER))
        with self.assertRaisesRegex(AgentQueueError, "cannot publish"):
            self.queue.finish(second["job_id"], worker_id=WORKER,
                              state="completed", artifact_id="asset_valid",
                              artifact_sha256="e" * 64)

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
        other = self.new_queue(queued_payload_available=lambda job_id: False)
        self.addCleanup(other.close)
        self.assertEqual(other.reconcile_missing_payloads(), 1)
        self.assertIsNone(other.claim(worker_id=WORKER2))
        self.assertEqual(other.get(first["job_id"], principal="owner")["state"],
                         "orphaned")

    def test_new_observer_connection_never_interferes_with_running_app_jobs(self):
        first = self.submit()
        readonly = self.new_queue(queued_payload_available=None)
        self.addCleanup(readonly.close)
        self.assertEqual(readonly.get(first["job_id"], principal="owner")["state"],
                         "queued")
        self.assertIsNone(readonly.claim(worker_id=WORKER2))
        self.assertEqual(self.queue.claim(worker_id=WORKER)["job_id"],
                         first["job_id"])

    def test_worker_claims_only_owned_payload_and_reconciles_missing_inputs(self):
        first = self.submit()
        second = self.submit(request_key="task-0002", plan_sha256=PLAN2)
        worker = self.new_queue(
            queued_payload_available=lambda job: job == second["job_id"])
        self.addCleanup(worker.close)
        self.assertEqual(worker.claim(worker_id=WORKER)["job_id"],
                         second["job_id"])
        self.assertEqual(self.queue.get(first["job_id"], principal="owner")["state"],
                         "queued")
        self.assertEqual(worker.reconcile_missing_payloads(), 1)
        self.assertEqual(self.queue.get(first["job_id"], principal="owner")["state"],
                         "interrupted")

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
