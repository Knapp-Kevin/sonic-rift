"""Procedural sounds: ambience loops and UI one-shots from plain DSP, no model.

Loops are periodic by construction, so they repeat without a seam:
- noise is shaped by circular (FFT) filtering of a buffer exactly one loop long;
- every modulator completes whole cycles per loop;
- discrete events (drops, thunder) wrap around the loop boundary.

Everything is driven by one seeded random generator, so a preset, seed and settings
always give the same sound.
"""

from dataclasses import dataclass

import numpy as np

SAMPLE_RATE = 48000


@dataclass(frozen=True)
class Preset:
    key: str
    label: str
    description: str
    loop: bool
    default_seconds: float
    target_lufs: float          # integrated loudness the result is mastered to
    intensity_label: str = "Intensity"


PRESETS = {
    "ocean": Preset("ocean", "Ocean waves", "Swells that build, break and wash back.", True, 60.0, -24.0,
                    "Wave size"),
    "rain": Preset("rain", "Rain", "Steady rain on leaves, with individual drops.", True, 60.0, -25.0,
                   "Rainfall"),
    "storm": Preset("storm", "Thunderstorm", "Heavy rain with rolling thunder.", True, 60.0, -23.0,
                    "Storm strength"),
    "wind": Preset("wind", "Wind", "Moving air with slow gusts.", True, 60.0, -25.0, "Gusts"),
    "drone": Preset("drone", "Ambient drone", "A soft, evolving tonal bed.", True, 60.0, -27.0,
                    "Movement"),
    "ui_success": Preset("ui_success", "Chime: success", "A bright two-note rising chime.", False, 1.6,
                         -16.0, "Sparkle"),
    "ui_notify": Preset("ui_notify", "Chime: notification", "A single soft bell.", False, 1.4, -18.0,
                        "Sparkle"),
    "ui_error": Preset("ui_error", "Chime: error", "A low, falling two-note tone.", False, 1.2, -18.0,
                       "Edge"),
}


@dataclass
class _Context:
    n: int
    sr: int
    rng: np.random.Generator
    intensity: float     # 0..1
    brightness: float    # 0..1

    @property
    def seconds(self):
        return self.n / self.sr

    @property
    def t(self):
        return np.arange(self.n) / self.sr


def generate(preset_key, seconds=None, seed=0, intensity=0.5, brightness=0.5, width=0.5,
             sample_rate=SAMPLE_RATE):
    """float32 stereo array (frames, 2) at `sample_rate`. Not loudness-normalized."""
    preset = PRESETS[preset_key]
    seconds = float(preset.default_seconds if seconds is None else seconds)
    if preset.loop and seconds < 5.0:
        raise ValueError("Loops must be at least 5 seconds long.")
    ctx = _Context(
        n=int(round(seconds * sample_rate)), sr=int(sample_rate),
        rng=np.random.default_rng(int(seed)),
        intensity=float(np.clip(intensity, 0.0, 1.0)), brightness=float(np.clip(brightness, 0.0, 1.0)))
    left, right = _BUILDERS[preset_key](ctx)
    return _set_width(left, right, float(np.clip(width, 0.0, 1.0))).astype(np.float32)


# --- building blocks -----------------------------------------------------------------
def _shaped_noise(ctx, lo, hi, tilt=0.0):
    """Periodic noise in a smooth band with a 1/f^tilt slope; brightness moves the top edge."""
    hi = hi * (0.6 + 0.8 * ctx.brightness)
    spec = np.fft.rfft(ctx.rng.standard_normal(ctx.n))
    f = np.maximum(np.fft.rfftfreq(ctx.n, 1 / ctx.sr), 1e-3)
    spec *= (f ** -tilt) / np.sqrt(1 + (lo / f) ** 4) / np.sqrt(1 + (f / hi) ** 4)
    x = np.fft.irfft(spec, ctx.n)
    return x / (np.std(x) + 1e-12)


def _lfo(ctx, cycles, phase=0.0):
    """0..1 raised cosine completing whole cycles per loop."""
    return 0.5 - 0.5 * np.cos(2 * np.pi * max(1, int(round(cycles))) * ctx.t / ctx.seconds + phase)


def _wrap_add(buf, start, event):
    idx = (int(start) + np.arange(len(event))) % len(buf)
    np.add.at(buf, idx, event)


def _smooth_circular(x, width):
    pad = width // 2
    kernel = np.hanning(width)
    kernel /= kernel.sum()
    return np.convolve(np.concatenate([x[-pad:], x, x[:pad]]), kernel, "same")[pad:-pad]


def _set_width(left, right, width):
    mid, side = (left + right) / 2, (left - right) / 2
    side *= 2 * width   # 0 = mono, 0.5 = as built, 1 = wider
    return np.stack([mid + side, mid - side], axis=1)


# --- presets -------------------------------------------------------------------------
def _ocean(ctx):
    count = max(2, int(round(ctx.seconds / 10.0)))
    lengths = ctx.rng.uniform(0.8, 1.2, count)
    lengths *= ctx.seconds / lengths.sum()   # whole waves per loop
    env = np.zeros(ctx.n)
    start = 0.0
    t = ctx.t
    for length in lengths:
        local = (t - start) % ctx.seconds
        rise, crash = 0.45 * length, 0.12 * length
        body = np.where(local < rise, (local / rise) ** 2,
                        np.where(local < rise + crash, 1.0, np.exp(-(local - rise - crash) / (0.22 * length))))
        # No cut at the next wave: the tail keeps decaying under it (and around the loop),
        # so wave boundaries carry no sudden drop in level.
        env = np.maximum(env, body * ctx.rng.uniform(0.7, 1.0))
        start += length
    env = _smooth_circular(env, int(0.1 * ctx.sr) | 1)
    size = 0.5 + ctx.intensity
    sides = []
    for _ in range(2):
        rumble = _shaped_noise(ctx, 30, 400, tilt=1.0)
        wash = _shaped_noise(ctx, 300, 3500, tilt=0.5)
        hiss = _shaped_noise(ctx, 2500, 11000, tilt=0.2)
        sides.append(0.55 * rumble * (0.35 + 0.65 * env) + 0.45 * size * wash * env ** 1.5
                     + 0.25 * size * hiss * env ** 3)
    return sides


def _drops(ctx, per_second):
    drops = np.zeros(ctx.n)
    for start in ctx.rng.integers(0, ctx.n, int(per_second * ctx.seconds)):
        dur = int(ctx.sr * ctx.rng.uniform(0.004, 0.02))
        t = np.arange(dur) / ctx.sr
        freq = ctx.rng.uniform(2500, 7000) * (0.7 + 0.6 * ctx.brightness)
        tick = np.sin(2 * np.pi * freq * t) * np.exp(-t / ctx.rng.uniform(0.0015, 0.006))
        _wrap_add(drops, start, tick * ctx.rng.uniform(0.2, 1.0))
    return drops / (np.std(drops) + 1e-12)


def _rain(ctx, heavy=1.0):
    sides = []
    density = 20 + 100 * ctx.intensity * heavy
    for side in range(2):
        bed = _shaped_noise(ctx, 400, 9000, tilt=0.6) * (0.8 + 0.2 * _lfo(ctx, 3, side))
        sides.append((0.5 + 0.4 * ctx.intensity) * heavy * bed + 0.25 * _drops(ctx, density))
    return sides


def _thunder(ctx, seconds=9.0):
    n = int(ctx.sr * seconds)
    sub = _Context(n, ctx.sr, ctx.rng, ctx.intensity, ctx.brightness)
    t = np.arange(n) / ctx.sr
    crack = _shaped_noise(sub, 60, 2500, tilt=1.2) * np.exp(-t / 0.25) * (t < 1.0)
    roll = _shaped_noise(sub, 20, 300, tilt=1.6)
    roll_env = (1 - np.exp(-t / 0.4)) * np.exp(-t / 2.8) * (1 + 0.5 * np.sin(2 * np.pi * 0.7 * t) ** 2)
    return 0.6 * crack + 1.4 * roll * roll_env


def _storm(ctx):
    left, right = _rain(ctx, heavy=1.6)
    strikes = max(1, int(round(ctx.seconds / 60.0 * (1 + 3 * ctx.intensity))))
    for _ in range(strikes):
        at = ctx.rng.uniform(0, ctx.seconds)
        pan = ctx.rng.uniform(0.25, 0.75)
        ev = _thunder(ctx) * ctx.rng.uniform(0.6, 1.0)
        _wrap_add(left, at * ctx.sr, ev * np.sqrt(1 - pan))
        _wrap_add(right, at * ctx.sr, ev * np.sqrt(pan))
    return left, right


def _wind(ctx):
    gusts = max(2, int(round(ctx.seconds / 12.0)))
    sides = []
    for side in range(2):
        low = _shaped_noise(ctx, 40, 500, tilt=1.2)
        mid = _shaped_noise(ctx, 200, 1800, tilt=0.8)
        gust = _lfo(ctx, gusts, side * 0.6) * _lfo(ctx, gusts * 2 + 1, side)
        depth = 0.3 + 0.7 * ctx.intensity
        sides.append(low * (1 - depth + depth * gust) + 0.6 * mid * gust ** 1.5 * depth)
    return sides


def _drone(ctx):
    def whole(f):  # whole cycles per loop, so every partial joins up at the seam
        return max(1, round(f * ctx.seconds)) / ctx.seconds
    sides = []
    root = 55.0 * (1 + 0.5 * ctx.brightness)
    for side in range(2):
        x = np.zeros(ctx.n)
        for i, (ratio, amp) in enumerate(((1, 1.0), (1.5, 0.6), (2, 0.5), (3, 0.3), (4, 0.2))):
            freq = whole(root * ratio + (0.15 if side else -0.15) * (i + 1))
            move = ctx.intensity * 0.6
            x += amp * np.sin(2 * np.pi * freq * ctx.t) * (1 - move + move * _lfo(ctx, i + 1, i + side))
        air = _shaped_noise(ctx, 200, 2000, tilt=1.0) * 0.15 * _lfo(ctx, 2, side)
        sides.append(x / (np.std(x) + 1e-12) + air)
    return sides


def _bell(ctx, notes):
    """notes: [(start_s, freq_hz, gain)]; a struck bell with inharmonic partials."""
    x = np.zeros(ctx.n)
    t = ctx.t
    partials = ((1.0, 1.0, 0.9), (1.5, 0.5, 0.6), (2.0, 0.35, 0.45), (3.0, 0.15 + 0.3 * ctx.intensity, 0.25))
    for start, freq, gain in notes:
        local = t - start
        on = local >= 0
        for ratio, amp, decay in partials:
            x += on * gain * amp * np.sin(2 * np.pi * freq * ratio * local) * np.exp(-np.maximum(local, 0) / decay)
    x *= np.minimum(1.0, t / 0.004)
    fade = int(0.05 * ctx.sr)
    x[-fade:] *= np.linspace(1, 0, fade)
    return x, x * 0.92


def _ui_success(ctx):
    base = 660 * (0.8 + 0.4 * ctx.brightness)
    return _bell(ctx, [(0.0, base, 0.8), (0.12, base * 1.335, 1.0)])


def _ui_notify(ctx):
    return _bell(ctx, [(0.0, 880 * (0.8 + 0.4 * ctx.brightness), 1.0)])


def _ui_error(ctx):
    base = 330 * (0.8 + 0.4 * ctx.brightness)
    return _bell(ctx, [(0.0, base, 1.0), (0.16, base * 0.75, 0.9)])


_BUILDERS = {
    "ocean": _ocean, "rain": _rain, "storm": _storm, "wind": _wind, "drone": _drone,
    "ui_success": _ui_success, "ui_notify": _ui_notify, "ui_error": _ui_error,
}
