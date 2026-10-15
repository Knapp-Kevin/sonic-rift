"""Non-destructive project mix export to a fresh, atomic delivery directory.

Exports a normalized master and optional post-duck, pre-master track stems.
Those stems are explicitly not bit-identical constituents of the mastered file.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile

import numpy as np

from this_voice_thing.core.audio_project_duck import duck_ambience
from this_voice_thing.core.audio_timeline_mix import render_timeline
from this_voice_thing.core.soundscape import mastering

ALLOWED_FORMATS = frozenset({"wav", "ogg", "mp3"})


class ExportCancelled(RuntimeError):
    """Cooperative user cancellation; no partial delivery directory is published."""


def _check_cancel(should_cancel):
    if should_cancel is not None and should_cancel():
        raise ExportCancelled("Project export cancelled")


def _safe_metrics(row):
    """Convert nonfinite numpy/Python measurement numbers to valid JSON nulls."""
    if isinstance(row, dict):
        return {str(key): _safe_metrics(value) for key, value in row.items()}
    if isinstance(row, (list, tuple)):
        return [_safe_metrics(value) for value in row]
    if isinstance(row, (float, np.floating)):
        return float(row) if math.isfinite(row) else None
    if isinstance(row, np.integer):
        return int(row)
    return row


def export_project(project, media, destination, *, target_lufs=-16.0,
                   formats=("wav",), use_ducking=True, include_stems=True,
                   should_cancel=None):
    """Render and atomically publish a new directory; refuse any overwrite.

    media implements resolve(asset_id). All stored project IDs are opaque and
    do not control destination file paths or directories.
    """
    project.validate()
    if not isinstance(formats, (list, tuple)) or not formats or len(formats) != len(set(formats)) or any(fmt not in ALLOWED_FORMATS for fmt in formats):
        raise ValueError("Unsupported or duplicate export formats")
    if isinstance(target_lufs, bool) or not isinstance(target_lufs, (int, float)) or not math.isfinite(target_lufs) or not -36 <= target_lufs <= -8:
        raise ValueError("Invalid export loudness target")
    if type(use_ducking) is not bool or type(include_stems) is not bool:
        raise ValueError("Invalid export options")

    _check_cancel(should_cancel)
    output = Path(destination)
    if output.exists() or output.is_symlink():
        raise FileExistsError("Refusing to overwrite an existing project export")
    raw = render_timeline(project, media.resolve)
    _check_cancel(should_cancel)
    arranged = duck_ambience(project, raw) if use_ducking else raw
    _check_cancel(should_cancel)
    master = mastering.normalize(arranged.audio, project.sample_rate, float(target_lufs))
    _check_cancel(should_cancel)
    if not np.all(np.isfinite(master)):
        raise ValueError("Master output contains nonfinite samples")
    metrics = _safe_metrics(mastering.measure(master, project.sample_rate, loop=False))
    root = output.parent
    root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".sonicrift-export-", dir=root))
    try:
        files = {}
        for fmt in formats:
            _check_cancel(should_cancel)
            filename = f"master.{fmt}"
            mastering.write_audio(str(stage / filename), master, project.sample_rate, fmt)
            _check_cancel(should_cancel)
            files[fmt] = filename
        stems = {}
        if include_stems:
            (stage / "stems").mkdir()
            for index, track in enumerate(project.tracks, 1):
                _check_cancel(should_cancel)
                digest = hashlib.sha256(track.id.encode("utf-8")).hexdigest()[:12]
                filename = f"stems/track_{index:03d}_{digest}.wav"
                mastering.write_audio(str(stage / filename), arranged.stems[track.id], project.sample_rate, "wav")
                _check_cancel(should_cancel)
                stems[track.id] = filename
        manifest = {
            "schema_version": 1,
            "project_id": project.id,
            "project_revision": project.revision,
            "sample_rate": project.sample_rate,
            "target_lufs": float(target_lufs),
            "ducking_enabled": use_ducking,
            "master_stage": "normalized_and_peak_limited",
            "stem_stage": "post_duck_pre_master",
            "master_files": files,
            "stems": stems,
            "asset_ids": {track.id: [clip.asset_id for clip in track.clips] for track in project.tracks},
            "metrics": metrics,
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        _check_cancel(should_cancel)
        if output.exists():
            raise FileExistsError("Export appeared while rendering; refusing overwrite")
        os.rename(stage, output)
        return output / "manifest.json"
    finally:
        if stage.exists():
            shutil.rmtree(stage)
