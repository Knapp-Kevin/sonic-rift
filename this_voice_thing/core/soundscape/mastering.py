"""Finishing shared by every sound engine: loudness, peaks, loop seams and export."""

import os

import numpy as np
import pyloudnorm
import soundfile as sf
from scipy.signal import resample_poly

TRUE_PEAK_CEILING_DB = -1.0   # headroom so lossy (OGG/MP3) delivery doesn't clip
EXPORT_FORMATS = {
    "wav": {"format": "WAV", "subtype": "PCM_24"},
    "ogg": {"format": "OGG", "subtype": "VORBIS"},
    "mp3": {"format": "MP3", "subtype": "MPEG_LAYER_III"},
}
_BLOCK = 4096


def as_stereo(x):
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 1:
        x = x[:, None]
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    return np.ascontiguousarray(x[:, :2])


def integrated_lufs(x, sr):
    """ITU-R BS.1770 integrated loudness; -inf for silence or clips under 0.4 s."""
    x = as_stereo(x)
    if len(x) < int(0.4 * sr):
        return float("-inf")
    return float(pyloudnorm.Meter(sr).integrated_loudness(x.astype(np.float64)))


def true_peak_db(x):
    up = resample_poly(as_stereo(x), 4, 1, axis=0)
    return float(20 * np.log10(np.max(np.abs(up)) + 1e-12))


def normalize(x, sr, target_lufs, ceiling_db=TRUE_PEAK_CEILING_DB):
    """Gain to `target_lufs`, then pulled down if the true peak would pass `ceiling_db`.
    Short one-shots (no integrated loudness) are peak-normalized to the ceiling instead."""
    x = as_stereo(x)
    loudness = integrated_lufs(x, sr)
    if np.isfinite(loudness):
        x = x * np.float32(10 ** ((target_lufs - loudness) / 20))
    else:
        x = x / (np.max(np.abs(x)) + 1e-12)
    peak = true_peak_db(x)
    if peak > ceiling_db:
        x = x * np.float32(10 ** ((ceiling_db - peak) / 20))
    return x.astype(np.float32)


def make_loop(x, sr, crossfade_seconds=2.0):
    """Turn any clip into a seamless loop by folding its tail over its head.

    The result is `crossfade_seconds` shorter. Its last sample is followed (on wrap) by
    audio that originally came straight after it, so the join is continuous.
    """
    x = as_stereo(x)
    fade = int(min(crossfade_seconds * sr, len(x) // 3))
    if fade < 2:
        return x
    body = x[:-fade].copy()
    ramp = np.linspace(0.0, np.pi / 2, fade, dtype=np.float32)[:, None]
    body[:fade] = x[:fade] * np.sin(ramp) + x[-fade:] * np.cos(ramp)   # equal-power
    return body


def seam_report(x, sr, probes=200):
    """Compare the loop's wrap point with ordinary points inside it.

    `seamless` is True when the wrap changes level, spectrum and sample value no more
    than the 95th percentile of interior points (the seam is as smooth as the sound itself).
    """
    x = as_stereo(x)
    rng = np.random.default_rng(0)
    steps = np.abs(np.diff(x, axis=0)).max(axis=1)
    jump_ratio = float(np.abs(x[0] - x[-1]).max() / (np.percentile(steps, 99) + 1e-12))
    w = int(0.025 * sr)

    def level(seg):
        return 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-12)

    def flux(a, b):
        win = np.hanning(len(a))
        sa = np.abs(np.fft.rfft(a.mean(axis=1) * win))
        sb = np.abs(np.fft.rfft(b.mean(axis=1) * win))
        return float(np.sum((sb - sa) ** 2) / (np.sum(sa ** 2) + 1e-12))

    span = 2048
    points = rng.integers(max(w, span), len(x) - max(w, span), probes)
    wrap_level = abs(level(x[-w:]) - level(x[:w]))
    inner_level = float(np.percentile([abs(level(x[p - w:p]) - level(x[p:p + w])) for p in points], 95))
    wrap_flux = flux(x[-span:], x[:span])
    inner_flux = float(np.percentile([flux(x[p - span:p], x[p:p + span]) for p in points], 95))
    return {
        "seamless": bool(jump_ratio <= 1.0 and wrap_level <= inner_level and wrap_flux <= inner_flux),
        "jump_vs_p99_step": round(jump_ratio, 3),
        "wrap_level_step_db": round(float(wrap_level), 2),
        "interior_level_step_db_p95": round(inner_level, 2),
        "wrap_spectral_flux": round(wrap_flux, 3),
        "interior_spectral_flux_p95": round(inner_flux, 3),
    }


def measure(x, sr, loop):
    x = as_stereo(x)
    row = {
        "seconds": round(len(x) / sr, 3),
        "sample_rate": int(sr),
        "integrated_lufs": round(integrated_lufs(x, sr), 2),
        "true_peak_db": round(true_peak_db(x), 2),
        "clipped_samples": int(np.sum(np.abs(x) >= 1.0)),
    }
    if loop:
        row["seam"] = seam_report(x, sr)
    return row


def write_audio(path, x, sr, fmt):
    """Write one file. libsndfile's Vorbis and MP3 encoders overflow the stack on Windows
    when handed a long buffer in one call, so everything is written in blocks."""
    x = as_stereo(x)
    with sf.SoundFile(path, "w", int(sr), 2, **EXPORT_FORMATS[fmt]) as handle:
        for i in range(0, len(x), _BLOCK):
            handle.write(x[i:i + _BLOCK])
    return path


def export(x, sr, path_without_extension, formats=("wav",)):
    """{format: path} for each requested format."""
    os.makedirs(os.path.dirname(os.path.abspath(path_without_extension)), exist_ok=True)
    return {fmt: write_audio(f"{path_without_extension}.{fmt}", x, sr, fmt) for fmt in formats}
