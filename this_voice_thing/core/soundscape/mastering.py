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


LOOP_FOLD_SECONDS = 2.0


def make_loop(x, sr, crossfade_seconds=LOOP_FOLD_SECONDS):
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


SEAM_SCALES = (0.025, 0.1, 0.4)          # seconds compared on each side of a join
_BAND_EDGES = np.geomspace(50, 16000, 25)


def _band_db(frames, sr):
    """Energy in 24 log-spaced bands, in dB, for each row of `frames`."""
    width = frames.shape[-1]
    power = np.abs(np.fft.rfft(frames * np.hanning(width), axis=-1)) ** 2
    band = np.digitize(np.fft.rfftfreq(width, 1 / sr), _BAND_EDGES)
    energy = np.stack([power[..., band == b].sum(axis=-1) for b in range(1, len(_BAND_EDGES))], axis=-1)
    return 10 * np.log10(energy + 1e-10)


def seam_report(x, sr):
    """Is the loop's wrap point more abrupt than anything that happens inside the loop?

    At three time scales (25 ms, 100 ms, 400 ms) the sound is cut into frames, and each
    pair of neighbouring frames gets a spectral distance (RMS difference of band levels
    in dB). The wrap pair is the last frame followed by the first. A seam is reported
    when, at any scale, the wrap changes the sound more than every natural change inside
    it, or when the sample step across the wrap is bigger than any step inside (a click).

    Calibration (100 procedural loops, 6 deliberately bad joins): no false alarms; it
    catches level trends, a tone cut mid-cycle, a change of sound and abrupt cuts. It
    can miss a join between two similar textures (e.g. two ocean recordings at a similar
    point in their swell), so "no seam detected" is not a listening test.
    """
    x = as_stereo(x).astype(np.float64)
    mono = x.mean(axis=1)
    scales = {}
    for scale in SEAM_SCALES:
        width = int(scale * sr)
        count = len(mono) // width
        if count < 4:
            continue
        levels = _band_db(mono[: count * width].reshape(count, width), sr)
        inside = np.sqrt(np.mean(np.diff(levels, axis=0) ** 2, axis=-1))
        ends = _band_db(np.stack([mono[-width:], mono[:width]]), sr)
        wrap = float(np.sqrt(np.mean((ends[1] - ends[0]) ** 2)))
        scales[f"{int(scale * 1000)}ms"] = {
            "wrap_db": round(wrap, 2), "inside_max_db": round(float(inside.max()), 2),
            # share of inside changes at least as big: 0 = more abrupt than all of them
            "rank": round(float(np.mean(inside >= wrap)), 4)}
    steps = np.abs(np.diff(x, axis=0)).max(axis=1)
    jump = float(np.abs(x[0] - x[-1]).max() / (steps.max() + 1e-12))
    worst = min((s["rank"] for s in scales.values()), default=1.0)
    return {"seamless": bool(worst > 0.0 and jump <= 1.0), "worst_rank": round(worst, 4),
            "jump_vs_max_step": round(jump, 3), "scales": scales}


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
