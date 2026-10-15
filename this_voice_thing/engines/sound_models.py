"""Main-app side of the sound-generation model engines.

Each model runs in its own environment (engines/<dir>/.venv) because its upstream pins
different PyTorch and Python versions from the app (MOSS-SoundEffect v2: torch 2.9 on
Python 3.12).
Upstream code is pinned to a commit so an install is reproducible.
"""

import os
import tempfile
from dataclasses import dataclass, field

import numpy as np
import soundfile as sf

from this_voice_thing.core.soundscape import catalog, mastering
from this_voice_thing.engines import worker as engine_worker

MOSS_COMMIT = "934d6826b084c46a0d033402174d5f8ac4ed2519"    # OpenMOSS/MOSS-TTS, 2026-09-06
STITCH_OVERLAP_SECONDS = 2.0


@dataclass(frozen=True)
class ModelSpec:
    key: str                    # catalog key
    directory: str              # engines/<directory>
    worker: str
    python_version: str
    torch_packages: list
    packages: list              # install steps after torch
    load_request: dict
    defaults: dict = field(default_factory=dict)
    env: dict = field(default_factory=dict)


SPECS = {
    "moss_sfx_v2": ModelSpec(
        key="moss_sfx_v2", directory="moss_sfx", worker="moss_worker.py", python_version="3.12",
        torch_packages=["torch==2.9.0", "torchaudio==2.9.0", "torchvision==0.24.0"],
        packages=[["torchcodec==0.8.0",
                   "moss-soundeffect-v2 @ git+https://github.com/OpenMOSS/MOSS-TTS.git"
                   f"@{MOSS_COMMIT}#subdirectory=moss_soundeffect_v2"]],
        load_request={"cmd": "load", "model_id": catalog.MOSS_SFX_V2.repo_id},
        defaults={"steps": 100, "cfg_scale": 4.0},
        env={"TORCHDYNAMO_DISABLE": "1"}),
}


def worker_path(spec):
    return os.path.join(engine_worker.engine_dir(spec.directory), spec.worker)


def is_installed(key):
    spec = SPECS[key]
    return os.path.exists(engine_worker.venv_python(spec.directory)) and os.path.exists(worker_path(spec))


def install(key, log=print):
    spec = SPECS[key]
    engine_worker.install_env(spec.directory, spec.packages, log,
                              python_version=spec.python_version, torch_packages=spec.torch_packages)


def stitch(chunks, sample_rate, overlap_seconds=STITCH_OVERLAP_SECONDS):
    """Join takes end to end with equal-power crossfades of `overlap_seconds`."""
    out = mastering.as_stereo(chunks[0])
    fade = int(overlap_seconds * sample_rate)
    for chunk in chunks[1:]:
        chunk = mastering.as_stereo(chunk)
        n = min(fade, len(out) // 2, len(chunk) // 2)
        ramp = np.linspace(0.0, np.pi / 2, n, dtype=np.float32)[:, None]
        joined = out[-n:] * np.cos(ramp) + chunk[:n] * np.sin(ramp)
        out = np.concatenate([out[:-n], joined, chunk[n:]])
    return out


def plan_chunks(seconds, max_seconds, overlap_seconds=STITCH_OVERLAP_SECONDS):
    """Lengths of the takes needed for `seconds` once overlaps are crossfaded away.
    A hair over the maximum (e.g. loop padding) is one take at the maximum, not two."""
    if seconds <= max_seconds + 0.1:
        return [min(seconds, max_seconds)]
    step = max_seconds - overlap_seconds
    count = int(np.ceil((seconds - overlap_seconds) / step))
    last = seconds - step * (count - 1)
    return [max_seconds] * (count - 1) + [max(last, overlap_seconds * 2)]


def explain_load_error(engine, message):
    """Turn Hugging Face access errors into what the user should do."""
    if "GatedRepoError" in message or "authorized list" in message or "403" in message:
        return (f"{engine.label} is gated on Hugging Face and this account doesn't have access yet. "
                f"Sign in at https://huggingface.co/{engine.repo_id}, accept the terms there, and make "
                "sure your Hugging Face token is saved on the Model page. Then start it again.")
    if "401" in message or "Invalid credentials" in message:
        return (f"Hugging Face rejected the saved token while downloading {engine.label}. "
                "Check the token on the Model page.")
    return message


class SoundModel:
    """A running model worker. generate() returns (float32 stereo array, sample_rate)."""

    def __init__(self, key, log=print):
        if not is_installed(key):
            raise RuntimeError(f"{catalog.ENGINES[key].label} isn't installed yet.")
        self.key = key
        self.spec = SPECS[key]
        self.engine = catalog.ENGINES[key]
        self.worker = engine_worker.WorkerProcess(
            engine_worker.venv_python(self.spec.directory), worker_path(self.spec), self.spec.directory,
            log, skip=lambda line: "warn" in line.lower(), env=self.spec.env)
        try:
            self.device = self.worker.request(**self.spec.load_request).get("device", self.worker.device)
        except Exception as exc:
            self.worker.close()
            raise RuntimeError(explain_load_error(self.engine, str(exc))) from exc
        self._temp = tempfile.mkdtemp(prefix=f"{self.spec.directory}_")
        self.loop_padding_seconds = mastering.LOOP_FOLD_SECONDS
        self._count = 0

    def _out_path(self):
        self._count += 1
        return os.path.join(self._temp, f"take_{self._count}.wav")

    def _take(self, prompt, seconds, seed, **options):
        request = dict(self.spec.defaults, **options)
        reply = self.worker.request(cmd="generate", prompt=prompt, seconds=float(seconds), seed=int(seed),
                                    out_path=self._out_path(), **request)
        audio, sample_rate = sf.read(reply["path"], dtype="float32", always_2d=True)
        return mastering.as_stereo(audio), int(sample_rate)

    def generate(self, prompt, seconds, seed=0, **options):
        lengths = plan_chunks(float(seconds), self.engine.max_seconds)
        takes, sample_rate = [], None
        for index, length in enumerate(lengths):
            audio, sample_rate = self._take(prompt, length, seed + index, **options)
            takes.append(audio)
        audio = stitch(takes, sample_rate) if len(takes) > 1 else takes[0]
        return audio[: int(round(float(seconds) * sample_rate))], sample_rate

    def heal_loop(self, audio, sample_rate, prompt, seed=0):
        """A seamless loop: fold the tail over the head (the take was padded for this)."""
        return mastering.make_loop(audio, sample_rate), sample_rate

    def close(self):
        self.worker.close()
