"""How a project's tracks sit against each other, for Studio's Check balance.

Renders the arranged mix exactly as Play mix and Export do (track gains, clip gains and fades,
mute, ducking), then measures each track's stem with BS.1770 loudness, split into the
stretches where a voice is speaking and the rest. Nothing is written to disk.
"""

import math

import numpy as np

from this_voice_thing.core.audio_project_duck import duck_ambience, voice_activity
from this_voice_thing.core.audio_timeline_mix import render_timeline
from this_voice_thing.core.soundscape import mastering

SILENT = float("-inf")
MIN_SECONDS = 0.4          # BS.1770 needs at least one 400 ms block


def _loudness(stem, mask, sample_rate):
    """Integrated loudness of the frames in `mask`; -inf if under 0.4 s or silent."""
    if np.count_nonzero(mask) < MIN_SECONDS * sample_rate:
        return SILENT
    value = mastering.integrated_lufs(stem[mask], sample_rate)
    return value if math.isfinite(value) else SILENT


def balance_report(project, resolve):
    """One row per track: {track_id, name, kind, muted, with_voice, without_voice, under_voice}.

    `with_voice` / `without_voice` are the track's loudness (LUFS) while any voice speaks and
    while none does; `under_voice` is how many dB the track sits below the voices while they
    speak (None for voice tracks, or when either side is silent). Muted tracks are measured as
    silent, as they play."""
    project.validate()
    raw = render_timeline(project, resolve)
    mixed = duck_ambience(project, raw)
    rate = project.sample_rate
    narration = np.zeros_like(mixed.audio)
    for track in project.tracks:
        if track.kind == "voice" and not track.muted:
            narration += raw.stems[track.id]
    speaking = voice_activity(narration, rate)
    quiet = ~speaking
    voices = _loudness(narration, speaking, rate)
    rows = []
    for track in project.tracks:
        stem = mixed.stems[track.id]
        if track.muted:
            stem = np.zeros_like(stem)
        with_voice = _loudness(stem, speaking, rate)
        without_voice = _loudness(stem, quiet, rate)
        under = None
        if track.kind != "voice" and math.isfinite(voices) and math.isfinite(with_voice):
            under = round(voices - with_voice, 1)
        rows.append({"track_id": track.id, "name": track.name, "kind": track.kind, "muted": track.muted,
                     "with_voice": with_voice, "without_voice": without_voice, "under_voice": under})
    return {"voices": voices, "speaking_seconds": float(np.count_nonzero(speaking)) / rate, "tracks": rows}


def _lufs(value):
    return "silent" if not math.isfinite(value) else f"{value:.1f} LUFS".replace("-", "−")


def describe(row):
    """The short badge Studio shows on a track after Check balance."""
    if row["muted"]:
        return "Muted"
    if row["kind"] == "voice":
        return f"Voices {_lufs(row['with_voice'])}"
    if row["under_voice"] is not None:
        return f"{row['under_voice']:.1f} dB under the voices"
    return f"{_lufs(row['without_voice'])}, no voice over it"


def summary(report):
    """One line for the whole mix: the non-voice track that comes closest to the voices."""
    if report["speaking_seconds"] < MIN_SECONDS:
        return "No voice long enough to compare against"
    gaps = [row for row in report["tracks"] if row["under_voice"] is not None]
    if not gaps:
        return f"Voices {_lufs(report['voices'])}, nothing under them"
    closest = min(gaps, key=lambda row: row["under_voice"])
    return f"Closest to the voices: {closest['name']}, {closest['under_voice']:.1f} dB under"
