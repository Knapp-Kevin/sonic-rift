"""The application-owned Music service: run a validated request, keep a chosen take.

The one place Music generation happens. The Music page calls it from a worker thread,
and a future agent adapter (#130) is meant to call the same entry points under the app's
model locks and approval. It never takes file paths from the caller: takes are written
to a working folder it owns, and kept takes go into the Sound library.
"""

import os
import shutil
import tempfile
import time

import numpy as np
import soundfile as sf

from this_voice_thing.core.music import catalog, contract
from this_voice_thing.core.soundscape import mastering

MUSIC_LUFS = -16.0              # a finished music master; Studio's gain and ducking set the mix
DURATION_TOLERANCE = 0.1        # a take may be up to 10% shorter or longer than asked
SILENCE_LUFS = -60.0


class MusicCancelled(Exception):
    pass


def validate_audio(audio, sample_rate, seconds):
    """Problems with a decoded take (empty list when it's usable)."""
    problems = []
    if audio.size == 0:
        return ["The engine returned no audio."]
    if not np.all(np.isfinite(audio)):
        problems.append("The take contains invalid samples.")
    length = len(audio) / float(sample_rate)
    if abs(length - seconds) > max(1.0, DURATION_TOLERANCE * seconds):
        problems.append(f"The take is {length:.1f} s long; {seconds:.0f} s was asked for.")
    elif not np.isfinite(mastering.integrated_lufs(audio, sample_rate)) or \
            mastering.integrated_lufs(audio, sample_rate) < SILENCE_LUFS:
        problems.append("The take is silent.")
    return problems


class MusicService:
    """Generates takes with a running MusicModel; owns their working folder."""

    def __init__(self, model, work_dir=None):
        """Takes go to `work_dir` (the caller's to clean up), or a private folder close() removes."""
        self.model = model
        self.engine = catalog.ENGINES[model.key]
        self._owns_work_dir = work_dir is None
        self.work_dir = work_dir or tempfile.mkdtemp(prefix="sonic_rift_music_")
        self._count = 0

    def plan(self, request):
        """The request as it will run: checked, with a recorded seed."""
        if request.seed is None:
            request.seed = int(time.time() * 1000) % contract.MAX_SEED
        contract.check(request, self.engine.capabilities)
        return request

    def generate(self, request, cancelled=lambda: False, progress=lambda _done, _total: None):
        """A MusicResult with one validated, mastered take per candidate (fewer if cancelled)."""
        request = self.plan(request)
        result = contract.MusicResult(
            request=request, engine=self.engine.key, model=self.engine.repo_id,
            model_revision=self.engine.model_revision, source_revision=self.engine.source_revision,
            license=self.engine.license_name, device=getattr(self.model, "device", ""))
        started = time.monotonic()
        seeds = request.seeds()
        for index, seed in enumerate(seeds):
            if cancelled():
                result.cancelled = True
                break
            progress(index, len(seeds))
            take = self._take(request, seed, cancelled)
            if take is None:            # cancelled mid-take
                result.cancelled = True
                break
            result.takes.append(take)
            result.peak_vram_mb = max(result.peak_vram_mb, take.engine_notes.pop("peak_mb", 0))
        progress(len(result.takes), len(seeds))
        result.elapsed_seconds = round(time.monotonic() - started, 2)
        return result

    def _take(self, request, seed, cancelled):
        self._count += 1
        os.makedirs(self.work_dir, exist_ok=True)
        raw = os.path.join(self.work_dir, f"raw_{self._count}.wav")
        final = os.path.join(self.work_dir, f"take_{self._count}_seed{seed}.wav")
        try:
            reply = self.model.generate_take(
                raw, request.caption(), request.seconds, seed, lyrics=request.lyrics,
                instrumental=request.instrumental, bpm=request.bpm, key=request.key,
                time_signature=request.time_signature)
            audio, sample_rate = sf.read(raw, dtype="float32", always_2d=True)
            problems = validate_audio(audio, sample_rate, float(request.seconds))
            if problems:
                raise RuntimeError(" ".join(problems))
            audio = mastering.normalize(audio, sample_rate, MUSIC_LUFS)
            mastering.write_audio(final, audio, sample_rate, "wav")
        except Exception:
            self._discard(raw, final)
            if cancelled():
                return None
            raise
        self._discard(raw)
        notes = dict(reply.get("chosen") or {})
        notes["peak_mb"] = int((reply.get("memory") or {}).get("peak_mb", 0))
        return contract.MusicTake(
            path=final, seed=seed, seconds=round(len(audio) / sample_rate, 3), sample_rate=int(sample_rate),
            channels=int(audio.shape[1]), elapsed_seconds=float(reply.get("elapsed", 0.0)),
            metrics=mastering.measure(audio, sample_rate, False), engine_notes=notes)

    @staticmethod
    def _discard(*paths):
        for path in paths:
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

    def discard_takes(self, result):
        """Remove a result's take files (kept takes are copies in the library)."""
        self._discard(*(take.path for take in result.takes))

    def close(self):
        if self._owns_work_dir:
            shutil.rmtree(self.work_dir, ignore_errors=True)


def keep(library, result, take, name):
    """Store `take` from `result` in the Sound library as a music asset with full provenance."""
    if not os.path.isfile(take.path):
        raise RuntimeError("That take's audio is gone; generate it again.")
    audio, sample_rate = sf.read(take.path, dtype="float32", always_2d=True)
    request = result.request
    settings = {"seconds": request.seconds, "instrumental": request.instrumental, "genre": request.genre,
                "mood": request.mood, "instrumentation": request.instrumentation, "bpm": request.bpm,
                "key": request.key, "time_signature": request.time_signature, "target_lufs": MUSIC_LUFS,
                "model_revision": result.model_revision, "source_revision": result.source_revision,
                "contract_version": result.contract_version, "engine_chose": take.engine_notes,
                "device": result.device}
    if request.lyrics:
        settings["lyrics"] = request.lyrics
    return library.add(audio, sample_rate, name, result.engine, False, kind="music", model=result.model,
                       license=result.license, prompt=request.prompt, seed=take.seed, settings=settings,
                       metrics=take.metrics)
