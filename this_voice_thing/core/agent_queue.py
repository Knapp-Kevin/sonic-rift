"""Durable metadata-only local agent job queue for Sonic Rift v1.

Stage B *foundation*, not a model executor or a permission-issuing endpoint.
No prompts, API tokens, audio, absolute paths or signing keys are stored here.
Queue submission is disabled unless an app-owned authority callback approves
the exact proposed operation. The adapter must never supply that callback.

Crash/restart interrupts incomplete jobs rather than replaying unattended
generation. SQLite BEGIN IMMEDIATE serializes leases across all API/UI/MCP
surfaces, but this component does not yet provide a shared GPU worker.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time

KIND = frozenset(("speech.generate", "sound.generate", "music.generate"))
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,95}\Z")
PRINCIPAL = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
KEY = re.compile(r"[A-Za-z0-9_.:-]{8,128}\Z")
WORKER = re.compile(r"[a-f0-9]{32}\Z")
GRANT_TOKEN = re.compile(r"[A-Za-z0-9_-]{32,128}\Z")
MAX_GRANT_TTL = 900
ASSET = re.compile(r"[A-Za-z0-9_-]{6,128}\Z")
MAX_QUEUE = 32
MAX_HISTORY = 10000
LEASE_SECONDS = 300
PUBLIC_FIELDS = ("job_id", "kind", "model_id", "state", "created_at",
                 "updated_at", "artifact_id", "artifact_sha256",
                 "provenance_status", "error_code")


class AgentQueueError(ValueError):
    """An agent request was refused before execution or filesystem work."""


def _valid_plan(kind, model_id, plan_sha256):
    if type(kind) is not str or kind not in KIND:
        raise AgentQueueError("Unsupported generation capability")
    if (type(model_id) is not str or not MODEL.fullmatch(model_id)
            or any(segment in (".", "..") for segment in model_id.split("/"))
            or "//" in model_id):
        raise AgentQueueError("Invalid registered model identifier")
    if type(plan_sha256) is not str or not HEX64.fullmatch(plan_sha256):
        raise AgentQueueError("Invalid canonical plan hash")


class AgentQueue:
    """App-owned durable job metadata; default deny and one active lease.

    The internal `authorize` callable must enforce owner approval, scope,
    expiry and one-time consumption. It must not be wired directly to a
    caller-controlled boolean or read from MCP tool input. This class cannot
    itself prove a grant was minted by the UI and must not be externally
    exposed until the Stage C authorization gate is qualified.
    """

    def __init__(self, db_path, *, owner_approval=None, installed_models=None,
                 supervisor_verify_stopped=None,
                 max_pending=MAX_QUEUE, clock=None):
        if type(max_pending) is not int or not 1 <= max_pending <= MAX_QUEUE:
            raise ValueError("Invalid pending-job quota")
        path = Path(db_path)
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError("Unsafe job database")
        if not path.parent.exists() or not path.parent.is_dir():
            raise ValueError("Job database parent must already exist")
        self.path = path
        self.owner_approval = owner_approval
        self.installed_models = installed_models
        self.supervisor_verify_stopped = supervisor_verify_stopped
        self.max_pending = max_pending
        self.clock = clock or time.time
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None,
                                  timeout=10.0)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA busy_timeout=10000")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("""CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            principal TEXT NOT NULL,
            request_key_sha256 TEXT NOT NULL,
            kind TEXT NOT NULL,
            model_id TEXT NOT NULL,
            plan_sha256 TEXT NOT NULL,
            state TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            lease_owner TEXT,
            lease_deadline REAL,
            artifact_id TEXT,
            artifact_sha256 TEXT,
            provenance_status TEXT NOT NULL DEFAULT 'unverified_local',
            error_code TEXT,
            grant_hash TEXT,
            UNIQUE(principal, request_key_sha256)
        )""")
        self.db.execute("CREATE INDEX IF NOT EXISTS jobs_state ON jobs(state,created_at)")
        # Safe additive migration for pre-grant internal job databases.
        old_columns = {row[1] for row in self.db.execute("PRAGMA table_info(jobs)")}
        if "grant_hash" not in old_columns:
            self.db.execute("ALTER TABLE jobs ADD COLUMN grant_hash TEXT")
        self.db.execute("""CREATE TABLE IF NOT EXISTS execution_grants (
            grant_hash TEXT PRIMARY KEY,
            principal TEXT NOT NULL,
            kind TEXT NOT NULL,
            model_id TEXT NOT NULL,
            plan_sha256 TEXT NOT NULL,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            consumed_job_id TEXT,
            consumed_at REAL,
            revoked INTEGER NOT NULL DEFAULT 0
        )""")
        # Queued jobs lack serialized inputs, so never replay them on restart.
        # Preserve an unexpired active lease: another Sonic Rift process may
        # still own the GPU. Mark only *expired* leases interrupted and wait
        # for live owners to release their slot.
        with self._transaction():
            now = self.clock()
            self.db.execute("""UPDATE jobs SET state='interrupted',
                lease_owner=NULL, lease_deadline=NULL, updated_at=?,
                error_code='process_restart' WHERE state='queued'""", (now,))
            self.db.execute("""UPDATE jobs SET state='orphaned',
                updated_at=?, error_code='expired_on_open'
                WHERE state IN ('running','cancel_requested')
                AND lease_deadline<=?""", (now, now))

    @contextmanager
    def _transaction(self):
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
            else:
                self.db.execute("COMMIT")

    def _owner_confirms(self, operation, principal, kind, model_id, plan_sha256):
        """Only trusted application UI may provide this approval callback.

        No HTTP or MCP route may provide or override this callback. A
        caller-controlled claim of permission is never sufficient.
        """
        callback = self.owner_approval
        return (callable(callback)
                and callback(operation, principal, kind, model_id, plan_sha256) is True)

    def issue_grant(self, *, principal, kind, model_id, plan_sha256,
                    ttl_seconds=120):
        """Mint a single-use, scoped capability after genuine app UI approval.

        Only the SHA-256 of this one-time secret is persisted in SQLite;
        the secret itself is returned once to the trusted owner UI.
        Principal identity must be derived from transport auth, not an
        arbitrary agent-provided field.
        """
        _valid_plan(kind, model_id, plan_sha256)
        if type(principal) is not str or PRINCIPAL.fullmatch(principal) is None:
            raise AgentQueueError("Invalid caller identity")
        if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= MAX_GRANT_TTL:
            raise AgentQueueError("Grant lifetime must be between 1 and 900 seconds")
        if not callable(self.installed_models) or model_id not in self.installed_models(kind):
            raise AgentQueueError("Model not installed or registered for capability")
        if not self._owner_confirms(
                "issue", principal, kind, model_id, plan_sha256):
            raise AgentQueueError("Explicit owner approval unavailable or refused")
        secret = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(secret.encode("ascii")).hexdigest()
        now = self.clock()
        with self._transaction():
            self.db.execute("""INSERT INTO execution_grants (
                grant_hash, principal, kind, model_id, plan_sha256,
                created_at, expires_at)
                VALUES (?,?,?,?,?,?,?)""", (
                token_hash, principal, kind, model_id, plan_sha256,
                now, now + ttl_seconds))
        return secret

    def revoke_grant(self, grant_proof, *, principal):
        """Owner-confirmed revocation stops queued or running granted work."""
        if (type(grant_proof) is not str
                or GRANT_TOKEN.fullmatch(grant_proof) is None
                or type(principal) is not str or PRINCIPAL.fullmatch(principal) is None):
            raise AgentQueueError("Invalid grant or caller identity")
        token_hash = hashlib.sha256(grant_proof.encode("ascii")).hexdigest()
        with self._transaction():
            row = self.db.execute("""SELECT * FROM execution_grants
                WHERE grant_hash=? AND principal=?""",
                (token_hash, principal)).fetchone()
            if row is None:
                raise AgentQueueError("Grant unavailable")
            if not self._owner_confirms(
                    "revoke", row["principal"], row["kind"],
                    row["model_id"], row["plan_sha256"]):
                raise AgentQueueError("Owner did not authorize revocation")
            self.db.execute("UPDATE execution_grants SET revoked=1 WHERE grant_hash=?",
                            (token_hash,))
            now = self.clock()
            self.db.execute("""UPDATE jobs SET state='cancelled',
                updated_at=?, error_code='grant_revoked'
                WHERE grant_hash=? AND state='queued'""", (now, token_hash))
            self.db.execute("""UPDATE jobs SET state='cancel_requested',
                updated_at=?, error_code='grant_revoked'
                WHERE grant_hash=? AND state='running'""", (now, token_hash))
            return True

    def submit(self, *, principal, request_key, kind, model_id, plan_sha256,
               grant_proof=None):
        """Atomically consume one scoped capability and enqueue its job.

        A repeated identical request may retrieve its prior receipt using
        the same grant and idempotency key, but the consumed grant cannot
        authorize a distinct job. No prompt or plaintext grant is stored.
        """
        _valid_plan(kind, model_id, plan_sha256)
        if type(principal) is not str or PRINCIPAL.fullmatch(principal) is None:
            raise AgentQueueError("Invalid caller identity")
        if type(request_key) is not str or KEY.fullmatch(request_key) is None:
            raise AgentQueueError("Invalid idempotency key")
        if type(grant_proof) is not str or GRANT_TOKEN.fullmatch(grant_proof) is None:
            raise AgentQueueError("Owner-issued execution grant required")
        if not callable(self.installed_models) or model_id not in self.installed_models(kind):
            raise AgentQueueError("Model not installed or registered for capability")
        token_hash = hashlib.sha256(grant_proof.encode("ascii")).hexdigest()
        key_hash = hashlib.sha256(request_key.encode("utf-8")).hexdigest()
        with self._transaction():
            now = self.clock()
            grant = self.db.execute(
                "SELECT * FROM execution_grants WHERE grant_hash=?",
                (token_hash,)).fetchone()
            if (grant is None or grant["revoked"] != 0
                    or grant["expires_at"] <= now
                    or grant["principal"] != principal or grant["kind"] != kind
                    or grant["model_id"] != model_id
                    or grant["plan_sha256"] != plan_sha256):
                raise AgentQueueError("Grant expired, revoked, unknown or out of scope")
            previous = self.db.execute(
                "SELECT * FROM jobs WHERE principal=? AND request_key_sha256=?",
                (principal, key_hash)).fetchone()
            if previous:
                if (previous["plan_sha256"] != plan_sha256
                        or previous["kind"] != kind
                        or previous["model_id"] != model_id
                        or previous["grant_hash"] != token_hash):
                    raise AgentQueueError("Idempotency key reused for another request")
                return self._public(previous)
            if grant["consumed_job_id"] is not None:
                raise AgentQueueError("Execution grant already consumed")
            total = self.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            if total >= MAX_HISTORY:
                raise AgentQueueError("Job receipt history capacity reached")
            pending = self.db.execute(
                "SELECT COUNT(*) FROM jobs WHERE state='queued'").fetchone()[0]
            if pending >= self.max_pending:
                raise AgentQueueError("Local job queue is at capacity")
            job_id = secrets.token_hex(16)
            self.db.execute("""INSERT INTO jobs (
                job_id, principal, request_key_sha256, kind, model_id,
                plan_sha256, state, created_at, updated_at, grant_hash)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (job_id, principal, key_hash, kind, model_id,
                 plan_sha256, "queued", now, now, token_hash))
            changed = self.db.execute("""UPDATE execution_grants SET
                consumed_job_id=?, consumed_at=?
                WHERE grant_hash=? AND consumed_job_id IS NULL AND revoked=0
                AND expires_at>?""", (job_id, now, token_hash, now)).rowcount
            if changed != 1:
                raise AgentQueueError("Grant consumption race; job rolled back")
            return self._public(self.db.execute(
                "SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone())

    def claim(self, *, worker_id):
        """Atomically admit at most one heavy generation across all instances."""
        if type(worker_id) is not str or not WORKER.fullmatch(worker_id):
            raise AgentQueueError("Invalid internal worker identity")
        with self._transaction():
            now = self.clock()
            # An expired lease is NOT proof its native GPU worker died.
            # Quarantine the entire worker pool until the app supervisor
            # independently verifies termination. Never auto-admit another.
            self.db.execute("""UPDATE jobs SET state='orphaned',
                updated_at=?, error_code='lease_expired_unreconciled'
                WHERE state IN ('running','cancel_requested') AND lease_deadline<=?""",
                            (now, now))
            active = self.db.execute("""SELECT COUNT(*) FROM jobs
                    WHERE state IN ('running','cancel_requested','orphaned')""").fetchone()[0]
            if active:
                return None
            job = self.db.execute("""SELECT job_id FROM jobs WHERE state='queued'
                ORDER BY created_at,job_id LIMIT 1""").fetchone()
            if job is None:
                return None
            self.db.execute("""UPDATE jobs SET state='running',
                lease_owner=?, lease_deadline=?, updated_at=?
                WHERE job_id=?""", (worker_id, now + LEASE_SECONDS, now, job["job_id"]))
            return self._public(self.db.execute(
                "SELECT * FROM jobs WHERE job_id=?", (job["job_id"],)).fetchone())

    def reconcile_orphan(self, job_id, *, supervisor_ticket):
        """Clear quarantine only after an app-owned worker supervisor proof.

        A mere agent assertion, callback-free queue, job timeout or owner
        boolean must not resume GPU work. The injected supervisor must check
        and terminate the actual process / GPU lease using a trusted app
        identity; Stage C/Windows integration must qualify that behavior.
        """
        if type(job_id) is not str or not WORKER.fullmatch(job_id):
            raise AgentQueueError("Invalid orphan ID")
        if not callable(self.supervisor_verify_stopped):
            raise AgentQueueError("Trusted worker supervisor unavailable")
        with self._transaction():
            row = self.db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None or row["state"] != "orphaned":
                raise AgentQueueError("Job is not quarantined")
            if self.supervisor_verify_stopped(
                    job_id, row["lease_owner"], supervisor_ticket) is not True:
                raise AgentQueueError("Native worker termination not verified")
            now = self.clock()
            self.db.execute("""UPDATE jobs SET state='interrupted',
                lease_owner=NULL, lease_deadline=NULL,
                updated_at=?, error_code='worker_terminated_verified'
                WHERE job_id=? AND state='orphaned'""", (now, job_id))
            return self._public(self.db.execute(
                "SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone())

    def heartbeat(self, job_id, worker_id):
        """Return False when cancellation has been requested; worker must stop."""
        if type(job_id) is not str or not WORKER.fullmatch(job_id):
            raise AgentQueueError("Invalid job ID")
        with self._transaction():
            job = self.db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if not job or job["lease_owner"] != worker_id:
                raise AgentQueueError("Lease does not belong to worker")
            if job["state"] == "cancel_requested":
                return False
            if job["state"] != "running" or job["lease_deadline"] < self.clock():
                raise AgentQueueError("Lease expired or job not running")
            now = self.clock()
            self.db.execute("UPDATE jobs SET lease_deadline=?,updated_at=? WHERE job_id=?",
                            (now + LEASE_SECONDS, now, job_id))
            return True

    def cancel(self, job_id, *, principal):
        """Request cancellation. Running worker must cooperatively acknowledge."""
        if type(job_id) is not str or not WORKER.fullmatch(job_id):
            raise AgentQueueError("Invalid job ID")
        with self._transaction():
            job = self.db.execute(
                "SELECT * FROM jobs WHERE job_id=? AND principal=?",
                (job_id, principal)).fetchone()
            if job is None:
                raise AgentQueueError("Job unavailable")
            if job["state"] == "queued":
                status = "cancelled"
            elif job["state"] == "running":
                status = "cancel_requested"
            else:
                return self._public(job)
            now = self.clock()
            self.db.execute("UPDATE jobs SET state=?, updated_at=? WHERE job_id=?",
                            (status, now, job_id))
            return self._public(self.db.execute(
                "SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone())

    def finish(self, job_id, *, worker_id, state, artifact_id=None,
               artifact_sha256=None, error_code=None):
        """Record local output only. Never self-certify C2PA as verified."""
        if state not in ("completed", "failed", "cancelled"):
            raise AgentQueueError("Invalid terminal state")
        if state == "completed":
            if (type(artifact_id) is not str or not ASSET.fullmatch(artifact_id)
                    or type(artifact_sha256) is not str
                    or not HEX64.fullmatch(artifact_sha256)):
                raise AgentQueueError("Missing safe artifact receipt")
        elif artifact_id is not None or artifact_sha256 is not None:
            raise AgentQueueError("Failed/cancelled jobs have no published artifact")
        if error_code is not None and (
                type(error_code) is not str or not PRINCIPAL.fullmatch(error_code)):
            raise AgentQueueError("Invalid bounded error code")
        with self._transaction():
            job = self.db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if (not job or job["lease_owner"] != worker_id
                    or job["state"] not in ("running", "cancel_requested")
                    or job["lease_deadline"] is None
                    or job["lease_deadline"] < self.clock()):
                raise AgentQueueError("Job has no valid active owner lease")
            if job["state"] == "cancel_requested" and state == "completed":
                raise AgentQueueError("Cancelled job cannot publish an artifact")
            now = self.clock()
            self.db.execute("""UPDATE jobs SET state=?, artifact_id=?,
                artifact_sha256=?, error_code=?, lease_owner=NULL,
                lease_deadline=NULL, updated_at=? WHERE job_id=?""",
                            (state, artifact_id, artifact_sha256, error_code, now, job_id))
            return self._public(self.db.execute(
                "SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone())

    def get(self, job_id, *, principal):
        if type(job_id) is not str or not WORKER.fullmatch(job_id):
            raise AgentQueueError("Invalid job ID")
        with self.lock:
            row = self.db.execute(
                "SELECT * FROM jobs WHERE job_id=? AND principal=?",
                (job_id, principal)).fetchone()
        if not row:
            raise AgentQueueError("Job unavailable")
        return self._public(row)

    @staticmethod
    def _public(row):
        # Never include principal, idempotency secret hash, prompt or internal
        # lease/worker identity in agent-facing receipts.
        return {field: row[field] for field in PUBLIC_FIELDS}

    def close(self):
        with self.lock:
            self.db.close()
