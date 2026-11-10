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

    def __init__(self, db_path, *, authorize=None, installed_models=None,
                 max_pending=MAX_QUEUE, clock=None):
        if type(max_pending) is not int or not 1 <= max_pending <= MAX_QUEUE:
            raise ValueError("Invalid pending-job quota")
        path = Path(db_path)
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError("Unsafe job database")
        if not path.parent.exists() or not path.parent.is_dir():
            raise ValueError("Job database parent must already exist")
        self.path = path
        self.authorize = authorize
        self.installed_models = installed_models
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
            UNIQUE(principal, request_key_sha256)
        )""")
        self.db.execute("CREATE INDEX IF NOT EXISTS jobs_state ON jobs(state,created_at)")
        # No serialized prompts exist to resume safely after process restart.
        # Mark all previously unfinished work interrupted, never auto-replay.
        with self._transaction():
            now = self.clock()
            self.db.execute("""UPDATE jobs SET state='interrupted',
                lease_owner=NULL, lease_deadline=NULL, updated_at=?,
                error_code='process_restart'
                WHERE state IN ('queued','running','cancel_requested')""", (now,))

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

    def submit(self, *, principal, request_key, kind, model_id, plan_sha256,
               grant_proof=None):
        """Enqueue only app-authorized registered intent; never store a prompt."""
        _valid_plan(kind, model_id, plan_sha256)
        if type(principal) is not str or not PRINCIPAL.fullmatch(principal):
            raise AgentQueueError("Invalid caller identity")
        if type(request_key) is not str or not KEY.fullmatch(request_key):
            raise AgentQueueError("Invalid idempotency key")
        if self.installed_models is None or not callable(self.installed_models):
            raise AgentQueueError("Model registry not bound to the application")
        if model_id not in self.installed_models(kind):
            raise AgentQueueError("Model not installed or not registered for capability")
        if self.authorize is None or not callable(self.authorize):
            raise AgentQueueError("Owner-issued execution permission unavailable")
        # This callback is an *internal authority boundary*, not an agent
        # supplied assertion. For true one-use grants, consumption and insert
        # need a shared transactional authority in Stage C.
        if self.authorize(principal, kind, model_id, plan_sha256, grant_proof) is not True:
            raise AgentQueueError("Owner permission refused")
        key_sha = hashlib.sha256(request_key.encode("utf-8")).hexdigest()
        now = self.clock()
        with self._transaction():
            previous = self.db.execute(
                "SELECT * FROM jobs WHERE principal=? AND request_key_sha256=?",
                (principal, key_sha)).fetchone()
            if previous:
                if (previous["plan_sha256"] != plan_sha256
                        or previous["kind"] != kind or previous["model_id"] != model_id):
                    raise AgentQueueError("Idempotency key reused for another request")
                return self._public(previous)
            count = self.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            if count >= MAX_HISTORY:
                raise AgentQueueError("Job receipt history capacity reached")
            pending = self.db.execute(
                "SELECT COUNT(*) FROM jobs WHERE state='queued'").fetchone()[0]
            if pending >= self.max_pending:
                raise AgentQueueError("Local job queue is at capacity")
            job_id = secrets.token_hex(16)
            self.db.execute("""INSERT INTO jobs (
                job_id, principal, request_key_sha256, kind, model_id,
                plan_sha256, state, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (job_id, principal, key_sha, kind, model_id,
                 plan_sha256, "queued", now, now))
            return self._public(self.db.execute(
                "SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone())

    def claim(self, *, worker_id):
        """Atomically admit at most one heavy generation across all instances."""
        if type(worker_id) is not str or not WORKER.fullmatch(worker_id):
            raise AgentQueueError("Invalid internal worker identity")
        with self._transaction():
            now = self.clock()
            self.db.execute("""UPDATE jobs SET state='interrupted',
                lease_owner=NULL, lease_deadline=NULL, updated_at=?,
                error_code='lease_expired'
                WHERE state IN ('running','cancel_requested') AND lease_deadline<?""",
                            (now, now))
            active = self.db.execute("""SELECT COUNT(*) FROM jobs
                    WHERE state IN ('running','cancel_requested')""").fetchone()[0]
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
                    or job["state"] not in ("running", "cancel_requested")):
                raise AgentQueueError("Job has no active owner lease")
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
