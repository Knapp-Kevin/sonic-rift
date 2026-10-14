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


MAX_LIMITING_DB = 6.0      # dense material: more than this audibly squashes ambience
SPARSE_LIMITING_DB = 12.0  # isolated peaks (raindrops, clicks) can take more, inaudibly
SPARSE_FRACTION = 0.01     # "isolated": under 1% of samples over the ceiling


def limit(x, sr, ceiling_db, lookahead_ms=5.0, release_ms=120.0):
    """Look-ahead true-peak limiter: pulls short peaks down to `ceiling_db` with a smooth
    gain curve, leaving everything below the ceiling untouched. Peaks are read from a 4x
    oversampled signal, so sharp transients don't overshoot between samples."""
    x = as_stereo(x)
    ceiling = 10 ** (ceiling_db / 20)
    up = np.abs(resample_poly(x, 4, 1, axis=0))[: len(x) * 4]
    peak = up.reshape(len(x), 4, 2).max(axis=(1, 2))
    need = np.minimum(1.0, ceiling / np.maximum(peak, 1e-12))       # gain each sample needs
    ahead = max(1, int(lookahead_ms / 1000 * sr))
    # Start reducing `ahead` samples early (running minimum over the look-ahead window).
    padded = np.concatenate([need, np.ones(ahead)])
    windows = np.lib.stride_tricks.sliding_window_view(padded, ahead + 1)
    target = windows.min(axis=1)[: len(need)]
    # Instant attack, exponential release.
    release = np.exp(-1.0 / (release_ms / 1000 * sr))
    gain = np.empty_like(target)
    level = 1.0
    for i, value in enumerate(target):     # cheap enough: ~1 s per minute of audio
        level = value if value < level else value + (level - value) * release
        gain[i] = level
    return (x * gain[:, None].astype(np.float32)).astype(np.float32)


def normalize(x, sr, target_lufs, ceiling_db=TRUE_PEAK_CEILING_DB):
    """Gain to `target_lufs` with true peaks under `ceiling_db`.

    Short peaks over the ceiling are limited (up to MAX_LIMITING_DB of reduction) so one
    transient doesn't pull the whole clip below its loudness target; beyond that the
    whole clip is turned down instead. Short one-shots (no integrated loudness) are
    peak-normalized to the ceiling.
    """
    x = as_stereo(x)
    loudness = integrated_lufs(x, sr)
    if not np.isfinite(loudness):
        x = x / (np.max(np.abs(x)) + 1e-12)
        return trim_to_ceiling(x, ceiling_db)
    source = x
    gain_db = target_lufs - loudness
    limited = None              # the last cleanly limited version, if any
    for _attempt in range(3):   # limiting removes some energy, so re-aim after it
        x = source * np.float32(10 ** (gain_db / 20))
        over = true_peak_db(x) - ceiling_db
        if over <= 0:
            limited = None
            break
        sparse = np.mean(np.abs(x).max(axis=1) > 10 ** (ceiling_db / 20)) < SPARSE_FRACTION
        if over > (SPARSE_LIMITING_DB if sparse else MAX_LIMITING_DB):
            break               # too much to limit cleanly at this gain
        limited = limit(x, sr, ceiling_db - 0.1)
        miss = target_lufs - integrated_lufs(limited, sr)
        if abs(miss) < 0.2:
            break
        gain_db += miss
    # Prefer the limited version (slightly under target at worst) over trimming the whole clip.
    return trim_to_ceiling(limited if limited is not None else x, ceiling_db)


def trim_to_ceiling(x, ceiling_db):
    peak = true_peak_db(x)
    if peak > ceiling_db:
        x = x * np.float32(10 ** ((ceiling_db - peak) / 20))
    return x.astype(np.float32)


def is_mono(x, threshold_db=-40.0):
    """True when the side signal is negligible (under -40 dB relative to the mid): some
    "stereo" models, e.g. Stable Audio 3 Small SFX, write two nearly identical channels."""
    x = as_stereo(x).astype(np.float64)
    mid = np.sqrt(np.mean(((x[:, 0] + x[:, 1]) / 2) ** 2)) + 1e-12
    side = np.sqrt(np.mean(((x[:, 0] - x[:, 1]) / 2) ** 2))
    return bool(20 * np.log10(side / mid + 1e-12) < threshold_db)


def widen(x, sr, width=0.5, loop=True, seed=0, crossover_hz=300.0):
    """Stereo from a mono source: the mid stays exactly the source (so it folds back to
    mono cleanly), and a side signal is made by a short (20 ms) random-phase decorrelation
    filter, high-passed so bass stays centred. For loops the filter is applied circularly,
    so the wrap point stays seamless. width 0 = mono, 1 = wide.
    """
    x = as_stereo(x)
    mid = x.mean(axis=1).astype(np.float64)
    if width <= 0:
        return np.stack([mid, mid], axis=1).astype(np.float32)
    rng = np.random.default_rng(seed)
    taps = int(0.02 * sr)
    spectrum = np.exp(1j * rng.uniform(-np.pi, np.pi, taps // 2 + 1))
    spectrum[0] = spectrum[-1] = 1.0
    kernel = np.fft.irfft(spectrum, taps) * np.hanning(taps)
    kernel /= np.sqrt(np.sum(kernel ** 2))
    n = len(mid) if loop else len(mid) + taps
    freqs = np.fft.rfftfreq(n, 1 / sr)
    highpass = 1.0 / np.sqrt(1.0 + (crossover_hz / np.maximum(freqs, 1e-3)) ** 4)
    side = np.fft.irfft(np.fft.rfft(mid, n) * np.fft.rfft(kernel, n) * highpass, n)[: len(mid)]
    side *= float(width)
    return np.stack([mid + side, mid - side], axis=1).astype(np.float32)


LOOP_FOLD_SECONDS = 2.0
SEAM_POLISH_SECONDS = 0.05   # micro-crossfade after inpainting, which can leave a click at the ends


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
