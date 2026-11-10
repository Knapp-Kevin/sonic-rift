"""Explicit, recoverable two-file save protocol for v1 project plus lineage.

Prototype only. Neither a filesystem-wide atomic transaction nor cryptographic
authenticity: a prepared journal makes crash windows detectable, and recovery
rolls forward *only* when every old/new file matches recorded SHA-256 values.

Never auto-recover or write from a Studio open/export path. This module is not
connected to the GUI until Windows and independent crash-injection acceptance.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

from this_voice_thing.core.audio_project import from_dict, read_project, to_dict
from this_voice_thing.core.project_lineage import (
    HEX64, MAX_EVENTS, MAX_BINDINGS, MAX_SIDECAR_BYTES,
    ProjectLineage, _valid_event, load_lineage, sidecar_path,
)

PROTOCOL_VERSION = 1
MAX_PROJECT_BYTES = 32 * 1024 * 1024
MAX_JOURNAL_BYTES = 4096
TXID = re.compile(r"[a-f0-9]{32}\Z")
JOURNAL_FIELDS = frozenset((
    "version", "transaction_id", "project_id", "old_project_hash",
    "old_lineage_hash", "new_project_hash", "new_lineage_hash",
))


def journal_path(project_path):
    path = Path(project_path)
    return path.with_name(path.name + ".lineage-transaction.json")


def _digest(value):
    return hashlib.sha256(value).hexdigest()


def _read_regular(path, limit):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing, linked, or irregular transaction file")
    if path.stat().st_size > limit:
        raise ValueError("Transaction file exceeds size limit")
    return path.read_bytes()


def _hash_file(path, limit):
    return _digest(_read_regular(path, limit)) if path.exists() or path.is_symlink() else None


def _names(project_path, transaction_id):
    path = Path(project_path)
    if not TXID.fullmatch(transaction_id):
        raise ValueError("Invalid transaction ID")
    return (
        path.with_name("." + path.name + ".project-" + transaction_id + ".stage"),
        path.with_name("." + path.name + ".lineage-" + transaction_id + ".stage"),
    )


def _write_exclusive(path, content):
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _project_bytes(project):
    project.validate()
    data = (json.dumps(to_dict(project), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(data) > MAX_PROJECT_BYTES:
        raise ValueError("Project exceeds transaction limit")
    return data


def _lineage_bytes(ledger, project):
    data = (json.dumps(ledger.to_dict(project), ensure_ascii=False,
                       sort_keys=True, indent=2) + "\n").encode("utf-8")
    if len(data) > MAX_SIDECAR_BYTES:
        raise ValueError("Lineage exceeds transaction limit")
    return data


def _read_journal(path):
    source = journal_path(path)
    if not source.exists() and not source.is_symlink():
        return None
    try:
        info = json.loads(_read_regular(source, MAX_JOURNAL_BYTES))
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise ValueError("Transaction journal invalid; refusing recovery") from exc
    if (type(info) is not dict or set(info) != JOURNAL_FIELDS
            or type(info["version"]) is not int
            or info["version"] != PROTOCOL_VERSION
            or type(info["transaction_id"]) is not str
            or TXID.fullmatch(info["transaction_id"]) is None
            or type(info["project_id"]) is not str
            or not info["project_id"]):
        raise ValueError("Transaction journal has invalid fields")
    for name in ("old_project_hash", "old_lineage_hash",
                 "new_project_hash", "new_lineage_hash"):
        value = info[name]
        if value is not None and (
                type(value) is not str or HEX64.fullmatch(value) is None):
            raise ValueError("Transaction journal hash invalid")
    if info["old_project_hash"] is None or info["new_project_hash"] is None:
        raise ValueError("Project hashes required in transaction")
    if info["new_lineage_hash"] is None:
        raise ValueError("Lineage hash required in transaction")
    return info


def _lineage_from_bytes(encoded, project):
    try:
        payload = json.loads(encoded)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Staged lineage JSON invalid") from exc
    if (type(payload) is not dict or set(payload) != {
            "schema_version", "evidence_status", "project_id", "project_revision",
            "project_sha256", "events", "bindings"}
            or payload["schema_version"] != 1
            or payload["evidence_status"] != "unsigned_local_event_ledger_not_c2pa"
            or type(payload["events"]) is not list
            or len(payload["events"]) > MAX_EVENTS
            or type(payload["bindings"]) is not dict
            or len(payload["bindings"]) > MAX_BINDINGS):
        raise ValueError("Staged lineage schema invalid")
    ledger = ProjectLineage(project)
    ledger.project_id = payload["project_id"]
    ledger.project_revision = payload["project_revision"]
    ledger.project_sha256 = payload["project_sha256"]
    ledger.events = {}
    for event in payload["events"]:
        _valid_event(event)
        if event["event_id"] in ledger.events:
            raise ValueError("Duplicate staged provenance event")
        ledger.events[event["event_id"]] = event
    ledger.bindings = payload["bindings"]
    ledger._validate(project)
    return ledger


def _check_old_events(old, new):
    if old is not None and any(new.events.get(k) != ev for k, ev in old.events.items()):
        raise ValueError("Refusing to delete or rewrite prior creation events")


def save_pair(project_path, old_project, new_project, new_ledger, *, fail_after=None):
    """Prepare both blobs then install with a recoverable journal.

    Crash simulations may be injected after 'journal', 'project' or 'lineage'.
    An interruption leaves a journal; it never silently claims a valid origin.
    Only the explicit recover_pair() may finish the installation.
    """
    path = Path(project_path)
    sidecar = sidecar_path(path)
    pending = journal_path(path)
    if path.is_symlink() or sidecar.is_symlink():
        raise ValueError("Refusing linked project or lineage transaction target")
    if fail_after not in (None, "journal", "project", "lineage"):
        raise ValueError("Unknown transaction test interruption point")
    if pending.exists() or pending.is_symlink():
        raise ValueError("Pending lineage transaction requires explicit recovery")
    if (new_project.id != old_project.id
            or new_project.revision < old_project.revision):
        raise ValueError("Cannot switch projects or roll back project revision")
    if read_project(path) != old_project:
        raise ValueError("Existing project changed before transaction")
    if not isinstance(new_ledger, ProjectLineage):
        raise TypeError("Expected a project lineage ledger")
    before = load_lineage(path)
    _check_old_events(before, new_ledger)
    new_project_bytes = _project_bytes(new_project)
    new_lineage_bytes = _lineage_bytes(new_ledger, new_project)
    old_project_hash = _hash_file(path, MAX_PROJECT_BYTES)
    old_lineage_hash = _hash_file(sidecar, MAX_SIDECAR_BYTES)
    txid = uuid.uuid4().hex
    project_stage, lineage_stage = _names(path, txid)
    prepared = {
        "version": PROTOCOL_VERSION,
        "transaction_id": txid,
        "project_id": new_project.id,
        "old_project_hash": old_project_hash,
        "old_lineage_hash": old_lineage_hash,
        "new_project_hash": _digest(new_project_bytes),
        "new_lineage_hash": _digest(new_lineage_bytes),
    }
    try:
        _write_exclusive(project_stage, new_project_bytes)
        _write_exclusive(lineage_stage, new_lineage_bytes)
        _write_exclusive(pending, json.dumps(prepared, sort_keys=True).encode("utf-8"))
    except BaseException:
        if not pending.exists():
            for stage in (project_stage, lineage_stage):
                if stage.exists():
                    stage.unlink()
        raise
    if fail_after == "journal":
        raise RuntimeError("Injected crash after journal preparation")
    return recover_pair(path, fail_after=fail_after)


def recover_pair(project_path, *, fail_after=None):
    """Explicit, hash-guarded roll-forward. Never infer success from a marker.

    If any source differs from its recorded old/new digest, refuse all writes
    and leave the journal for investigation. Never auto-overwrite user edits.
    """
    path = Path(project_path)
    sidecar = sidecar_path(path)
    marker = journal_path(path)
    info = _read_journal(path)
    if info is None:
        return "no_pending_transaction"
    project_stage, lineage_stage = _names(path, info["transaction_id"])

    # Check all old/new live and stage content before mutating either file.
    current_project = _hash_file(path, MAX_PROJECT_BYTES)
    current_lineage = _hash_file(sidecar, MAX_SIDECAR_BYTES)
    if (current_project not in (info["old_project_hash"], info["new_project_hash"])
            or current_lineage not in (info["old_lineage_hash"], info["new_lineage_hash"])):
        raise ValueError("Transaction conflict; existing files differ from journal")
    if path.is_symlink() or sidecar.is_symlink():
        raise ValueError("Transaction target is an unsafe symbolic link")
    if (current_project != info["new_project_hash"]
            and _hash_file(project_stage, MAX_PROJECT_BYTES) != info["new_project_hash"]):
        raise ValueError("Missing or altered staged project")
    if (current_lineage != info["new_lineage_hash"]
            and _hash_file(lineage_stage, MAX_SIDECAR_BYTES) != info["new_lineage_hash"]):
        raise ValueError("Missing or altered staged lineage")

    new_project_bytes = (
        _read_regular(path, MAX_PROJECT_BYTES)
        if current_project == info["new_project_hash"]
        else _read_regular(project_stage, MAX_PROJECT_BYTES))
    new_lineage_bytes = (
        _read_regular(sidecar, MAX_SIDECAR_BYTES)
        if current_lineage == info["new_lineage_hash"]
        else _read_regular(lineage_stage, MAX_SIDECAR_BYTES))
    try:
        candidate = from_dict(json.loads(new_project_bytes))
        _lineage_from_bytes(new_lineage_bytes, candidate)
    except (TypeError, UnicodeError, ValueError, KeyError) as exc:
        raise ValueError("Invalid staged project-lineage pair") from exc
    if candidate.id != info["project_id"]:
        raise ValueError("Staged project identity differs from journal")

    if current_project != info["new_project_hash"]:
        os.replace(project_stage, path)
    if fail_after == "project":
        raise RuntimeError("Injected crash after project installation")
    if _hash_file(path, MAX_PROJECT_BYTES) != info["new_project_hash"]:
        raise ValueError("Project installation failed integrity verification")

    if current_lineage != info["new_lineage_hash"]:
        os.replace(lineage_stage, sidecar)
    if fail_after == "lineage":
        raise RuntimeError("Injected crash after lineage installation")
    if _hash_file(sidecar, MAX_SIDECAR_BYTES) != info["new_lineage_hash"]:
        raise ValueError("Lineage installation failed integrity verification")

    # Journal removal is the committed marker, only after both file hashes
    # agree. A subsequent call is idempotent, including after final rename.
    marker.unlink()
    for stage in (project_stage, lineage_stage):
        if stage.exists():
            stage.unlink()
    return "committed"
