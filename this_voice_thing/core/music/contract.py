"""The engine-neutral Music contract: what a user asks for, and what comes back.

Qt-free and versioned, so the Music page, tests and a future agent adapter (#130)
all speak the same request and result. Each engine declares its capabilities;
a request is checked against them before anything runs, so an unsupported
control is reported, never silently ignored.

Generated music is not bit-for-bit reproducible across GPUs or driver versions, even with
the same seed. What is deterministic is the validation, the plan (seeds, lengths) and the
provenance recorded with each take.
"""

from dataclasses import asdict, dataclass, field

CONTRACT_VERSION = 1

NOTES = ("C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B")
MODES = ("major", "minor")
KEYS = tuple(f"{note} {mode}" for mode in MODES for note in NOTES)
TIME_SIGNATURES = (2, 3, 4, 6)
MAX_PROMPT_CHARS = 512
MAX_LYRICS_CHARS = 4096
MAX_SEED = 2**31 - 1


class MusicRequestError(ValueError):
    """The request can't run as asked; `problems` lists each reason in plain words."""

    def __init__(self, problems):
        super().__init__(" ".join(problems))
        self.problems = list(problems)


@dataclass(frozen=True)
class MusicCapabilities:
    """What an engine can honour. A control it lacks has a reason in `unsupported`."""
    min_seconds: float
    max_seconds: float
    max_candidates: int
    sample_rate: int
    channels: int
    instrumental: bool = True
    vocals: bool = False            # sung vocals (needs lyrics)
    bpm: bool = False
    bpm_range: tuple = (30, 300)
    key: bool = False
    time_signature: bool = False
    seed: bool = True
    unsupported: dict = field(default_factory=dict)   # control -> why it isn't offered


@dataclass
class MusicRequest:
    engine: str
    prompt: str                     # what the music is: purpose, feel, instruments
    seconds: float
    instrumental: bool = True
    lyrics: str = ""                # the user's own words; only with instrumental=False
    candidates: int = 2
    seed: int = None                # None: the app picks one and records it
    bpm: int = None                 # None: the engine decides
    key: str = ""                   # e.g. "D minor"; "" lets the engine decide
    time_signature: int = None      # beats per bar
    genre: str = ""
    mood: str = ""
    instrumentation: str = ""
    contract_version: int = CONTRACT_VERSION

    def caption(self):
        """The text description the engine receives: the prompt plus the style fields."""
        parts = [self.prompt.strip()]
        for label, value in (("genre", self.genre), ("mood", self.mood), ("instrumentation", self.instrumentation)):
            if value.strip():
                parts.append(f"{label}: {value.strip()}")
        if self.instrumental:
            parts.append("instrumental, no vocals")
        return ", ".join(part for part in parts if part)

    def seeds(self):
        """One seed per candidate, consecutive from the request's seed."""
        start = int(self.seed or 0)
        return [(start + index) % (MAX_SEED + 1) for index in range(int(self.candidates))]


def validate(request, capabilities):
    """Problems with `request` for an engine with `capabilities` (empty when it can run)."""
    caps, problems = capabilities, []
    if request.contract_version != CONTRACT_VERSION:
        problems.append(f"This request uses Music contract version {request.contract_version}; "
                        f"this app speaks version {CONTRACT_VERSION}.")
    if not request.prompt.strip():
        problems.append("Describe the music first.")
    if len(request.caption()) > MAX_PROMPT_CHARS:
        problems.append(f"The description is too long (keep it under {MAX_PROMPT_CHARS} characters, "
                        "style fields included).")
    try:
        seconds = float(request.seconds)
    except (TypeError, ValueError):
        seconds = float("nan")
    if not caps.min_seconds <= seconds <= caps.max_seconds:
        problems.append(f"Length must be between {caps.min_seconds:.0f} and {caps.max_seconds:.0f} seconds.")
    if not isinstance(request.candidates, int) or not 1 <= request.candidates <= caps.max_candidates:
        problems.append(f"Ask for 1 to {caps.max_candidates} takes.")
    if request.seed is not None and (not isinstance(request.seed, int) or not 0 <= request.seed <= MAX_SEED):
        problems.append("The seed must be a whole number from 0 to 2147483647.")
    if request.instrumental:
        if request.lyrics.strip():
            problems.append("Lyrics need a vocal song; switch off Instrumental or clear the lyrics.")
        if not caps.instrumental:
            problems.append("This engine can't make instrumental music.")
    else:
        if not caps.vocals:
            problems.append(caps.unsupported.get("vocals", "This engine can't sing."))
        elif not request.lyrics.strip():
            problems.append("A vocal song needs lyrics: write your own words, or switch on Instrumental.")
        if len(request.lyrics) > MAX_LYRICS_CHARS:
            problems.append(f"Lyrics are too long (keep them under {MAX_LYRICS_CHARS} characters).")
    if request.bpm is not None:
        low, high = caps.bpm_range
        if not caps.bpm:
            problems.append(caps.unsupported.get("bpm", "This engine doesn't take a tempo."))
        elif not isinstance(request.bpm, int) or not low <= request.bpm <= high:
            problems.append(f"Tempo must be {low} to {high} BPM.")
    if request.key:
        if not caps.key:
            problems.append(caps.unsupported.get("key", "This engine doesn't take a key."))
        elif request.key not in KEYS:
            problems.append(f"“{request.key}” isn't a key this app knows (for example “D minor”).")
    if request.time_signature is not None:
        if not caps.time_signature:
            problems.append(caps.unsupported.get("time_signature", "This engine doesn't take a time signature."))
        elif request.time_signature not in TIME_SIGNATURES:
            problems.append("Time signature must be 2, 3, 4 or 6 beats per bar.")
    return problems


def check(request, capabilities):
    problems = validate(request, capabilities)
    if problems:
        raise MusicRequestError(problems)


@dataclass
class MusicTake:
    path: str                       # a validated WAV in the job's working folder
    seed: int
    seconds: float
    sample_rate: int
    channels: int
    elapsed_seconds: float
    metrics: dict = field(default_factory=dict)       # loudness, peak (mastering.measure)
    engine_notes: dict = field(default_factory=dict)  # what the engine reports it chose (e.g. bpm, key)


@dataclass
class MusicResult:
    request: MusicRequest
    engine: str
    model: str                      # repo id
    model_revision: str             # exact weights commit
    source_revision: str            # exact engine source commit
    license: str
    device: str
    takes: list = field(default_factory=list)
    cancelled: bool = False
    elapsed_seconds: float = 0.0
    peak_vram_mb: int = 0
    contract_version: int = CONTRACT_VERSION

    def to_dict(self):
        return asdict(self)
