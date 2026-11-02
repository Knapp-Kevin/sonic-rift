"""Background threads: model loading, generation, engine installs, speech and transcription."""

import contextlib
import datetime
import os
import random
import sys
import threading
import time
import traceback

import numpy as np
import torch
from PySide6.QtCore import QThread, Signal

from this_voice_thing.core import audio_effects, documents, subtitles
from this_voice_thing.core.engine_loading import (
    EngineProvider, EngineRequest, EngineUnavailableError, UnsupportedEngineError,
    load_engine,
)
from this_voice_thing.engines import (
    kokoro as kokoro_engine,
    omnivoice as omnivoice_engine,
    qwen as qwen_engine,
    vibevoice as vibevoice_engine,
    voxcpm as voxcpm_engine,
)
from this_voice_thing.ui.common import (
    BACKEND_LEGACY, BACKEND_MULTILINGUAL, CHATTERBOX_AVAILABLE,
    DEFAULT_MODEL_REPO, DEFAULT_MULTILINGUAL_T3_MODEL, DEFAULT_PREVIEW_CHARS,
    KOKORO_BACKEND, OMNIVOICE_BACKEND, QWEN_BACKEND, VIBEVOICE_BACKEND, VOXCPM_BACKEND,
    load_chatterbox_model, MAX_TEXT_INPUT_LENGTH, nltk, NLTK_RESOURCES_OK,
    preview_cut, probe_usable_torch_cuda, safe_console_text, UnsupportedChatterboxRepoError,
)

RANDOM_TAKE_LIMIT = 1_000_000   # take number 0 draws a fresh one from 1..this


def pick_device():
    """(device, why CUDA was refused): the GPU only when this PyTorch build can really use it."""
    problem = None
    if torch.cuda.is_available():
        usable, problem = probe_usable_torch_cuda()
        if usable:
            return "cuda", None
    return "cpu", problem


def seed_everything(seed):
    """Seed Python's, NumPy's and PyTorch's generators, so one take number gives one take.
    torch.manual_seed seeds every GPU as well."""
    for seeder in (random.seed, np.random.seed, torch.manual_seed):
        seeder(seed)


def _always():
    """Worker engines are installed on demand by the Models page; loading reports problems."""
    return True


def _engine_providers():
    """Backend -> how to load it, whether it can load here, and what to say if not."""
    chatterbox = EngineProvider(
        load=lambda req: load_chatterbox_model(req.repo_id, req.backend, req.device,
                                               multilingual_t3_model=req.multilingual_t3_model),
        available=lambda: CHATTERBOX_AVAILABLE,
        unavailable_message=("The Chatterbox engine isn't available (the chatterbox-tts "
                             "library failed to import). Other engines still work."),
    )
    workers = {
        QWEN_BACKEND: (lambda req: qwen_engine.load_qwen_model(req.repo_id, log=print), qwen_engine.is_installed,
                       "The Qwen engine isn't installed. Use Load this model on the Models page to install it."),
        KOKORO_BACKEND: (lambda req: kokoro_engine.load_kokoro_model(req.repo_id, log=print), _always,
                         "Kokoro is unavailable."),
        VOXCPM_BACKEND: (lambda req: voxcpm_engine.load_voxcpm_model(req.repo_id, req.mode, log=print), _always,
                         "VoxCPM is unavailable."),
        OMNIVOICE_BACKEND: (lambda req: omnivoice_engine.load_omnivoice_model(req.repo_id, req.mode, log=print),
                            _always, "OmniVoice is unavailable."),
        VIBEVOICE_BACKEND: (lambda req: vibevoice_engine.load_vibevoice_model(req.repo_id, log=print), _always,
                            "VibeVoice is unavailable."),
    }
    providers = {backend: EngineProvider(load=load, available=available, unavailable_message=message)
                 for backend, (load, available, message) in workers.items()}
    providers[BACKEND_LEGACY] = providers[BACKEND_MULTILINGUAL] = chatterbox
    return providers


class ModelLoaderThread(QThread):
    """Loads one model entry off the UI thread."""

    model_loaded = Signal(object, str)   # model, device it runs on
    error_occurred = Signal(str)         # what to tell the user

    def __init__(self, repo_id=DEFAULT_MODEL_REPO, backend=BACKEND_MULTILINGUAL,
                 multilingual_t3_model=DEFAULT_MULTILINGUAL_T3_MODEL):
        super().__init__()
        self.device, self.cuda_probe_error = pick_device()
        self.repo_id, self.backend, self.multilingual_t3_model = (
            repo_id, backend, multilingual_t3_model)
        self.mode = "clone"   # the app sets the entry's mode before start()

    def run(self):
        if self.cuda_probe_error:
            print(f"CUDA is present but this PyTorch build can't use it; loading on the CPU. "
                  f"({self.cuda_probe_error})")
        print(f"Loading '{self.repo_id}' with the {self.backend} engine on {self.device}...")
        # Engine selection, the availability gate and result checks live in the
        # Qt-independent core; this thread only reports the outcome.
        request = EngineRequest(backend=self.backend, repo_id=self.repo_id, device=self.device,
                                mode=self.mode, multilingual_t3_model=self.multilingual_t3_model)
        try:
            model = load_engine(request, _engine_providers())
        except (EngineUnavailableError, UnsupportedEngineError, UnsupportedChatterboxRepoError) as exc:
            print(f"Can't load '{self.repo_id}': {exc}")
            self.error_occurred.emit(str(exc))
            return
        except Exception as exc:
            print(f"Loading '{self.repo_id}' failed:\n{traceback.format_exc()}")
            self.error_occurred.emit(f"Couldn't load '{self.repo_id}': {exc}\n"
                                     "The log (Settings) has the details.")
            return
        print(f"'{self.repo_id}' is loaded (model device: {getattr(model, 'device', 'unknown')}).")
        self.model_loaded.emit(model, self.device)


class _ThreadQuiet:
    """A stream that drops what one thread writes and passes everything else through."""

    def __init__(self, stream, thread_id):
        self._stream, self._thread_id = stream, thread_id

    def write(self, text):
        if threading.get_ident() == self._thread_id:
            return len(text)
        return self._stream.write(text)

    def __getattr__(self, name):
        return getattr(self._stream, name)


@contextlib.contextmanager
def quiet_this_thread():
    """Hide a model's console chatter while it generates, without swallowing what other
    threads print meanwhile (contextlib.redirect_stdout is process-wide, so it hid the UI's
    "Stop requested" message during long batches)."""
    saved = sys.stdout, sys.stderr
    sys.stdout = _ThreadQuiet(saved[0], threading.get_ident())
    sys.stderr = _ThreadQuiet(saved[1], threading.get_ident())
    try:
        yield
    finally:
        sys.stdout, sys.stderr = saved


class _StopRender(Exception):
    """Stop was pressed and nothing worth saving was finished yet."""


class AudioGeneratorThread(QThread):
    """Renders a text section by section and saves one take (or a preview)."""

    generation_complete = Signal(str, int)   # saved file, sample rate
    error_occurred = Signal(str)             # why no take was saved
    chunk_generated = Signal(int, int, int)  # first, last, total
    section_timed = Signal(int, int, float)  # characters (longest in a batch), sections, seconds

    def __init__(self, model, text, audio_prompt_path, exaggeration, temperature, cfg_weight, seed,
                 output_dir, language_id="en", repetition_penalty=1.2, min_p=0.05, top_p=1.0,
                 finishing=None, output_name=None, preview=False):
        super().__init__()
        self.model, self.original_text = model, text
        self.audio_prompt_path = audio_prompt_path or None
        # Passed to the engine's generate() for every section.
        self.sampling = {
            "exaggeration": exaggeration, "temperature": temperature, "cfg_weight": cfg_weight,
            "language_id": language_id, "repetition_penalty": repetition_penalty,
            "min_p": min_p, "top_p": top_p,
        }
        self.input_seed = self.actual_seed_used = seed
        self.output_dir, self.output_name, self.preview = output_dir, output_name, preview
        self.finishing = finishing or audio_effects.FinishingSettings()
        self.preview_chars = DEFAULT_PREVIEW_CHARS  # set by the app; None previews all the text
        self.pronunciations = None                  # set by the app; respells what is spoken
        self.partial_info = None                    # (sections saved, total) after a Stop
        self.subtitle_path = None
        self._stop_event = threading.Event()
        os.makedirs(output_dir, exist_ok=True)

    def stop(self):
        """Finish after the sections in progress (called from the UI thread)."""
        self.stop_requested_at = time.monotonic()
        self._stop_event.set()
        print("Stop requested: the render ends after the sections in progress.")

    def _use_seed(self, seed):
        seed_everything(seed)
        self.actual_seed_used = seed
        print(f"Take number (seed): {seed}")

    def _cannot_start(self):
        if not (nltk and NLTK_RESOURCES_OK):
            return "The sentence splitter (NLTK and its punkt data) is missing. Run the installer again."
        if self.model is None:
            return "No speech model is loaded."
        if self._stop_event.is_set():
            return "Generation stopped by user before it started."
        return None

    def _sections(self):
        """(written texts, texts to speak, paragraph boundaries) for this render."""
        max_chars = getattr(self.model, "max_section_chars", MAX_TEXT_INPUT_LENGTH)
        planner = getattr(self.model, "plan_sections", None)
        planned = planner(self.original_text) if planner else documents.plan_sections(self.original_text, max_chars)
        if self.preview:
            planned = planned[:preview_cut([len(section.text) for section in planned], self.preview_chars)]
        written = [section.text for section in planned]
        # The model is given the text with the pronunciation dictionary applied; subtitles
        # keep the written text.
        spoken = written
        if self.pronunciations is not None:
            respelled = [self.pronunciations.apply_section(text) for text in written]
            spoken = [text for text, _count in respelled]
            words = sum(count for _text, count in respelled)
            if words:
                print(f"Pronunciation dictionary: respelled {words} word(s).")
        print(f"{len(planned)} section(s) of up to {max_chars} characters, never across paragraphs.")
        return written, spoken, [section.boundary for section in planned]

    def _speak(self, spoken):
        """One waveform (1-D numpy) per section. Stop keeps the finished sections of a full
        render; with nothing finished, or in a preview, it raises _StopRender."""
        total = len(spoken)
        options = dict(self.sampling, audio_prompt_path=self.audio_prompt_path)
        # Engines that support it (Qwen) generate several sections per call.
        per_call = max(1, int(getattr(self.model, "batch_size", 1)))
        batches = documents.plan_batches([len(text) for text in spoken], per_call,
                                         getattr(self.model, "batch_char_budget", None))
        waves = []
        for start, end in batches:
            if self._stop_event.is_set():
                if waves and not self.preview:
                    self.partial_info = (start, total)
                    print(f"Stopped: keeping the {start} finished section(s); "
                          f"{total - start} of {total} were skipped.")
                    break
                raise _StopRender(f"Generation stopped by user before section {start + 1} of {total}.")
            batch = spoken[start:end]
            last = start + len(batch)
            self.chunk_generated.emit(start + 1, last, total)
            label = f"{start + 1}" if last == start + 1 else f"{start + 1}-{last}"
            print(f"\nSection {label} of {total} (take {self.actual_seed_used}).")
            began = time.monotonic()
            with quiet_this_thread():
                if len(batch) == 1:
                    outputs = [self.model.generate(batch[0], **options)]
                else:
                    outputs = self.model.generate_batch(batch, **options)
            waves.extend(wave.cpu().reshape(-1).float().numpy() for wave in outputs)
            # A batch takes as long as its longest section, so time is measured against that.
            self.section_timed.emit(max(map(len, batch)), len(batch), time.monotonic() - began)
        return waves

    def _output_base(self):
        """File path without extension: previews go to previews/, takes to the output folder."""
        stamp = f"{datetime.datetime.now():%Y%m%d_%H%M%S}"
        if self.preview:
            folder = os.path.join(self.output_dir, "previews")
            os.makedirs(folder, exist_ok=True)
            return os.path.join(folder, f"preview_{stamp}_seed{self.actual_seed_used}")
        # Kept as "chatterbox" for now so scripts that look for chatterbox_*.wav keep
        # working; renaming it (and chatterbox_outputs/) is a future migration.
        prefix = self.output_name or "chatterbox"
        if self.partial_info:
            suffix = "_partial"
        else:
            suffix = "" if self.output_name else "_full_stitched"
        return os.path.join(self.output_dir, f"{prefix}_{stamp}_seed{self.actual_seed_used}{suffix}")

    def _save(self, waves, written, boundaries):
        """Join, finish and save the sections; (path, sample rate)."""
        rate = self.model.sr
        settings = self.finishing
        spans, timing = [], {}
        joined = audio_effects.join_sections(waves, rate, boundaries[:len(waves)],
                                             settings.paragraph_pause, spans)
        print(f"Finishing: {settings.summary()}")
        finished = audio_effects.apply_finishing(joined, rate, settings, timing=timing)
        base = self._output_base()
        path = audio_effects.save_audio(base, finished, rate, settings.output_format)
        print(f"Saved the take: {path}")
        if settings.save_subtitles and not self.preview:
            try:  # captions never cost the audio
                cues = subtitles.build_cues(written[:len(waves)], spans, joined, rate,
                                            timing.get("scale", 1.0), timing.get("offset", 0.0),
                                            len(finished) / rate)
                self.subtitle_path = subtitles.save(base, cues, settings.subtitle_format)
                print(f"Captions: {self.subtitle_path} ({len(cues)} cues)")
            except Exception as exc:
                print(f"Could not write subtitles: {safe_console_text(exc)}")
        return path, rate

    def run(self):
        try:
            refusal = self._cannot_start()
            if refusal:
                self.error_occurred.emit(refusal)
                return
            self._use_seed(self.input_seed or random.randint(1, RANDOM_TAKE_LIMIT))
            written, spoken, boundaries = self._sections()
            if not written:
                self.error_occurred.emit("There's no text to generate.")
                return
            waves = self._speak(spoken)
            if not waves:
                self.error_occurred.emit("The model produced no audio.")
                return
            path, rate = self._save(waves, written, boundaries)
        except _StopRender as stopped:
            self.error_occurred.emit(str(stopped))
            return
        except Exception as exc:
            if self._stop_event.is_set():
                return  # an error while stopping is not worth a dialog
            print(f"Generation failed: {safe_console_text(exc)}\n{safe_console_text(traceback.format_exc())}")
            self.error_occurred.emit(f"Error while generating: {exc}")
            return
        self.generation_complete.emit(path, rate)


class TaskThread(QThread):
    """Runs one function off the UI thread and reports (result, error message)."""

    done = Signal(object, str)

    def __init__(self, function, parent=None):
        super().__init__(parent)
        self.function = function

    def run(self):
        try:
            self.done.emit(self.function(), "")
        except Exception as exc:
            self.done.emit(None, str(exc))


class TranscribeThread(QThread):
    """Runs Whisper off the UI thread."""

    done = Signal(object, str)  # Transcript or None, error

    def __init__(self, transcriber, source, language, task, parent=None):
        super().__init__(parent)
        self.transcriber, self.source, self.language, self.task = transcriber, source, language, task

    def run(self):
        try:
            self.done.emit(self.transcriber.transcribe(self.source, self.language, self.task), "")
        except Exception as exc:
            self.done.emit(None, f"{type(exc).__name__}: {exc}")


class SpeakThread(QThread):
    """Speak a short text with the loaded model (for trying respellings)."""

    finished_with = Signal(object, int, str)  # waveform, sample rate, error

    def __init__(self, model, text, kwargs, parent=None):
        super().__init__(parent)
        self.model, self.text, self.kwargs = model, text, kwargs

    def run(self):
        try:
            try:
                wav = self.model.generate(self.text, **self.kwargs)
            except TypeError:
                wav = self.model.generate(self.text)  # older loaders take fewer options
            data = wav.squeeze(0).detach().cpu().numpy() if hasattr(wav, "detach") else np.asarray(wav)
            self.finished_with.emit(np.asarray(data, dtype=np.float32).reshape(-1), int(self.model.sr), "")
        except Exception as exc:
            self.finished_with.emit(None, 0, str(exc))


class MakeClipThread(QThread):
    """Generates a reference clip with the current voice: a phonetically rich passage, so
    the clip comes with an exact transcript."""

    finished_with = Signal(object, int, str)  # waveform (numpy) or None, sample rate, error

    def __init__(self, model, text, language_id, parent=None):
        super().__init__(parent)
        self.model, self.text, self.language_id = model, text, language_id

    def run(self):
        try:
            wav = self.model.generate(self.text, language_id=self.language_id)
            data = wav.squeeze(0).detach().cpu().numpy() if hasattr(wav, "detach") else np.asarray(wav)
            self.finished_with.emit(np.asarray(data, dtype=np.float32).reshape(-1), int(self.model.sr), "")
        except Exception as exc:
            self.finished_with.emit(None, 0, str(exc))


class EngineInstallThread(QThread):
    finished_with = Signal(str)

    def __init__(self, engine_module, parent=None):
        super().__init__(parent)
        self.engine_module = engine_module

    def run(self):
        try:
            self.engine_module.install(log=print)
            self.finished_with.emit("")
        except Exception as exc:
            self.finished_with.emit(str(exc))


class SoundRenderThread(QThread):
    """Renders Soundscape candidates off the UI thread; Stop takes effect between takes."""

    progressed = Signal(int, int)
    done = Signal(object, str)      # [Candidate] or None, error

    def __init__(self, request, model, parent=None):
        super().__init__(parent)
        self.request, self.model = request, model
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        from this_voice_thing.core.soundscape import render
        try:
            results = render.render(self.request, self.model, cancelled=self._stop.is_set,
                                    progress=lambda done, total: self.progressed.emit(done, total))
            self.done.emit(results, "")
        except Exception as exc:
            traceback.print_exc()
            self.done.emit(None, f"{type(exc).__name__}: {exc}")
