# ruff: noqa: E402
"""Start-up setup and shared constants for the window modules: console logging,
NLTK, the Chatterbox backend, model config and engine tables."""

import sys
import os
if "PYTHONIOENCODING" not in os.environ:
    os.environ["PYTHONIOENCODING"] = "utf-8"   # child processes print UTF-8 too

# Keep device policy within individual engine loaders. The old import-time
# torch.load monkeypatch altered the entire process, including other providers.
# Windows CPU/CUDA acceptance is required before merging this refactor.
import torchaudio  # noqa: F401  (imported at start-up, as before the split)


# Preserve the historical `common.TeeStream` interface and mutable sink for
# callers while moving generic stream behavior into a UI-independent core.
from this_voice_thing.core.console_io import (
    ForwardingStream,
    configure_console_stream,
    safe_console_text,
)

# The window sets this to a callable taking text; console output is copied to it.
APP_LOG_SINK = None


def _current_log_sink():
    return APP_LOG_SINK


class TeeStream(ForwardingStream):
    """A console stream that also feeds whatever APP_LOG_SINK is at the time of each write."""

    def __init__(self, stream):
        super().__init__(stream, sink_supplier=_current_log_sink)


def _tee_console():
    """UTF-8 console output, mirrored into the window's log once it exists."""
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name)
        configure_console_stream(stream)
        setattr(sys, name, TeeStream(stream))


_tee_console()


# Sentence splitting (documents, subtitles, chunking) needs NLTK's Punkt data.
PUNKT_DATA = (("punkt", "tokenizers/punkt"), ("punkt_tab", "tokenizers/punkt_tab"))


def _install_punkt(nltk_module):
    """Make sure each PUNKT_DATA package is installed, downloading missing ones once.

    Returns False, after printing how to install it by hand, if one can't be made available."""
    for package, data_path in PUNKT_DATA:
        try:
            nltk_module.data.find(data_path)
        except LookupError:
            print(f"NLTK data package '{package}' is missing; downloading it now...")
        except Exception as exc:
            print(f"ERROR: could not check NLTK data package '{package}': {exc}")
            return False
        else:
            print(f"NLTK data package '{package}' is installed.")
            continue
        try:
            nltk_module.download(package, quiet=False)
            nltk_module.data.find(data_path)   # confirm the download is usable
        except Exception as exc:
            print(f"ERROR: NLTK data package '{package}' could not be downloaded: {exc}")
            print(f"  To install it by hand: python -m nltk.downloader {package}")
            return False
        print(f"NLTK data package '{package}' downloaded.")
    return True


try:
    import nltk
except ImportError:
    print("FATAL ERROR: the NLTK library is not installed; text can't be split into sentences.")
    nltk = None
    NLTK_RESOURCES_OK = False
else:
    NLTK_RESOURCES_OK = _install_punkt(nltk)

from this_voice_thing.core import documents
from this_voice_thing.core import model_registry
from this_voice_thing.core import config_io
from this_voice_thing.core.hardware import has_system_nvidia_gpu, probe_usable_torch_cuda
from this_voice_thing.engines import qwen as qwen_engine
from this_voice_thing.engines import kokoro as kokoro_engine
from this_voice_thing.engines import voxcpm as voxcpm_engine
from this_voice_thing.engines import omnivoice as omnivoice_engine
from this_voice_thing.engines import vibevoice as vibevoice_engine

try:
    from this_voice_thing.engines import chatterbox_backend as chatterbox_backends
except ImportError:
    chatterbox_backends = None
    print("WARNING: the chatterbox-tts library is not installed; Chatterbox models can't be loaded.")
CHATTERBOX_AVAILABLE = chatterbox_backends is not None


class _ChatterboxUnavailableRepoError(RuntimeError):
    """Stand-in when chatterbox-tts is missing. Never RuntimeError itself: callers catch this
    to label Chatterbox repository problems, and other engines raise RuntimeError too."""


def _t3_choice_without_chatterbox(choice):
    return f"{choice or DEFAULT_MULTILINGUAL_T3_MODEL}".strip()


# What the window uses from the Chatterbox backend, with stand-ins for when it isn't installed.
_CHATTERBOX_STAND_INS = {
    "DEFAULT_MODEL_REPO": "ResembleAI/chatterbox",
    "BACKEND_LEGACY": "legacy",
    "BACKEND_MULTILINGUAL": "multilingual",
    "DEFAULT_MULTILINGUAL_T3_MODEL": "v3",
    "UnsupportedChatterboxRepoError": _ChatterboxUnavailableRepoError,
    "get_supported_languages_for_backend": lambda _backend: {"en": "English"},
    "load_chatterbox_model": lambda *_args, **_kwargs: None,
    "resolve_multilingual_t3_model": _t3_choice_without_chatterbox,
}


def _from_chatterbox(name):
    return getattr(chatterbox_backends, name, _CHATTERBOX_STAND_INS[name])


DEFAULT_MODEL_REPO = _from_chatterbox("DEFAULT_MODEL_REPO")
BACKEND_LEGACY = _from_chatterbox("BACKEND_LEGACY")
BACKEND_MULTILINGUAL = _from_chatterbox("BACKEND_MULTILINGUAL")
DEFAULT_MULTILINGUAL_T3_MODEL = _from_chatterbox("DEFAULT_MULTILINGUAL_T3_MODEL")
UnsupportedChatterboxRepoError = _from_chatterbox("UnsupportedChatterboxRepoError")
get_supported_languages_for_backend = _from_chatterbox("get_supported_languages_for_backend")
load_chatterbox_model = _from_chatterbox("load_chatterbox_model")
resolve_multilingual_t3_model = _from_chatterbox("resolve_multilingual_t3_model")

MAX_TEXT_INPUT_LENGTH = documents.MAX_SECTION_LENGTH
LOSSLESS_FORMATS = ["WAV", "FLAC"]
QWEN_BACKEND = "qwen3"
KOKORO_BACKEND = "kokoro"
VOXCPM_BACKEND = "voxcpm"
OMNIVOICE_BACKEND = "omnivoice"
VIBEVOICE_BACKEND = "vibevoice"
# Engines that run in their own environment and never need the chatterbox-tts library.
WORKER_BACKENDS = frozenset({QWEN_BACKEND, KOKORO_BACKEND, VOXCPM_BACKEND, OMNIVOICE_BACKEND, VIBEVOICE_BACKEND})


def needs_chatterbox(backend):
    """Only the Chatterbox backends need the chatterbox-tts library in this environment."""
    return backend not in WORKER_BACKENDS
# Engines that run in their own environment (engines/<name>), installed on first use.
ENGINE_MODULES = {QWEN_BACKEND: qwen_engine, KOKORO_BACKEND: kokoro_engine, VOXCPM_BACKEND: voxcpm_engine,
                  OMNIVOICE_BACKEND: omnivoice_engine, VIBEVOICE_BACKEND: vibevoice_engine}
WORKER_MODEL_TYPES = (qwen_engine.QwenModel, kokoro_engine.KokoroModel, voxcpm_engine.VoxCPMModel,
                      omnivoice_engine.OmniVoiceModel, vibevoice_engine.VibeVoiceModel)
# One model that both clones and designs; its entries switch mode without reloading.
DUAL_MODE_BACKENDS = {VOXCPM_BACKEND, OMNIVOICE_BACKEND}
DUAL_MODE_TYPES = (voxcpm_engine.VoxCPMModel, omnivoice_engine.OmniVoiceModel)
ENGINE_INSTALL_NOTES = {
    QWEN_BACKEND: ("Qwen", "Qwen3-TTS runs in its own Python environment (engines/qwen) because it "
                           "needs different library versions than Chatterbox.\n\nInstalling downloads "
                           "about 3 GB of PyTorch and Qwen packages (less if PyTorch is already "
                           "cached). Model weights download the first time each Qwen model is loaded."),
    KOKORO_BACKEND: ("Kokoro", "Kokoro runs in its own Python environment (engines/kokoro) because its "
                               "text processing needs packages Chatterbox doesn't use.\n\nInstalling "
                               "downloads PyTorch (about 3 GB, or nothing if another engine already "
                               "cached it) plus about 300 MB of text-processing packages. The model "
                               "itself is about 340 MB."),
    VOXCPM_BACKEND: ("VoxCPM", "VoxCPM2 runs in its own Python environment (engines/voxcpm) because it "
                               "needs packages Chatterbox doesn't use.\n\nInstalling downloads "
                               "PyTorch (about 3 GB, or nothing if another engine already cached it) "
                               "plus about 1.5 GB of VoxCPM packages. The model itself is about 5 GB, "
                               "shared by the voice cloning and voice design entries."),
    OMNIVOICE_BACKEND: ("OmniVoice", "OmniVoice runs in its own Python environment (engines/omnivoice) "
                                     "because it needs packages Chatterbox doesn't use.\n\nInstalling "
                                     "downloads PyTorch (about 3 GB, or nothing if another engine already "
                                     "cached it) plus OmniVoice's packages. The model itself is about "
                                     "3 GB, shared by the voice cloning and voice design entries.\n\n"
                                     "Note: OmniVoice's weights are licensed CC BY-NC 4.0, for "
                                     "non-commercial use only."),
    VIBEVOICE_BACKEND: ("VibeVoice", "VibeVoice runs in its own Python environment (engines/vibevoice) "
                                     "because it needs a newer transformers than Chatterbox.\n\n"
                                     "Installing downloads PyTorch (about 3 GB, or nothing if another "
                                     "engine already cached it) plus about 1 GB of packages. The 1.5B "
                                     "model is about 5 GB.\n\nNote: VibeVoice is MIT-licensed, but "
                                     "Microsoft's model card limits it to research use and rules out "
                                     "cloning anyone's voice without their recorded consent."),
}


def languages_for_backend(backend):
    if backend == QWEN_BACKEND:
        return dict(qwen_engine.LANGUAGE_LABELS)
    if backend == KOKORO_BACKEND:
        return dict(kokoro_engine.LANGUAGE_LABELS)
    if backend == VOXCPM_BACKEND:
        return dict(voxcpm_engine.LANGUAGE_LABELS)
    if backend == OMNIVOICE_BACKEND:
        return dict(omnivoice_engine.LANGUAGE_LABELS)
    if backend == VIBEVOICE_BACKEND:
        return dict(vibevoice_engine.LANGUAGE_LABELS)
    return get_supported_languages_for_backend(backend)
MODEL_CONFIG_FILENAME = "models.json"
APP_SETTINGS_FILENAME = "app_settings.json"
REFERENCE_RECORDINGS_DIRNAME = "reference_recordings"
RECORDING_SAMPLE_RATE = 48000
MIN_RECORDING_SECONDS = 3
MAX_RECORDING_SECONDS = 30
# Preview lengths offered next to Preview: (label, characters). Speech runs at roughly
# 15 characters a second; a few seconds is enough to judge a voice.
PREVIEW_LENGTHS = (("3 s", 45), ("5 s", 75), ("10 s", 150))
DEFAULT_PREVIEW_CHARS = 75


def preview_cut(lengths, budget):
    """How many leading sections make up a preview of about budget characters (at least one)."""
    if not budget:
        return len(lengths)
    total = 0
    for count, length in enumerate(lengths, 1):
        total += length
        if total >= budget:
            return count
    return len(lengths)
# Batched engines: a batch costs about longest_section_chars * rate * (1 + slope * sections).
# Fitted on an RTX 5070 Ti (Qwen3 1.7B): 16 sections ~78 s, 2 sections ~28 s.
BATCH_COST_SLOPE = 0.07
# Initial generation-speed guesses (seconds per character), refined by measurement.
# Initial speed guesses (seconds of generation per character of text) per engine
# and device; replaced by measurements as each model is used.
DEFAULT_SECONDS_PER_CHAR = {
    ("chatterbox", "cuda"): 0.045, ("chatterbox", "cpu"): 0.35,
    ("qwen3", "cuda"): 0.13, ("qwen3", "cpu"): 2.0,  # Qwen on CUDA: see BATCH_COST_SLOPE
    # Kokoro: ~0.001 s/char warm on an RTX 5070 Ti, plus a little per section.
    ("kokoro", "cuda"): 0.002, ("kokoro", "cpu"): 0.02,
    # VoxCPM2: ~0.06-0.09 s/char on an RTX 5070 Ti (about real time).
    ("voxcpm", "cuda"): 0.07, ("voxcpm", "cpu"): 1.5,
    # OmniVoice batches: ~0.0035 s/char across a batch of 8 on an RTX 5070 Ti.
    ("omnivoice", "cuda"): 0.012, ("omnivoice", "cpu"): 0.5,
    # VibeVoice 1.5B: 0.075-0.11 s/char on an RTX 5070 Ti (slower for longer sections).
    ("vibevoice", "cuda"): 0.1, ("vibevoice", "cpu"): 2.0,
}
SILENT_RECORDING_PEAK = 0.01  # ~ -40 dBFS; quieter usually means a blocked/muted mic
# Read-aloud passages for reference recordings (~15 s each). Each one covers
# every English vowel, diphthong and consonant (including the rarer "zh",
# "th", "ng", "oy" sounds) and mixes a statement, question and exclamation to
# capture inflection. Chatterbox weighs the first 6-10 s most heavily, so the
# densest sentences come first.
REFERENCE_READING_SCRIPTS = [
    "Would you hand me the yellow measuring cup before the soup boils over? "
    "The quick thinker judged each chance, then sighed with real pleasure. "
    "Out by the oyster boats, a young fisherman sang about his long voyage home. "
    "I can't believe it, the whole village showed up early!",

    "Have you ever watched a thunderstorm roll across the open prairie? "
    "Judy's shiny beige jacket hung on a hook behind the kitchen door. "
    "Thousands of noisy geese flew south, honking loudly over the calm bay. "
    "Please, just breathe slowly and think about what you really want!",

    "My brother usually orders the cheese pizza with extra garlic and mushrooms. "
    "Why would anyone leave a shiny new toy out in the pouring rain? "
    "The judge thoughtfully weighed the evidence while the phone kept ringing. "
    "Wow, that's the most beautiful sunset I've seen all year!",
]
DEFAULT_LANGUAGE_TEST_TEXTS = {
    "ar": "أهلاً! هذه جملة قصيرة لسماع الصوت قبل البدء.",
    "da": "Hej! Her er en lille sætning, så du kan høre stemmen, før du går i gang.",
    "de": "Hi! Hier ist ein kleiner Satz, damit du die Stimme hörst, bevor es losgeht.",
    "el": "Γεια! Μια μικρή πρόταση για να ακούσεις τη φωνή πριν ξεκινήσεις.",
    "en": "Hi! Here's a little sentence so you can hear the voice before you start.",
    "es": "¡Hola! Aquí tienes una frase breve para escuchar la voz antes de empezar.",
    "fi": "Hei! Tässä pieni lause, jotta kuulet äänen ennen kuin aloitat.",
    "fr": "Salut ! Voici une petite phrase pour entendre la voix avant de commencer.",
    "he": "היי! הנה משפט קטן כדי לשמוע את הקול לפני שמתחילים.",
    "hi": "नमस्ते! शुरू करने से पहले आवाज़ सुनने के लिए यह एक छोटा सा वाक्य है।",
    "it": "Ciao! Ecco una frase breve per sentire la voce prima di iniziare.",
    "ja": "やあ！始める前に声を聞けるよう、短い一文をどうぞ。",
    "ko": "안녕하세요! 시작하기 전에 목소리를 들어 볼 수 있는 짧은 문장이에요.",
    "ms": "Hai! Ini ayat pendek supaya anda boleh dengar suara itu sebelum bermula.",
    "nl": "Hoi! Hier is een korte zin, zodat je de stem hoort voordat je begint.",
    "no": "Hei! Her er en liten setning, så du kan høre stemmen før du begynner.",
    "pl": "Cześć! Oto krótkie zdanie, żebyś usłyszał głos, zanim zaczniesz.",
    "pt": "Oi! Aqui está uma frase curtinha para você ouvir a voz antes de começar.",
    "ru": "Привет! Вот короткая фраза, чтобы услышать голос перед началом.",
    "sv": "Hej! Här är en kort mening så att du hör rösten innan du börjar.",
    "sw": "Habari! Hii ni sentensi fupi ili usikie sauti kabla ya kuanza.",
    "tr": "Selam! Başlamadan önce sesi duyman için kısa bir cümle.",
    "zh": "你好！先用这句短话听听这个声音，再开始吧。",
}
DEFAULT_MODELS_CONFIG = {
    "models": [
        {
            "repo_id": DEFAULT_MODEL_REPO,
            "label": "Official multilingual",
            "enabled": True,
            "experimental": False,
            "test_text": DEFAULT_LANGUAGE_TEST_TEXTS["en"],
            "test_texts": DEFAULT_LANGUAGE_TEST_TEXTS,
            "notes": "The default: Resemble AI's multilingual model.",
            "backend": BACKEND_MULTILINGUAL,
            "language_id": "en",
            "multilingual_t3_model": DEFAULT_MULTILINGUAL_T3_MODEL,
        },
    ]
}


def read_models_config_payload(path):
    """(decoded models.json, diagnostic). A missing file is reported, unlike app settings."""
    return config_io.read_json(
        path,
        missing_error=f"Model config '{path}' not found.",
        error_label=f"model config '{path}'",
    )


def _clean_test_texts(raw):
    """{language: sample sentence} with lower-case language codes; blank keys/texts dropped."""
    if not isinstance(raw, dict):
        return {}
    cleaned = {}
    for language, sentence in raw.items():
        code, text = str(language).strip().lower(), str(sentence).strip()
        if code and text:
            cleaned[code] = text
    return cleaned


def _model_entry(item):
    """One models.json entry in the shape the window uses, or None if it has no repo_id."""
    def text(key, default=""):
        return str(item.get(key, default)).strip()

    repo_id = text("repo_id")
    if not repo_id:
        return None
    backend = text("backend", BACKEND_MULTILINGUAL) or BACKEND_MULTILINGUAL
    # Only the multilingual backend has T3 model versions.
    is_multilingual = backend == BACKEND_MULTILINGUAL
    t3_model = (resolve_multilingual_t3_model(item.get("multilingual_t3_model", DEFAULT_MULTILINGUAL_T3_MODEL))
                if is_multilingual else "")
    entry = {}
    # Optional fields come first and only when set (the key order is kept from older versions).
    licence = text("license")
    if licence:
        entry["license"] = licence.lower()
    size = item.get("download_bytes")
    if isinstance(size, int) and size > 0:
        entry["download_bytes"] = size
    if backend in DUAL_MODE_BACKENDS:
        entry["mode"] = model_registry.entry_mode(item)
    entry.update(
        repo_id=repo_id,
        label=text("label", repo_id) or repo_id,
        enabled=bool(item.get("enabled", True)),
        # Anything but the default model counts as experimental unless the entry says otherwise.
        experimental=bool(item.get("experimental", repo_id != DEFAULT_MODEL_REPO)),
        test_text=text("test_text"),
        notes=text("notes"),
        backend=backend,
        language_id=text("language_id", "en").lower() or "en",
        multilingual_t3_model=t3_model,
        qwen_variant=text("qwen_variant"),
        test_texts=_clean_test_texts(item.get("test_texts", {})),
    )
    return entry


def _entry_identity(entry, item):
    """Entries that agree on all of these are duplicates; only the first is kept."""
    variant = entry["multilingual_t3_model"] or str(item.get("mode") or item.get("voxcpm_mode") or "")
    return entry["repo_id"], entry["backend"], entry["label"], variant


def _built_in_default_entry():
    """The official multilingual model, which the list always offers."""
    # A copy of the first built-in entry, with its own copy of the sample sentences (last).
    entry = {key: value for key, value in DEFAULT_MODELS_CONFIG["models"][0].items() if key != "test_texts"}
    entry["test_texts"] = dict(DEFAULT_LANGUAGE_TEST_TEXTS)
    return entry


def load_models_config(path):
    """The model list from models.json (built-in defaults if it is missing or unreadable).

    Entries are cleaned up and de-duplicated, and the official multilingual model is always
    first when the file leaves it out. The file itself is never changed."""
    payload, problem = read_models_config_payload(path)
    if problem:
        print(f"{problem} Using built-in defaults.")
        raw_entries = DEFAULT_MODELS_CONFIG["models"]
    elif not isinstance(payload, dict):
        print("Model config has no model list. Using built-in defaults.")
        raw_entries = DEFAULT_MODELS_CONFIG["models"]
    else:
        raw_entries = payload.get("models", [])

    models, seen = [], set()
    for item in raw_entries:
        entry = _model_entry(item) if isinstance(item, dict) else None
        if entry is None:
            continue
        identity = _entry_identity(entry, item)
        if identity not in seen:
            seen.add(identity)
            models.append(entry)

    has_default = any(m["repo_id"] == DEFAULT_MODEL_REPO and m["backend"] == BACKEND_MULTILINGUAL for m in models)
    if not has_default:
        models.insert(0, _built_in_default_entry())
    return models


def read_json_payload(path):
    """(decoded JSON, diagnostic); a missing file is not an error (fresh installs)."""
    return config_io.read_json(path)


def write_json_payload(path, payload):
    config_io.write_json(path, payload)
