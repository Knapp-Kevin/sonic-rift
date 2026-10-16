"""Versioned, Qt-free Sonic Rift timeline project documents.

Timing uses integer sample frames, never binary floats. A project stores references
and editing intent, not embedded audio or executable paths. No legacy user files
are read or modified by importing this module.
"""

from dataclasses import dataclass, field, asdict
import json
import math
import os
import re
from pathlib import Path
import tempfile
import uuid

SCHEMA_VERSION = 1
TRACK_KINDS = frozenset({"voice", "sound", "effect"})
MAX_TRACKS = 128
MAX_CLIPS_PER_TRACK = 4096


def new_id():
    return uuid.uuid4().hex


def _text(value, label, max_len=2000):
    if not isinstance(value, str) or len(value) > max_len:
        raise ValueError(f"Invalid {label}")
    return value


def _integer(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"Invalid {label}")
    return value


def _real(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"Invalid {label}")
    return float(value)


@dataclass
class Clip:
    id: str
    kind: str
    start_frame: int
    frame_count: int
    asset_id: str = ""
    text: str = ""
    voice_id: str = ""
    gain_db: float = 0.0
    fade_in_frames: int = 0
    fade_out_frames: int = 0
    loop: bool = False
    # Frames of the source skipped at the clip's start (a non-destructive trim). Written to
    # project files only when non-zero, so untrimmed projects still open in earlier builds.
    source_offset_frames: int = 0

    def validate(self):
        _text(self.id, "clip ID", 128)
        if not self.id or self.kind not in TRACK_KINDS:
            raise ValueError("Invalid clip kind or ID")
        _integer(self.start_frame, "clip start")
        _integer(self.frame_count, "clip length")
        _integer(self.fade_in_frames, "fade in")
        _integer(self.fade_out_frames, "fade out")
        _integer(self.source_offset_frames, "source offset")
        if self.source_offset_frames and not self.asset_id:
            raise ValueError("Only clips with audio can be trimmed")
        if self.fade_in_frames > self.frame_count or self.fade_out_frames > self.frame_count:
            raise ValueError("Fade exceeds clip duration")
        if not -60 <= _real(self.gain_db, "clip gain") <= 24:
            raise ValueError("Clip gain outside supported range")
        for key in ("asset_id", "voice_id"):
            _text(getattr(self, key), key, 128)
        if self.asset_id and not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", self.asset_id):
            raise ValueError("Invalid asset ID")
        _text(self.text, "clip text", 100000)
        if type(self.loop) is not bool or (self.loop and self.kind != "sound"):
            raise ValueError("Only sound clips may loop")
        if self.frame_count == 0 and (self.asset_id or not (self.kind == "voice" and self.text.strip())):
            raise ValueError("Only unrendered voice text may have zero length")
        if self.frame_count > 0 and not self.asset_id:
            raise ValueError("Rendered clip requires a library asset reference")


@dataclass
class Track:
    id: str
    kind: str
    name: str
    clips: list[Clip] = field(default_factory=list)
    muted: bool = False
    gain_db: float = 0.0

    def validate(self):
        _text(self.id, "track ID", 128)
        _text(self.name, "track name", 256)
        if not self.id or self.kind not in TRACK_KINDS or type(self.muted) is not bool:
            raise ValueError("Invalid track")
        if not -60 <= _real(self.gain_db, "track gain") <= 24:
            raise ValueError("Track gain outside supported range")
        if len(self.clips) > MAX_CLIPS_PER_TRACK:
            raise ValueError("Too many clips")
        seen = set()
        for clip in self.clips:
            clip.validate()
            if clip.kind != self.kind or clip.id in seen:
                raise ValueError("Clip kind mismatch or duplicate ID")
            seen.add(clip.id)


@dataclass
class AudioProject:
    id: str
    title: str
    sample_rate: int = 48000
    tracks: list[Track] = field(default_factory=list)
    schema_version: int = SCHEMA_VERSION
    revision: int = 0

    def validate(self):
        _text(self.id, "project ID", 128)
        _text(self.title, "project title", 256)
        if not self.id or not self.title.strip():
            raise ValueError("Project ID and title are required")
        if type(self.schema_version) is not int or self.schema_version != SCHEMA_VERSION:
            raise ValueError("Unsupported project schema version")
        if self.sample_rate not in (44100, 48000) or type(self.sample_rate) is not int:
            raise ValueError("Unsupported project sample rate")
        _integer(self.revision, "project revision")
        if len(self.tracks) > MAX_TRACKS:
            raise ValueError("Too many tracks")
        seen_tracks, seen_clips = set(), set()
        for track in self.tracks:
            track.validate()
            if track.id in seen_tracks:
                raise ValueError("Duplicate track ID")
            seen_tracks.add(track.id)
            for clip in track.clips:
                if clip.id in seen_clips:
                    raise ValueError("Duplicate project clip ID")
                seen_clips.add(clip.id)


def from_dict(data):
    if not isinstance(data, dict):
        raise ValueError("Expected project object")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported project schema version")
    try:
        if not isinstance(data["tracks"], list) or len(data["tracks"]) > MAX_TRACKS:
            raise ValueError("Invalid tracks array")
        tracks = []
        for item in data["tracks"]:
            track = dict(item)
            if not isinstance(track["clips"], list) or len(track["clips"]) > MAX_CLIPS_PER_TRACK:
                raise ValueError("Invalid clips array")
            track["clips"] = [Clip(**clip) for clip in track["clips"]]
            tracks.append(Track(**track))
        project = AudioProject(**{**data, "tracks": tracks})
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("Invalid project document") from exc
    project.validate()
    return project


def to_dict(project):
    """The saved form: like asdict(), minus fields at their defaults that earlier builds
    don't know (source_offset_frames), so files without trims stay readable by them."""
    data = asdict(project)
    for track in data["tracks"]:
        for clip in track["clips"]:
            if not clip.get("source_offset_frames"):
                clip.pop("source_offset_frames", None)
    return data


def read_project(path):
    """Reject corrupt/future documents without writing any user data."""
    with open(path, encoding="utf-8") as handle:
        return from_dict(json.load(handle))


def save_project(path, project):
    """Validate, write to same-directory temp file, atomically replace target."""
    project.validate()
    path = Path(path)
    if path.exists():
        previous = read_project(path)
        if previous.id != project.id:
            raise ValueError("Refusing to overwrite another project")
        if previous.revision > project.revision:
            raise ValueError("Refusing to overwrite a newer project revision")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(to_dict(project), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".sonic-rift-", suffix=".tmp", delete=False) as handle:
            temp_name = handle.name
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def new_voice_project(title, text, voice_id="", sample_rate=48000):
    """Non-destructively represent legacy Create input as an unrendered voice clip."""
    _text(text, "generation text", 100000)
    if not text.strip():
        raise ValueError("Cannot migrate empty text")
    clip = Clip(new_id(), "voice", 0, 0, text=text, voice_id=voice_id)
    track = Track(new_id(), "voice", "Narration", clips=[clip])
    project = AudioProject(new_id(), title, sample_rate=sample_rate, tracks=[track])
    project.validate()
    return project
