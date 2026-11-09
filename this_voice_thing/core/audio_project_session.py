"""Undoable, UI-agnostic edits for Sonic Rift layered audio projects.

Edits operate on deep copies and publish only fully validated snapshots. No source
media, existing voice profiles, or audio settings are ever modified here.
"""
from copy import deepcopy
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path

from this_voice_thing.core.audio_project import AudioProject, Clip, Track, from_dict, save_project, new_id

MAX_HISTORY = 100
MAX_CLIPBOARD_CLIPS = 32
MAX_TIMELINE_SECONDS = 36000  # Studio editing and mix controls use a 10-hour horizon.


@dataclass(frozen=True)
class ClipClipboard:
    """Process-local editing intent, not an external-authority or disk format.

    The clip objects are snapshots; paste always deep-copies and revalidates
    them. No media bytes, absolute file paths or external destinations appear.
    """
    project_id: str
    sample_rate: int
    origin_frame: int
    items: tuple   # (source_track_id, Clip), in project-lane and time order



def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def may_attach_import_result(project, project_id, revision):
    """Reject late worker results after any project switch or edit."""
    return (project.id == project_id and project.revision == revision)


def generated_take_target(project, project_id, clip_id, text, previous_asset_id):
    """The voice clip a finished in-editor narration render may attach to: (clip, "") or
    (None, reason). Other edits made meanwhile are fine; the result is stale only if this
    clip's own script or take changed, it was removed, or another project is open."""
    if project.id != project_id:
        return None, "A different project is open now, so the new take wasn't attached."
    clip = next((c for t in project.tracks for c in t.clips if c.id == clip_id), None)
    if clip is None or clip.kind != "voice":
        return None, "The script was removed while it was generating, so the new take wasn't attached."
    if clip.text != text:
        return None, "The script was edited while it was generating, so the new take wasn't attached."
    if clip.asset_id != previous_asset_id:
        return None, "Another take was attached while this one was generating, so it wasn't replaced."
    return clip, ""


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


def sound_track_for(project, selection, is_music, asset_is_music):
    """The selected sound track a kept sound may join, or None for a track of its own.

    Music and other sounds don't share a track: music added while the waves are selected
    would otherwise sit on the waves' lane, and their gains couldn't be set apart. An empty
    sound track takes either. `asset_is_music(asset_id)` says whether a clip holds music."""
    track_id = compatible_track_id(project, selection, "sound")
    track = next((t for t in project.tracks if t.id == track_id), None)
    if track is None:
        return None
    if all(bool(asset_is_music(clip.asset_id)) == bool(is_music) for clip in track.clips):
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

    def split_clip(self, clip_id, at_frame):
        """Split rendered audio at an absolute sample frame, without changing source PCM.

        Reject a cut through a fade: the schema cannot preserve a partial linear
        fade without an additional envelope parameter. A rejected edit leaves the
        document and undo history unchanged. The right clip gets a fresh ID.
        """
        if type(at_frame) is not int or at_frame < 0:
            raise ValueError("Split position must be a non-negative sample frame")
        right_id = new_id()

        def edit(project):
            for track in project.tracks:
                for index, clip in enumerate(track.clips):
                    if clip.id != clip_id:
                        continue
                    if not clip.asset_id or clip.frame_count < 2:
                        raise ValueError("Only rendered audio can be split")
                    left_count = at_frame - clip.start_frame
                    right_count = clip.frame_count - left_count
                    if left_count <= 0 or right_count <= 0:
                        raise ValueError("Split must lie strictly inside the clip")
                    if (left_count < clip.fade_in_frames
                            or right_count < clip.fade_out_frames):
                        raise ValueError("Cannot split through an existing fade")
                    left, right = deepcopy(clip), deepcopy(clip)
                    left.frame_count = left_count
                    left.fade_out_frames = 0
                    right.id = right_id
                    right.start_frame = at_frame
                    right.frame_count = right_count
                    right.source_offset_frames += left_count
                    right.fade_in_frames = 0
                    track.clips[index:index + 1] = [left, right]
                    return
            raise KeyError(f"Unknown clip: {clip_id}")

        self.apply(edit)
        return right_id

    def duplicate_clip(self, clip_id, start_frame=None):
        """Copy a rendered clip onto its track, retaining a read-only source reference.

        The default placement is directly after the source clip; overlaps are
        permitted when a caller supplies an explicit absolute frame.
        """
        if start_frame is not None and (type(start_frame) is not int or start_frame < 0):
            raise ValueError("Duplicate position must be a non-negative sample frame")
        duplicate_id = new_id()

        def edit(project):
            for track in project.tracks:
                for index, clip in enumerate(track.clips):
                    if clip.id != clip_id:
                        continue
                    if not clip.asset_id or clip.frame_count <= 0:
                        raise ValueError("Only rendered audio can be duplicated")
                    duplicate = deepcopy(clip)
                    duplicate.id = duplicate_id
                    duplicate.start_frame = (
                        clip.start_frame + clip.frame_count if start_frame is None
                        else start_frame
                    )
                    track.clips.insert(index + 1, duplicate)
                    return
            raise KeyError(f"Unknown clip: {clip_id}")

        self.apply(edit)
        return duplicate_id

    def copy_clips(self, clip_ids):
        """Snapshot 1-32 rendered clips for project-local, non-destructive paste.

        Copy does not alter the project, revision, media, undo or redo history.
        The clipboard is not a security token and is never passed raw to MCP.
        """
        if (type(clip_ids) not in (tuple, list) or not 1 <= len(clip_ids) <= MAX_CLIPBOARD_CLIPS
                or any(type(clip_id) is not str or not clip_id for clip_id in clip_ids)
                or len(set(clip_ids)) != len(clip_ids)):
            raise ValueError("Select 1-32 distinct clip IDs to copy")
        requested = set(clip_ids)
        found = []
        for track in self.project.tracks:
            for clip in sorted(track.clips, key=lambda c: (c.start_frame, c.id)):
                if clip.id not in requested:
                    continue
                if not clip.asset_id or clip.frame_count <= 0:
                    raise ValueError("Only rendered audio clips can be copied")
                found.append((track.id, deepcopy(clip)))
        if len(found) != len(requested):
            raise KeyError("One or more selected clips no longer exist")
        return ClipClipboard(
            self.project.id, self.project.sample_rate,
            min(clip.start_frame for _, clip in found), tuple(found))

    def paste_clips(self, clipboard, at_frame, *, target_track_id=None, expected_revision=None):
        """Atomically paste selected clips at one frame, preserving relative offsets.

        Existing source track IDs remain the default paste destinations. A target
        track override is allowed only for a single-lane clipboard with matching
        kind. Every failure leaves project and undo history unchanged.
        """
        if type(clipboard) is not ClipClipboard:
            raise ValueError("Expected an in-memory clip clipboard")
        if type(at_frame) is not int or at_frame < 0:
            raise ValueError("Paste position must be a non-negative whole frame")
        if (target_track_id is not None
                and (type(target_track_id) is not str or not target_track_id)):
            raise ValueError("Invalid target track ID")
        if expected_revision is not None and (
                type(expected_revision) is not int
                or expected_revision != self.project.revision):
            raise ValueError("Project changed before paste; refresh and retry")
        if (clipboard.project_id != self.project.id
                or clipboard.sample_rate != self.project.sample_rate):
            raise ValueError("Clipboard belongs to another project or sample rate")
        if not 1 <= len(clipboard.items) <= MAX_CLIPBOARD_CLIPS:
            raise ValueError("Clipboard has no valid clips")
        if type(clipboard.origin_frame) is not int or clipboard.origin_frame < 0:
            raise ValueError("Invalid clipboard origin")
        if target_track_id is not None and len({tid for tid, _ in clipboard.items}) != 1:
            raise ValueError("Cannot redirect a multi-track selection to one lane")
        pasted_ids = [new_id() for _ in clipboard.items]

        def edit(project):
            tracks = {track.id: track for track in project.tracks}
            placements = []
            for (source_track_id, original), clip_id in zip(clipboard.items, pasted_ids):
                if type(source_track_id) is not str or type(original) is not Clip:
                    raise ValueError("Invalid clipboard clip entry")
                if not original.asset_id or original.frame_count <= 0:
                    raise ValueError("Clipboard contains unrendered audio")
                destination = tracks.get(
                    target_track_id if target_track_id is not None else source_track_id)
                if destination is None:
                    raise KeyError("Destination track no longer exists")
                if destination.kind != original.kind:
                    raise ValueError("Cannot paste a clip into a different track kind")
                delta = original.start_frame - clipboard.origin_frame
                if delta < 0 or at_frame + delta + original.frame_count > (
                        MAX_TIMELINE_SECONDS * project.sample_rate):
                    raise ValueError("Pasted audio exceeds the timeline boundary")
                clip = deepcopy(original)
                clip.id = clip_id
                clip.start_frame = at_frame + delta
                placements.append((destination, clip))
            for track, clip in placements:
                track.clips.append(clip)

        self.apply(edit)
        return tuple(pasted_ids)

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
