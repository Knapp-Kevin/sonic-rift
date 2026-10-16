"""Timeline ruler and waveform math independent of the Qt view.

Kept separate so long-project layout and sample bucket boundaries can be
regression-tested without starting an audio device or GUI.
"""
import math

import numpy as np

PEAKS_PER_SECOND = 50


def ruler_tick_step(total_seconds, max_ticks=16):
    """Return a pleasant integer seconds interval with at most max_ticks gaps.

    The 1/2/5 decade progression remains valid for any finite nonnegative
    duration, including projects much longer than the old 300-second cap.
    """
    if (isinstance(total_seconds, bool)
            or not isinstance(total_seconds, (int, float))
            or not math.isfinite(total_seconds)
            or total_seconds < 0):
        raise ValueError("Timeline duration must be finite and nonnegative")
    if type(max_ticks) is not int or max_ticks <= 0:
        raise ValueError("Max ruler ticks must be a positive integer")
    # Preserve the established short-project ruler intervals before scaling up.
    for interval in (1, 2, 5, 10, 15, 30, 60, 120, 300):
        if total_seconds / interval <= max_ticks:
            return interval
    minimum = max(1.0, total_seconds / max_ticks)
    decade = 10 ** math.floor(math.log10(minimum))
    for multiplier in (1, 2, 5, 10):
        step = int(multiplier * decade)
        if step >= minimum:
            return max(1, step)
    raise AssertionError("Unreachable ruler increment")


def envelope(pcm, sample_rate, per_second=PEAKS_PER_SECOND):
    """Normalized peak buckets, including the final incomplete audio bucket."""
    if type(sample_rate) is not int or sample_rate <= 0:
        raise ValueError("Sample rate must be positive")
    if type(per_second) is not int or per_second <= 0:
        raise ValueError("Envelope bucket rate must be positive")
    audio = np.asarray(pcm, dtype=np.float32)
    if audio.ndim == 1:
        audio = np.abs(audio)
    elif audio.ndim == 2 and audio.shape[1] in (1, 2):
        audio = np.max(np.abs(audio), axis=1)
    else:
        raise ValueError("Envelope needs mono or stereo audio")
    if not np.all(np.isfinite(audio)):
        raise ValueError("Envelope samples must be finite")
    if len(audio) == 0:
        return np.zeros(1, dtype=np.float32)

    step = max(1, sample_rate // per_second)
    complete = len(audio) // step
    parts = []
    if complete:
        parts.append(audio[:complete * step].reshape(complete, step).max(axis=1))
    if len(audio) % step:
        parts.append(np.array([audio[complete * step:].max()], dtype=np.float32))
    peaks = np.concatenate(parts)
    maximum = float(peaks.max())
    if maximum <= 0:
        return np.zeros(len(peaks), dtype=np.float32)
    return np.clip(peaks / maximum, 0.0, 1.0).astype(np.float32)
