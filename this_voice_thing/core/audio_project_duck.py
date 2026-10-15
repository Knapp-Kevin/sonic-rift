"""Speech-driven ambience ducking for staged Sonic Rift timeline mixes.

Uses rendered narration PCM, not text length or synthetic timing guesses. Operates
on pre-master stems and returns new buffers, leaving the input mix untouched.
"""

import math

import numpy as np

from this_voice_thing.core.audio_timeline_mix import TimelineMix


def duck_ambience(project, raw_mix, attenuation_db=-10.0, threshold_db=-42.0,
                  attack_ms=20.0, release_ms=350.0):
    """Lower sound-track stems while voice PCM is active; preserve voice/effects.

    Duck gain rises smoothly over attack time and recovers over release time.
    The signal remains unmastered; a finishing pass is required before export.
    """
    project.validate()
    if raw_mix.sample_rate != project.sample_rate:
        raise ValueError("Mix sample rate differs from project")
    for value, lower, upper, label in (
        (attenuation_db, -36, 0, "attenuation"),
        (threshold_db, -90, 0, "threshold"),
        (attack_ms, 1, 1000, "attack"),
        (release_ms, 10, 10000, "release"),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lower <= value <= upper:
            raise ValueError(f"Invalid duck {label}")
    if raw_mix.audio.ndim != 2 or raw_mix.audio.shape[1] != 2:
        raise ValueError("Expected stereo timeline mix")
    frames = len(raw_mix.audio)
    stems = {}
    narration = np.zeros((frames, 2), dtype=np.float32)
    for track in project.tracks:
        stem = raw_mix.stems.get(track.id)
        if stem is None or stem.shape != narration.shape:
            raise ValueError("Timeline stem is missing or has wrong dimensions")
        stems[track.id] = stem.copy()
        if track.kind == "voice":
            narration += stem
    if not any(t.kind == "sound" and not t.muted for t in project.tracks) or attenuation_db == 0:
        return TimelineMix(sum(stems.values(), np.zeros_like(narration)), project.sample_rate, stems)

    energy = np.mean(narration.astype(np.float64) ** 2, axis=1)
    window = max(1, int(0.01 * project.sample_rate))
    cumulative = np.concatenate(([0.0], np.cumsum(energy)))
    indices = np.arange(frames)
    end = np.minimum(indices + window, frames)
    rms_power = (cumulative[end] - cumulative[indices]) / np.maximum(1, end - indices)
    active = rms_power >= 10 ** (threshold_db / 10)

    attack_coeff = math.exp(-1.0 / (attack_ms / 1000 * project.sample_rate))
    release_coeff = math.exp(-1.0 / (release_ms / 1000 * project.sample_rate))
    envelope = np.empty(frames, dtype=np.float32)
    level = 0.0
    for i, speaking in enumerate(active):
        coefficient = attack_coeff if speaking else release_coeff
        level = coefficient * level + (1 - coefficient) * float(speaking)
        envelope[i] = level
    target_gain = 10 ** (attenuation_db / 20)
    duck_gain = (1 - (1 - target_gain) * envelope)[:, None]
    for track in project.tracks:
        if track.kind == "sound" and not track.muted:
            stems[track.id] *= duck_gain
    combined = sum(stems.values(), np.zeros_like(narration))
    return TimelineMix(combined, project.sample_rate, stems)
