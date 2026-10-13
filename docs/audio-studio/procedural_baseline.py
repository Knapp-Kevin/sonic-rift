"""Zero-model procedural baseline for #53 Phase 0.

Every loop is built to be periodic by construction: noise is shaped by circular (FFT)
filtering, modulators complete whole cycles per loop, and discrete events wrap around
the loop boundary. Then each file is measured: loudness, peaks, and the seam.
"""
import json
import os
import sys
import time

import numpy as np
import pyloudnorm
import soundfile as sf
from scipy.signal import resample_poly

SR = 48000
LOOP_S = 60.0
N = int(SR * LOOP_S)
# Usage: python procedural_baseline.py OUTPUT_DIR  (writes ~120 MB of WAV/OGG/MP3; keep it out of the repo)
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "procedural_out")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(53)
T = np.arange(N) / SR


def shaped_noise(n, shape):
    """Periodic noise with |spectrum| = shape(freqs): circular, so it loops seamlessly."""
    spec = np.fft.rfft(rng.standard_normal(n))
    freqs = np.fft.rfftfreq(n, 1 / SR)
    spec *= shape(np.maximum(freqs, 1e-3))
    x = np.fft.irfft(spec, n)
    return x / (np.std(x) + 1e-12)


def band(lo, hi, tilt=0.0):
    """Smooth band-pass magnitude with a 1/f^tilt slope."""
    def shape(f):
        return (f ** -tilt) / np.sqrt(1 + (lo / f) ** 4) / np.sqrt(1 + (f / hi) ** 4)
    return shape


def periodic_lfo(cycles, phase=0.0):
    return 0.5 - 0.5 * np.cos(2 * np.pi * cycles * T / LOOP_S + phase)


def wrap_add(buf, start, event):
    idx = (start + np.arange(len(event))) % len(buf)
    np.add.at(buf, idx, event)


def stereo(left, right):
    return np.stack([left, right], axis=1)


# --- sounds ------------------------------------------------------------------------
def ocean():
    # Uneven wave lengths that sum exactly to the loop, so the swell pattern is periodic.
    lengths = np.array([9.5, 11.0, 8.5, 12.0, 9.0, 10.0])
    lengths *= LOOP_S / lengths.sum()
    env = np.zeros(N)
    start = 0.0
    for i, length in enumerate(lengths):
        t = (T - start) % LOOP_S
        rise, crash = 0.45 * length, 0.12 * length
        body = np.where(t < rise, (t / rise) ** 2,
                        np.where(t < rise + crash, 1.0,
                                 np.exp(-(t - rise - crash) / (0.22 * length))))
        body = np.where(t < length, body, 0.0)
        env = np.maximum(env, body * (0.75 + 0.25 * ((i * 7) % 4) / 3))
        start += length
    env = np.convolve(np.concatenate([env[-2400:], env, env[:2400]]), np.hanning(4801) / np.hanning(4801).sum(), "same")[2400:-2400]
    out = []
    for side in range(2):
        rumble = shaped_noise(N, band(30, 400, tilt=1.0))
        wash = shaped_noise(N, band(300, 3500, tilt=0.5))
        hiss = shaped_noise(N, band(2500, 11000, tilt=0.2))
        out.append(0.55 * rumble * (0.35 + 0.65 * env) + 0.45 * wash * env ** 1.5 + 0.25 * hiss * env ** 3)
    return stereo(*out)


def rain(intensity=1.0, drops_per_s=60):
    out = []
    for side in range(2):
        bed = shaped_noise(N, band(400, 9000, tilt=0.6)) * (0.8 + 0.2 * periodic_lfo(3, side))
        drops = np.zeros(N)
        count = int(drops_per_s * LOOP_S * intensity)
        for start in rng.integers(0, N, count):
            dur = int(SR * rng.uniform(0.004, 0.02))
            t = np.arange(dur) / SR
            freq = rng.uniform(2500, 7000)
            tick = np.sin(2 * np.pi * freq * t) * np.exp(-t / rng.uniform(0.0015, 0.006))
            wrap_add(drops, start, tick * rng.uniform(0.2, 1.0))
        drops /= np.std(drops) + 1e-12
        out.append(0.7 * intensity * bed + 0.25 * drops)
    return stereo(*out)


def thunder_event(seconds=9.0):
    n = int(SR * seconds)
    t = np.arange(n) / SR
    crack = shaped_noise(n, band(60, 2500, tilt=1.2)) * np.exp(-t / 0.25) * (t < 1.0)
    roll = shaped_noise(n, band(20, 300, tilt=1.6))
    roll_env = (1 - np.exp(-t / 0.4)) * np.exp(-t / 2.8) * (1 + 0.5 * np.sin(2 * np.pi * 0.7 * t) ** 2)
    return 0.6 * crack + 1.4 * roll * roll_env


def storm():
    base = rain(intensity=1.6, drops_per_s=90)
    for at, gain, pan in ((7.0, 1.0, 0.35), (34.0, 0.7, 0.65), (52.0, 0.85, 0.5)):
        ev = thunder_event() * gain
        wrap_add(base[:, 0], int(at * SR), ev * np.sqrt(1 - pan))
        wrap_add(base[:, 1], int(at * SR), ev * np.sqrt(pan))
    return base


def drone():
    # Frequencies are whole multiples of 1/LOOP_S, so every partial completes whole cycles.
    def snap(f):
        return round(f * LOOP_S) / LOOP_S
    out = []
    for side in range(2):
        x = np.zeros(N)
        for i, (f, a) in enumerate(((55, 1.0), (82.5, 0.6), (110, 0.5), (164.8, 0.3), (220, 0.2))):
            detune = snap(f + (0.15 if side else -0.15) * (i + 1))
            x += a * np.sin(2 * np.pi * detune * T) * (0.6 + 0.4 * periodic_lfo(i + 1, i + side))
        air = shaped_noise(N, band(200, 2000, tilt=1.0)) * 0.15 * periodic_lfo(2, side)
        out.append(x / np.std(x) + air)
    return stereo(*out)


def chime(seconds=1.6):
    n = int(SR * seconds)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f, a, d in ((880, 1.0, 0.9), (1318.5, 0.5, 0.6), (1760, 0.35, 0.45), (2637, 0.15, 0.25)):
        x += a * np.sin(2 * np.pi * f * t) * np.exp(-t / d)
    attack = np.minimum(1.0, t / 0.004)
    x *= attack
    fade = np.ones(n)
    fade[-int(0.05 * SR):] = np.linspace(1, 0, int(0.05 * SR))
    x *= fade
    return stereo(x, x * 0.92)


# --- measurement -------------------------------------------------------------------
def to_lufs(x, target):
    meter = pyloudnorm.Meter(SR)
    x = pyloudnorm.normalize.loudness(x, meter.integrated_loudness(x), target)
    tp = true_peak_db(x)
    if tp > -1.0:  # keep 1 dB true-peak headroom for lossy delivery
        x = x * 10 ** ((-1.0 - tp) / 20)
    return x


def true_peak_db(x):
    up = resample_poly(x, 4, 1, axis=0)
    return 20 * np.log10(np.max(np.abs(up)) + 1e-12)


def seam_metrics(x):
    """Compare the loop wrap with ordinary points inside the loop."""
    diffs = np.abs(np.diff(x, axis=0)).max(axis=1)
    wrap_jump = np.abs(x[0] - x[-1]).max()
    w = int(0.025 * SR)

    def level(seg):
        return 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-12)
    # level step across the wrap vs across 200 random interior points
    across = level(x[-w:]) - level(x[:w])
    inner = []
    for p in rng.integers(w, len(x) - w, 200):
        inner.append(abs(level(x[p - w:p]) - level(x[p:p + w])))

    def flux(a, b):
        sa = np.abs(np.fft.rfft(a.mean(axis=1) * np.hanning(len(a))))
        sb = np.abs(np.fft.rfft(b.mean(axis=1) * np.hanning(len(b))))
        return float(np.sum((sb - sa) ** 2) / (np.sum(sa ** 2) + 1e-12))
    seam_flux = flux(x[-2048:], x[:2048])
    inner_flux = [flux(x[p - 2048:p], x[p:p + 2048]) for p in rng.integers(2048, len(x) - 2048, 200)]
    return {
        "wrap_jump_vs_p99_step": round(float(wrap_jump / np.percentile(diffs, 99)), 3),
        "wrap_level_step_db": round(abs(float(across)), 2),
        "interior_level_step_db_p95": round(float(np.percentile(inner, 95)), 2),
        "wrap_spectral_flux": round(seam_flux, 3),
        "interior_spectral_flux_p95": round(float(np.percentile(inner_flux, 95)), 3),
    }


def measure(name, x, seconds, loop):
    meter = pyloudnorm.Meter(SR)
    row = {
        "name": name, "seconds": round(len(x) / SR, 3), "generate_s": round(seconds, 2),
        "integrated_lufs": round(float(meter.integrated_loudness(x)), 2),
        "sample_peak_dbfs": round(float(20 * np.log10(np.max(np.abs(x)) + 1e-12)), 2),
        "true_peak_dbtp": round(true_peak_db(x), 2),
        "clipped_samples": int(np.sum(np.abs(x) >= 1.0)),
        "dc_offset": round(float(np.mean(x)), 5),
    }
    if loop:
        row.update(seam_metrics(x))
    return row


def write_blocks(path, x, **kwargs):
    """libsndfile's Vorbis/MP3 encoders overflow the stack on Windows when handed a
    whole 60 s buffer in one call (fatal 'stack overflow'); write in blocks instead."""
    with sf.SoundFile(path, "w", SR, x.shape[1], **kwargs) as handle:
        for i in range(0, len(x), 4096):
            handle.write(x[i:i + 4096])


def export(name, x, loop):
    sf.write(os.path.join(OUT, f"{name}.wav"), x, SR, subtype="PCM_24")
    sizes = {"wav_kb": os.path.getsize(os.path.join(OUT, f"{name}.wav")) // 1024}
    for ext, kwargs in (("ogg", {"format": "OGG", "subtype": "VORBIS"}),
                        ("mp3", {"format": "MP3", "subtype": "MPEG_LAYER_III"})):
        path = os.path.join(OUT, f"{name}.{ext}")
        try:
            write_blocks(path, x, **kwargs)
            sizes[f"{ext}_kb"] = os.path.getsize(path) // 1024
        except Exception as exc:
            sizes[f"{ext}_kb"] = f"unsupported: {exc}"
    if loop:  # three passes back to back, for listening to the seam
        sf.write(os.path.join(OUT, f"{name}_x3_listen.wav"), np.concatenate([x] * 3), SR, subtype="PCM_16")
    return sizes


SOUNDS = [
    ("ocean_waves", ocean, True, -20.0),
    ("forest_rain", rain, True, -22.0),
    ("thunderstorm", storm, True, -20.0),
    ("ambient_drone", drone, True, -24.0),
    ("ui_chime", chime, False, None),
]

if __name__ == "__main__":
    rows = []
    for name, fn, loop, target in SOUNDS:
        t0 = time.perf_counter()
        x = fn()
        if target is None:
            x = x / np.max(np.abs(x)) * 10 ** (-3 / 20)
        else:
            x = to_lufs(x, target)
        seconds = time.perf_counter() - t0
        row = measure(name, x, seconds, loop)
        row.update(export(name, x, loop))
        rows.append(row)
        print(json.dumps(row), flush=True)
    json.dump({"sample_rate": SR, "loop_seconds": LOOP_S, "python": sys.version.split()[0],
               "rows": rows}, open(os.path.join(OUT, "procedural_metrics.json"), "w"), indent=1)
