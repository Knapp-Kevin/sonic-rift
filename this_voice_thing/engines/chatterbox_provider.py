"""Sonic Rift adapter for the official Resemble Chatterbox TTS Python APIs.

This is an application-owned provider boundary; it is not a bundled speech
engine. Both the installed chatterbox-tts package and model weights retain
their own licensing terms. The previous Chatterbox UI implementation is not
called from this module.
"""
from dataclasses import dataclass
import inspect
import os
from pathlib import Path

from huggingface_hub import snapshot_download
from huggingface_hub.errors import EntryNotFoundError, LocalEntryNotFoundError, RepositoryNotFoundError
from chatterbox.tts import ChatterboxTTS
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

# GPU detection is shared by every engine and lives in core.hardware; re-exported here
# for callers of the historical chatterbox_backend import path.
from this_voice_thing.core.hardware import has_system_nvidia_gpu, probe_usable_torch_cuda  # noqa: F401


DEFAULT_MODEL_REPO = "ResembleAI/chatterbox"   # Resemble AI's official checkpoints
BACKEND_LEGACY, BACKEND_MULTILINGUAL = "legacy", "multilingual"   # English-only, 23 languages
DEFAULT_MULTILINGUAL_T3_MODEL = "v3"           # the newest multilingual T3 weights

# These model-repository filenames are API/data-contract identifiers, not
# application source code. Keep custom repository support explicit.
_ENGLISH_ASSETS = (
    "ve.safetensors", "t3_cfg.safetensors", "s3gen.safetensors",
    "tokenizer.json", "conds.pt",
)
_MULTILINGUAL_ASSETS = (
    "ve.pt", "t3_mtl23ls_v2.safetensors", "t3_mtl23ls_v3.safetensors",
    "t3_23lang.safetensors", "s3gen.pt", "s3gen_v3.pt",
    "s3gen_v3.safetensors", "grapheme_mtl_merged_expanded_v1.json",
    "mtl_tokenizer.json", "conds.pt", "Cangjie5_TC.json",
)
# Multilingual T3 weight versions and their checkpoint file names.
_T3_FILES = {version: f"t3_mtl23ls_{version}.safetensors" for version in ("v2", "v3")}

# What the loaders actually read. snapshot_download skips patterns a repository lacks
# without raising, so these are checked after downloading: a repository missing them
# gets a clear error instead of a FileNotFoundError deep inside the speech engine.
_ENGLISH_REQUIRED = ("ve.safetensors", "t3_cfg.safetensors", "s3gen.safetensors", "tokenizer.json")
_MULTILINGUAL_REQUIRED = ("ve.pt", "s3gen.pt", "grapheme_mtl_merged_expanded_v1.json")
_MULTILINGUAL_OPTIONAL = ("conds.pt", "Cangjie5_TC.json")   # built-in voice; Chinese tokenizer

# Non-code model identifiers retained for configuration compatibility.
LEGACY_MODEL_FILES = list(_ENGLISH_ASSETS)
MULTILINGUAL_MODEL_FILES = list(_MULTILINGUAL_ASSETS)
# models.json may name a T3 version as "v3", "t3_mtl23ls_v3" or the full file name.
MULTILINGUAL_T3_MODEL_ALIASES = {alias: file_name for version, file_name in _T3_FILES.items()
                                 for alias in (version, file_name.removesuffix(".safetensors"), file_name)}



class UnsupportedChatterboxRepoError(RuntimeError):
    """The requested repository does not contain compatible model assets."""


def resolve_multilingual_t3_model(value):
    """An alias (v2, v3, t3_mtl23ls_v3, their .safetensors names; any case) to its file name.
    Anything else is returned as given (stripped), so a repository's own file name still works."""
    chosen = DEFAULT_MULTILINGUAL_T3_MODEL if not value else str(value).strip()
    known = MULTILINGUAL_T3_MODEL_ALIASES.get(chosen.lower())
    return known if known else chosen


def _has_parameter(method, name):
    """Avoid forwarding a keyword the installed engine version cannot handle."""
    try:
        return name in inspect.signature(method).parameters
    except (ValueError, TypeError):
        return False


def _fetch_assets(repo_id, names, required=()):
    location = Path(snapshot_download(
        repo_id=repo_id, repo_type="model", revision="main",
        allow_patterns=list(names), token=os.getenv("HF_TOKEN"),
    ))
    missing = [name for name in required if not (location / name).exists()]
    if missing:
        error = UnsupportedChatterboxRepoError(
            f"Model repository '{repo_id}' doesn't have the checkpoint files this loader needs "
            f"(missing: {', '.join(missing)}). Select a compatible repository or model version.")
        error.missing = missing
        raise error
    return location


@dataclass
class ChatterboxSession:
    instance: object
    backend: str
    repo_id: str
    supported_languages: dict

    @property
    def sr(self):
        return self.instance.sr

    @property
    def device(self):
        try:
            return self.instance.device
        except AttributeError:
            return "N/A"

    def generate(
        self, text, audio_prompt_path=None, exaggeration=0.5, temperature=0.8,
        cfg_weight=0.5, language_id=None, repetition_penalty=1.2,
        min_p=0.05, top_p=1.0,
    ):
        """Speak one section. Only the multilingual engine takes a language and the extra
        sampling options; the English engine would reject them."""
        voice = {"audio_prompt_path": audio_prompt_path, "exaggeration": exaggeration,
                 "temperature": temperature, "cfg_weight": cfg_weight}
        extras = {"language_id": language_id or "en", "repetition_penalty": repetition_penalty,
                  "min_p": min_p, "top_p": top_p}
        multilingual = self.backend == BACKEND_MULTILINGUAL
        return self.instance.generate(text, **voice, **(extras if multilingual else {}))


# Public alias retained for callers of the old adapter's Python contract.
LoadedChatterboxModel = ChatterboxSession


# Where each backend's language list comes from; the English-only model has just English.
_LANGUAGE_LISTS = {
    BACKEND_LEGACY: lambda: {"en": "English"},
    BACKEND_MULTILINGUAL: lambda: ChatterboxMultilingualTTS.get_supported_languages(),
}


def get_supported_languages_for_backend(backend):
    """Language id -> name for a Chatterbox backend (an unknown one counts as English-only)."""
    listing = _LANGUAGE_LISTS.get(backend, _LANGUAGE_LISTS[BACKEND_LEGACY])
    return listing()


def _create_multilingual(repo_id, device, t3_choice):
    requested = resolve_multilingual_t3_model(t3_choice)
    # Official repository path is documented in the public speech-engine API.
    official_factory = getattr(ChatterboxMultilingualTTS, "from_pretrained", None)
    if (repo_id == DEFAULT_MODEL_REPO and callable(official_factory)
            and _has_parameter(official_factory, "t3_model")):
        print(f"Loading the official multilingual model with from_pretrained (t3_model='{requested}').")
        return official_factory(device=device, t3_model=requested)

    local_factory = ChatterboxMultilingualTTS.from_local
    if _has_parameter(local_factory, "t3_model"):
        # Only what from_local reads: other T3 variants and s3gen formats can add ~6 GB.
        checkpoint_dir = _fetch_assets(
            repo_id, (*_MULTILINGUAL_REQUIRED, requested, *_MULTILINGUAL_OPTIONAL),
            required=(*_MULTILINGUAL_REQUIRED, requested))
        print(f"Loading multilingual checkpoint from '{repo_id}' with from_local (t3_model='{requested}').")
        return local_factory(checkpoint_dir, device, t3_model=requested)
    # Older chatterbox-tts (no t3_model): keep the full historical download set, and require only
    # the files every version reads, so a working older setup isn't refused.
    checkpoint_dir = _fetch_assets(repo_id, _MULTILINGUAL_ASSETS, required=("ve.pt", "s3gen.pt"))
    if requested != _T3_FILES["v2"]:
        print("Installed multilingual engine does not support explicit T3 selection; "
              "using its built-in default.")
    return local_factory(checkpoint_dir, device)


def load_chatterbox_model(repo_id, backend, device, multilingual_t3_model=None):
    if backend not in _LANGUAGE_LISTS:
        raise ValueError(f"Unknown Chatterbox backend: {backend}")
    multilingual = backend == BACKEND_MULTILINGUAL
    try:
        if multilingual:
            engine = _create_multilingual(repo_id, device, multilingual_t3_model)
        else:
            checkpoint = _fetch_assets(repo_id, _ENGLISH_ASSETS, required=_ENGLISH_REQUIRED)
            engine = ChatterboxTTS.from_local(checkpoint, device)
    except UnsupportedChatterboxRepoError as exc:
        missing = getattr(exc, "missing", [])
        only_v3_absent = missing == [_T3_FILES["v3"]]
        if (multilingual and only_v3_absent
                and resolve_multilingual_t3_model(multilingual_t3_model) == _T3_FILES["v3"]):
            # Only the v3 weights are absent: likely an older repository that publishes v2.
            hinted = UnsupportedChatterboxRepoError(
                f"{exc} If this is an older repository, set its multilingual_t3_model to v2 "
                "in models.json.")
            hinted.missing = missing
            raise hinted from exc
        raise
    except (EntryNotFoundError, RepositoryNotFoundError) as exc:   # Local... is an EntryNotFoundError
        raise _download_problem(exc, repo_id, multilingual) from exc
    return ChatterboxSession(engine, backend, repo_id, get_supported_languages_for_backend(backend))


def _download_problem(exc, repo_id, multilingual):
    """A Hugging Face download error as a message the Models page can show."""
    if isinstance(exc, LocalEntryNotFoundError):   # offline, or unreachable, with no full cache
        message = (f"Couldn't download '{repo_id}': Hugging Face is unreachable or offline mode is on, "
                   "and the model isn't fully cached on this PC. Connect to the internet once to download it.")
    elif isinstance(exc, RepositoryNotFoundError):   # also covers gated repositories
        message = (f"Model repository '{repo_id}' wasn't found on Hugging Face, or it is private or "
                   "gated. Check the name; for a gated repository accept its terms on huggingface.co "
                   "and add a token on the Models page.")
    else:
        layout = "multilingual" if multilingual else "English"
        message = (f"Model repository '{repo_id}' doesn't have the {layout} checkpoint files this "
                   "loader needs. Select a compatible repository or model version.")
    return UnsupportedChatterboxRepoError(message)
