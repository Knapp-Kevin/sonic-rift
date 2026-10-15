"""Deterministic, Qt-free PCM layering of validated Sonic Rift project clips.

This is an unmastered timeline mix, not a full renderer/exporter. A caller supplies
asset data via an ID-only resolver; no arbitrary paths are read from documents.
"""

from dataclasses import dataclass
from math import gcd

import numpy as np
from scipy.signal import resample_poly


DEFAULT_MAX_MIX_BYTES = 512 * 1024 * 1024


@dataclass
class TimelineMix:
    audio: np.ndarray
    sample_rate: int
    stems: dict[str, np.ndarray]


def _source_pcm(payload, desired_rate):
    try:
        pcm, source_rate = payload
    except (TypeError, ValueError) as exc:
        raise ValueError("Resolver must return (audio, sample_rate)") from exc
    if type(source_rate) is not int or not 8000 <= source_rate <= 192000:
        raise ValueError("Invalid source sample rate")
    data = np.asarray(pcm, dtype=np.float32)
    if data.ndim == 1:
        data = data[:, None]
    if data.ndim != 2 or data.shape[1] not in (1, 2) or len(data) == 0:
        raise ValueError("Expected nonempty mono/stereo source audio")
    if not np.all(np.isfinite(data)):
        raise ValueError("Source contains nonfinite samples")
    if source_rate != desired_rate:
        factor = gcd(source_rate, desired_rate)
        data = resample_poly(data, desired_rate // factor, source_rate // factor, axis=0)
    if data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    return np.asarray(data, dtype=np.float32)


def render_timeline(project, resolve_asset, max_mix_bytes=DEFAULT_MAX_MIX_BYTES):
    """Assemble raw stereo mix + pre-master stems; leaves input project/assets intact.

    resolve_asset(asset_id) -> (PCM mono/stereo array, source sample rate).
    Any unresolved or unrendered clip raises an actionable error rather than
    silently dropping it. Use mastering separately before delivery/export.
    """
    project.validate()
    if type(max_mix_bytes) is not int or max_mix_bytes < 1024:
        raise ValueError("Invalid PCM memory budget")
    ends = [c.start_frame + c.frame_count for t in project.tracks for c in t.clips]
    if not ends or max(ends) == 0:
        raise ValueError("Project has no rendered audio")
    total = max(ends)
    if total * 2 * np.dtype(np.float32).itemsize * (len(project.tracks) + 1) > max_mix_bytes:
        raise ValueError("Project exceeds unmastered PCM memory budget")
    stems = {}
    mixed = np.zeros((total, 2), dtype=np.float32)
    for track in project.tracks:
        stem = np.zeros_like(mixed)
        if not track.muted:
            for clip in track.clips:
                if not clip.asset_id or clip.frame_count == 0:
                    raise ValueError(f"Unrendered or missing clip asset: {clip.id}")
                try:
                    samples = _source_pcm(resolve_asset(clip.asset_id), project.sample_rate)
                except (OSError, KeyError, FileNotFoundError) as exc:
                    raise ValueError(f"Cannot resolve clip asset: {clip.asset_id}") from exc
                n = clip.frame_count
                if len(samples) < n and not clip.loop:
                    raise ValueError(f"Source shorter than nonlooping clip: {clip.id}")
                if len(samples) < n:
                    times = (n + len(samples) - 1) // len(samples)
                    segment = np.tile(samples, (times, 1))[:n].copy()
                else:
                    segment = samples[:n].copy()
                if clip.fade_in_frames:
                    segment[:clip.fade_in_frames] *= np.linspace(
                        0, 1, clip.fade_in_frames, dtype=np.float32)[:, None]
                if clip.fade_out_frames:
                    segment[-clip.fade_out_frames:] *= np.linspace(
                        1, 0, clip.fade_out_frames, dtype=np.float32)[:, None]
                segment *= np.float32(10 ** (clip.gain_db / 20))
                stem[clip.start_frame:clip.start_frame + n] += segment
            stem *= np.float32(10 ** (track.gain_db / 20))
        stems[track.id] = stem
        mixed += stem
    return TimelineMix(mixed, project.sample_rate, stems)
