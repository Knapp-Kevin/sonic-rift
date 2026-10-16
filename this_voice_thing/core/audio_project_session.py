"""Undoable, UI-agnostic edits for Sonic Rift layered audio projects.

Edits operate on deep copies and publish only fully validated snapshots. No source
media, existing voice profiles, or audio settings are ever modified here.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from this_voice_thing.core.audio_project import AudioProject, Clip, Track, from_dict, save_project, new_id

MAX_HISTORY = 100


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def may_attach_import_result(project, project_id, revision):
    """Reject late worker results after any project switch or edit."""
    return (project.id == project_id and project.revision == revision)


def compatible_track_id(project, selection, kind):
    """Resolve a selected track or its clip to a compatible track, without paths."""
    if not selection or not isinstance(selection, tuple) or len(selection) != 2:
        return None
    selected_kind, identifier = selection
    for track in project.tracks:
        if track.kind != kind:
            continue
        if selected_kind == "track" and track.id == identifier:
            return track.id
        if selected_kind == "clip" and any(clip.id == identifier for clip in track.clips):
            return track.id
    return None


class ProjectSession:
    def __init__(self, project, *, path=None, fingerprint=None):
        project.validate()
        self.project = deepcopy(project)
        self.path = Path(path).resolve() if path is not None else None
        self._fingerprint = fingerprint
        self._undo = []
        self._redo = []

    @classmethod
    def open(cls, path):
        """Parse and fingerprint one identical on-disk snapshot, not two reads."""
        path = Path(path).resolve()
        payload = path.read_bytes()
        project = from_dict(json.loads(payload.decode("utf-8")))
        fingerprint = hashlib.sha256(payload).hexdigest()
        return cls(project, path=path, fingerprint=fingerprint)

    @property
    def can_undo(self):
        return bool(self._undo)

    @property
    def can_redo(self):
        return bool(self._redo)

    def apply(self, change):
        """Validate an edit on a clone and commit it as one undoable revision."""
        candidate = deepcopy(self.project)
        change(candidate)
        candidate.validate()
        if replace(candidate, revision=self.project.revision) == self.project:
            return False
        self._undo.append(deepcopy(self.project))
        self._undo = self._undo[-MAX_HISTORY:]
        self._redo.clear()
        candidate.revision = self.project.revision + 1
        self.project = candidate
        return True

    def _restore(self, source, destination):
        if not source:
            return False
        target = deepcopy(source.pop())
        destination.append(deepcopy(self.project))
        if len(destination) > MAX_HISTORY:
            del destination[:-MAX_HISTORY]
        target.revision = self.project.revision + 1
        target.validate()
        self.project = target
        return True

    def undo(self):
        return self._restore(self._undo, self._redo)

    def redo(self):
        return self._restore(self._redo, self._undo)

    def add_track(self, kind, name):
        track_id = new_id()
        self.apply(lambda project: project.tracks.append(Track(track_id, kind, name)))
        return track_id

    def update_track(self, track_id, **changes):
        allowed = {"name", "gain_db", "muted"}
        if not changes or set(changes) - allowed:
            raise ValueError("Unsupported track edit")
        def edit(project):
            track = next((track for track in project.tracks if track.id == track_id), None)
            if track is None:
                raise KeyError(f"Unknown track: {track_id}")
            for key, value in changes.items():
                setattr(track, key, value)
        return self.apply(edit)

    def remove_track(self, track_id):
        def edit(project):
            if not any(track.id == track_id for track in project.tracks):
                raise KeyError(f"Unknown track: {track_id}")
            project.tracks = [track for track in project.tracks if track.id != track_id]
        return self.apply(edit)

    def add_clip(self, track_id, clip):
        if not isinstance(clip, Clip):
            raise TypeError("Expected a project clip")
        def edit(project):
            track = next((track for track in project.tracks if track.id == track_id), None)
            if track is None:
                raise KeyError(f"Unknown track: {track_id}")
            track.clips.append(deepcopy(clip))
        return self.apply(edit)

    def update_clip(self, clip_id, **changes):
        allowed = {"start_frame", "frame_count", "gain_db", "fade_in_frames", "fade_out_frames", "loop", "text",
                   "voice_id", "asset_id", "source_offset_frames"}
        if not changes or set(changes) - allowed:
            raise ValueError("Unsupported clip edit")
        def edit(project):
            clip = next((c for t in project.tracks for c in t.clips if c.id == clip_id), None)
            if clip is None:
                raise KeyError(f"Unknown clip: {clip_id}")
            for key, value in changes.items():
                setattr(clip, key, value)
        return self.apply(edit)

    def place_clip(self, clip_id, start_frame, frame_count, source_offset_frames):
        """Move and/or trim one clip as a single undoable edit (the timeline's drag).

        The source audio is never changed: trimming the start only skips frames of it.
        Fades shorter than the new length are kept; longer ones are shortened to fit.
        """
        for value in (start_frame, frame_count, source_offset_frames):
            if type(value) is not int or value < 0:
                raise ValueError("Clip placement must be whole, non-negative frames")
        if frame_count == 0:
            raise ValueError("A clip can't be trimmed to nothing")
        def edit(project):
            clip = next((c for t in project.tracks for c in t.clips if c.id == clip_id), None)
            if clip is None:
                raise KeyError(f"Unknown clip: {clip_id}")
            if not clip.asset_id:
                raise ValueError("Only clips with audio can be moved or trimmed on the timeline")
            clip.start_frame = start_frame
            clip.frame_count = frame_count
            clip.source_offset_frames = source_offset_frames
            clip.fade_in_frames = min(clip.fade_in_frames, frame_count)
            clip.fade_out_frames = min(clip.fade_out_frames, frame_count)
        return self.apply(edit)

    def attach_narration_take(self, clip_id, asset_id, frame_count):
        """Replace a voice clip's rendered take atomically and preserve undo history.

        Shorter takes must not inherit invalid or overlapping fade lengths from
        the previous recording. The previous source remains in project media.
        """
        def edit(project):
            clip = next((c for t in project.tracks for c in t.clips if c.id == clip_id), None)
            if clip is None:
                raise KeyError(f"Unknown clip: {clip_id}")
            if clip.kind != "voice":
                raise ValueError("Only voice clips can attach narration")
            if type(frame_count) is not int or frame_count <= 0:
                raise ValueError("Narration duration must be positive frames")
            clip.asset_id = asset_id
            clip.frame_count = frame_count
            clip.source_offset_frames = 0          # a trim belonged to the previous take
            clip.fade_in_frames = min(clip.fade_in_frames, frame_count // 2)
            clip.fade_out_frames = min(clip.fade_out_frames, frame_count // 2)
        return self.apply(edit)

    def update_narration_text(self, clip_id, text):
        """Changing script invalidates its previous rendered take, never deletes media."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Narration text cannot be empty")
        def edit(project):
            clip = next((c for t in project.tracks for c in t.clips if c.id == clip_id), None)
            if clip is None:
                raise KeyError(f"Unknown clip: {clip_id}")
            if clip.kind != "voice":
                raise ValueError("Only voice clips can contain narration text")
            clip.text = text.strip()
            clip.asset_id = ""
            clip.frame_count = 0
            clip.source_offset_frames = 0
            clip.fade_in_frames = 0
            clip.fade_out_frames = 0
        return self.apply(edit)

    def remove_clip(self, clip_id):
        def edit(project):
            if not any(c.id == clip_id for track in project.tracks for c in track.clips):
                raise KeyError(f"Unknown clip: {clip_id}")
            for track in project.tracks:
                track.clips = [clip for clip in track.clips if clip.id != clip_id]
        return self.apply(edit)

    def move_track(self, track_id, new_index):
        if type(new_index) is not int:
            raise ValueError("Invalid track index")
        def edit(project):
            position = next((i for i, t in enumerate(project.tracks) if t.id == track_id), None)
            if position is None:
                raise KeyError(f"Unknown track: {track_id}")
            if not 0 <= new_index < len(project.tracks):
                raise ValueError("Track index out of bounds")
            track = project.tracks.pop(position)
            project.tracks.insert(new_index, track)
        return self.apply(edit)

    def ensure_current_file(self):
        """Prevent exporting a stale in-memory view of a changed saved document."""
        if self.path is None or self._fingerprint is None:
            raise ValueError("Save this project before exporting")
        if not self.path.is_file() or _sha(self.path) != self._fingerprint:
            raise ValueError("Project changed on disk; reopen or save a new copy")
        return self.path

    def save(self, path=None):
        """Refuse unnoticed outside edits and accidental overwrite of another file."""
        target = Path(path).resolve() if path is not None else self.path
        if target is None:
            raise ValueError("Choose a project save location")
        if target.exists():
            if target != self.path or self._fingerprint is None:
                raise FileExistsError("Refusing to replace an untracked project file")
            if _sha(target) != self._fingerprint:
                raise ValueError("Project changed on disk; reopen instead of overwriting")
        save_project(target, self.project)
        self.path = target
        self._fingerprint = _sha(target)
        return target
