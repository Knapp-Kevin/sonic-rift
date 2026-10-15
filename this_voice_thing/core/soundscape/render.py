"""One request in, finished candidates out, whichever engine makes the sound."""

from dataclasses import dataclass, field

from this_voice_thing.core.soundscape import catalog, mastering, procedural

DEFAULT_MODEL_LUFS = -24.0   # calm background level; presets carry their own


@dataclass
class SoundRequest:
    engine: str                 # catalog key
    seconds: float
    loop: bool = True
    seed: int = 0
    candidates: int = 3
    preset: str = ""            # procedural
    intensity: float = 0.5
    brightness: float = 0.5
    width: float = 0.5
    prompt: str = ""            # models
    negative_prompt: str = ""
    target_lufs: float = None     # None: the preset's (procedural) or DEFAULT_MODEL_LUFS
    start_soft: bool = True       # loops begin at their quietest moment and build
    even_dynamics: bool = False   # gently level loud and quiet stretches


@dataclass
class Candidate:
    audio: object               # float32 (frames, 2)
    sample_rate: int
    seed: int
    metrics: dict = field(default_factory=dict)


def target_lufs(request):
    if request.target_lufs is not None:
        return float(request.target_lufs)
    if request.engine == "procedural":
        return procedural.PRESETS[request.preset].target_lufs
    return DEFAULT_MODEL_LUFS


def render(request, model=None, cancelled=lambda: False, progress=lambda _done, _total: None):
    """Candidates for `request`; `model` is a running SoundModel for model engines."""
    engine = catalog.ENGINES[request.engine]
    is_loop = request.loop and (engine.kind == "model" or procedural.PRESETS[request.preset].loop)
    results = []
    for index in range(max(1, int(request.candidates))):
        if cancelled():
            break
        seed = int(request.seed) + index
        if engine.kind == "procedural":
            preset = procedural.PRESETS[request.preset]
            audio = procedural.generate(request.preset, seconds=request.seconds if preset.loop else None,
                                        seed=seed, intensity=request.intensity,
                                        brightness=request.brightness, width=request.width)
            sample_rate = procedural.SAMPLE_RATE
        else:
            if model is None:
                raise RuntimeError(f"{engine.label} isn't running.")
            options = {"negative_prompt": request.negative_prompt} if request.negative_prompt else {}
            # Folding a take into a loop shortens it; ask for that much more so the loop
            # comes out at the requested length.
            extra = getattr(model, "loop_padding_seconds", 0.0) if is_loop else 0.0
            audio, sample_rate = model.generate(request.prompt, request.seconds + extra, seed=seed, **options)
            if is_loop:
                audio, sample_rate = model.heal_loop(audio, sample_rate, request.prompt, seed=seed)
            if mastering.is_mono(audio):
                # e.g. MOSS-SoundEffect: give it stereo width without touching its mono mix
                audio = mastering.widen(audio, sample_rate, request.width, loop=is_loop, seed=seed)
        if is_loop and request.even_dynamics:
            audio = mastering.even_dynamics(audio, sample_rate, loop=True)
        if is_loop and request.start_soft:
            audio = mastering.start_soft(audio, sample_rate)
        audio = mastering.normalize(audio, sample_rate, target_lufs(request))
        results.append(Candidate(audio, sample_rate, seed, mastering.measure(audio, sample_rate, is_loop)))
        progress(index + 1, request.candidates)
    return results
