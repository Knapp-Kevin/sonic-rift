"""A project-v1-compatible, unsigned per-clip media creation-event ledger.

The project JSON and its audio bytes remain unchanged. A separate versioned
sidecar maps clip IDs to *creation event IDs*, not merely source byte hashes.
Two clips with identical media bytes can therefore retain distinct creation
histories, while a copied/split clip can reference its original event.

This is an internal local assertion record, NOT cryptographic attestation or
C2PA. It is deliberately not auto-enabled in Studio until project-save and
undo/redo integration has independent qualification. A missing/stale/malformed
sidecar must never be used to declare audio human-made or AI-generated.
"""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

from this_voice_thing.core.audio_project import read_project, to_dict

SCHEMA_VERSION = 1
MAX_EVENTS = 16384
MAX_BINDINGS = 16384
MAX_SIDECAR_BYTES = 2 * 1024 * 1024
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
HEX32 = re.compile(r"[a-f0-9]{32}\Z")
ALLOWED_ORIGINS = frozenset(("ai_generated", "non_ai_synthesis", "unknown"))
ALLOWED_OBSERVERS = frozenset(("studio_generator", "import_unknown"))
FIELDS = frozenset(("event_id", "asset_id", "media_sha256", "origin",
                    "observer", "engine", "model_id", "model_revision"))


def _project_digest(project):
    """Deterministic hash of a validated project snapshot, not a signature."""
    project.validate()
    data = json.dumps(to_dict(project), sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _clip_by_id(project, clip_id):
    return next((clip for track in project.tracks for clip in track.clips
                 if clip.id == clip_id), None)


def _valid_event(event):
    if type(event) is not dict or set(event) != FIELDS:
        raise ValueError("Invalid creation-event fields")
    if (type(event["event_id"]) is not str or HEX32.fullmatch(event["event_id"]) is None
            or type(event["asset_id"]) is not str
            or not 1 <= len(event["asset_id"]) <= 128
            or type(event["media_sha256"]) is not str
            or HEX64.fullmatch(event["media_sha256"]) is None
            or type(event["origin"]) is not str or event["origin"] not in ALLOWED_ORIGINS
            or type(event["observer"]) is not str or event["observer"] not in ALLOWED_OBSERVERS):
        raise ValueError("Invalid creation-event identifier or origin")
    for key in ("engine", "model_id", "model_revision"):
        if type(event[key]) is not str or len(event[key]) > 200:
            raise ValueError("Invalid event model details")
    if event["observer"] == "import_unknown":
        if (event["origin"] != "unknown" or event["engine"]
                or event["model_id"] or event["model_revision"]):
            raise ValueError("Imports cannot assert a generation history")
    else:
        if event["origin"] == "unknown" or not event["engine"]:
            raise ValueError("Generation events require an observed engine")
        if event["origin"] == "non_ai_synthesis" and (
                event["model_id"] or event["model_revision"]):
            raise ValueError("Non-AI synthesis cannot claim generative weights")
    # The content-addressed voice namespace must match its actual media digest.
    if event["asset_id"].startswith("voice_") and (
            event["asset_id"] != "voice_" + event["media_sha256"]):
        raise ValueError("Voice event mismatches the media content address")


class ProjectLineage:
    """Validated, bounded and explicitly revision-bound per-clip event ledger."""

    def __init__(self, project):
        self.project_id = project.id
        self.project_revision = project.revision
        self.project_sha256 = _project_digest(project)
        self.events = {}
        self.bindings = {}

    def _validate(self, project):
        if (project.id != self.project_id or project.revision != self.project_revision
                or _project_digest(project) != self.project_sha256):
            raise ValueError("Stale or different project lineage; origin remains unknown")
        if len(self.events) > MAX_EVENTS or len(self.bindings) > MAX_BINDINGS:
            raise ValueError("Provenance history exceeds limits")
        for key, event in self.events.items():
            _valid_event(event)
            if key != event["event_id"]:
                raise ValueError("Event ID does not match its key")
        for clip_id, event_id in self.bindings.items():
            if type(clip_id) is not str or type(event_id) is not str:
                raise ValueError("Invalid clip-event reference")
            clip = _clip_by_id(project, clip_id)
            if (clip is None or not clip.asset_id or event_id not in self.events
                    or self.events[event_id]["asset_id"] != clip.asset_id):
                raise ValueError("Clip-event reference is stale or mismatched")

    def capture(self, project, clip_id, *, origin, observer,
                media_sha256, engine="", model_id="", model_revision=""):
        """Capture one event for one rendered clip, with an independent event ID.

        A local caller may still lie; only a future signed, trusted app event can
        upgrade assurance. Never call this with untrusted agent-supplied claims.
        """
        self._validate(project)
        clip = _clip_by_id(project, clip_id)
        if clip is None or not clip.asset_id or not clip.frame_count:
            raise ValueError("Creation event needs a rendered clip")
        if clip_id in self.bindings:
            raise ValueError("Clip already has a source event; refusing to rewrite origin")
        if len(self.events) >= MAX_EVENTS or len(self.bindings) >= MAX_BINDINGS:
            raise ValueError("Too many provenance records")
        event_id = uuid.uuid4().hex
        event = {
            "event_id": event_id,
            "asset_id": clip.asset_id,
            "media_sha256": media_sha256,
            "origin": origin,
            "observer": observer,
            "engine": engine,
            "model_id": model_id,
            "model_revision": model_revision,
        }
        _valid_event(event)
        self.events[event_id] = event
        self.bindings[clip_id] = event_id
        return event_id

    def bind_existing(self, project, clip_id, event_id):
        """Explicitly bind a split/duplicate to an existing source event."""
        self._validate(project)
        if event_id not in self.events:
            raise ValueError("Unknown source creation event")
        clip = _clip_by_id(project, clip_id)
        if clip is None or clip.asset_id != self.events[event_id]["asset_id"]:
            raise ValueError("Source event does not match target clip")
        previous = self.bindings.get(clip_id)
        if previous is not None and previous != event_id:
            raise ValueError("Clip already has a different event; refusing silent reattribution")
        if len(self.bindings) >= MAX_BINDINGS and clip_id not in self.bindings:
            raise ValueError("Too many clip-event bindings")
        self.bindings[clip_id] = event_id

    def event_for_clip(self, project, clip_id):
        """Return only a validated app-claimed event or None (never infer human)."""
        self._validate(project)
        event_id = self.bindings.get(clip_id)
        return deepcopy(self.events[event_id]) if event_id is not None else None

    def advance(self, old_project, new_project):
        """Explicit session transition, dropping stale clip/media bindings.

        A split creates a new clip without a binding until its caller explicitly
        copies the event reference. Undo/reopen can safely retain only matching
        clip-ID+asset-ID pairs. No 'best guess' creation event is ever generated.
        """
        self._validate(old_project)
        if new_project.id != self.project_id or new_project.revision < old_project.revision:
            raise ValueError("Lineage cannot switch project or roll back revision")
        new_project.validate()
        snapshot = deepcopy(self)
        snapshot.bindings = {
            clip_id: event_id for clip_id, event_id in snapshot.bindings.items()
            if ((clip := _clip_by_id(new_project, clip_id)) is not None
                and clip.asset_id == snapshot.events[event_id]["asset_id"])
        }
        snapshot.project_revision = new_project.revision
        snapshot.project_sha256 = _project_digest(new_project)
        snapshot._validate(new_project)
        return snapshot

    def to_dict(self, project):
        self._validate(project)
        return {
            "schema_version": SCHEMA_VERSION,
            "evidence_status": "unsigned_local_event_ledger_not_c2pa",
            "project_id": self.project_id,
            "project_revision": self.project_revision,
            "project_sha256": self.project_sha256,
            "events": [deepcopy(self.events[key]) for key in sorted(self.events)],
            "bindings": {key: self.bindings[key] for key in sorted(self.bindings)},
        }


def sidecar_path(project_path):
    """Sibling companion to an existing v1 project. No path from source metadata."""
    path = Path(project_path)
    return path.with_name(path.name + ".lineage.json")


def save_lineage(project_path, ledger):
    """Save only against an already persisted, byte-equivalent project snapshot.

    Project/sidecar cannot be atomically renamed together. Consumers *must*
    verify the project fingerprint and refuse stale files on re-open.
    """
    project_path = Path(project_path)
    if not project_path.is_file():
        raise FileNotFoundError("Project must be saved before its lineage ledger")
    project = read_project(project_path)
    payload = ledger.to_dict(project)
    filename = sidecar_path(project_path)
    if filename.is_symlink():
        raise ValueError("Refusing a linked lineage sidecar")
    if filename.exists():
        if not filename.is_file() or filename.stat().st_size > MAX_SIDECAR_BYTES:
            raise ValueError("Existing lineage sidecar is unsafe")
        try:
            existing = json.loads(filename.read_text(encoding="utf-8"))
        except (ValueError, OSError, UnicodeError) as exc:
            raise ValueError("Refusing overwrite of corrupted lineage sidecar") from exc
        if (type(existing) is not dict
                or set(existing) != {"schema_version", "evidence_status", "project_id",
                                     "project_revision", "project_sha256",
                                     "events", "bindings"}
                or existing["schema_version"] != SCHEMA_VERSION
                or existing["evidence_status"] != "unsigned_local_event_ledger_not_c2pa"
                or existing["project_id"] != project.id
                or type(existing["project_revision"]) is not int
                or existing["project_revision"] > project.revision
                or type(existing["project_sha256"]) is not str
                or HEX64.fullmatch(existing["project_sha256"]) is None
                or type(existing["events"]) is not list
                or len(existing["events"]) > MAX_EVENTS
                or type(existing["bindings"]) is not dict
                or len(existing["bindings"]) > MAX_BINDINGS):
            raise ValueError("Existing lineage sidecar is corrupted or belongs to another/newer project")
        past_events = {}
        try:
            for event in existing["events"]:
                _valid_event(event)
                if event["event_id"] in past_events:
                    raise ValueError("Duplicate event")
                past_events[event["event_id"]] = event
            for clip_id, event_id in existing["bindings"].items():
                if (type(clip_id) is not str or type(event_id) is not str
                        or event_id not in past_events):
                    raise ValueError("Dangling event reference")
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError("Existing lineage sidecar is corrupted") from exc
        # Creation events are append-only even if clips are later deleted or
        # reattached. Never erase earlier evidence by overwriting the sidecar.
        if any(ledger.events.get(key) != event for key, event in past_events.items()):
            raise ValueError("Refusing to discard or rewrite recorded source events")
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
               + "\n").encode("utf-8")
    if len(encoded) > MAX_SIDECAR_BYTES:
        raise ValueError("Lineage record exceeds storage limit")
    temp = None
    try:
        with tempfile.NamedTemporaryFile(
                dir=filename.parent, prefix=".sonic-rift-lineage-",
                suffix=".tmp", delete=False) as output:
            temp = Path(output.name)
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, filename)
        temp = None
    finally:
        if temp is not None and temp.exists():
            temp.unlink()
    return filename


def load_lineage(project_path):
    """Fail closed on stale/forged/corrupted sidecars; no origin inference."""
    project_path = Path(project_path)
    filename = sidecar_path(project_path)
    if not filename.exists():
        return None
    if filename.is_symlink() or not filename.is_file() or filename.stat().st_size > MAX_SIDECAR_BYTES:
        raise ValueError("Unsafe lineage sidecar")
    project = read_project(project_path)
    try:
        data = json.loads(filename.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise ValueError("Corrupted lineage sidecar") from exc
    if (type(data) is not dict or set(data) != {
            "schema_version", "evidence_status", "project_id", "project_revision",
            "project_sha256", "events", "bindings"}
            or data["schema_version"] != SCHEMA_VERSION
            or data["evidence_status"] != "unsigned_local_event_ledger_not_c2pa"
            or type(data["project_revision"]) is not int
            or type(data["project_sha256"]) is not str
            or HEX64.fullmatch(data["project_sha256"]) is None
            or type(data["events"]) is not list or len(data["events"]) > MAX_EVENTS
            or type(data["bindings"]) is not dict or len(data["bindings"]) > MAX_BINDINGS):
        raise ValueError("Invalid lineage sidecar schema")
    ledger = ProjectLineage(project)
    ledger.project_id = data["project_id"]
    ledger.project_revision = data["project_revision"]
    ledger.project_sha256 = data["project_sha256"]
    ledger.events = {}
    for event in data["events"]:
        _valid_event(event)
        if event["event_id"] in ledger.events:
            raise ValueError("Duplicate source event identifier")
        ledger.events[event["event_id"]] = event
    ledger.bindings = data["bindings"]
    ledger._validate(project)
    return ledger
