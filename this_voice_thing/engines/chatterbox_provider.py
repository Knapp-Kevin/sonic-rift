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
import subprocess

import torch
from huggingface_hub import snapshot_download
from huggingface_hub.errors import EntryNotFoundError
from chatterbox.tts import ChatterboxTTS
from chatterbox.mtl_tts import ChatterboxMultilingualTTS


DEFAULT_MODEL_REPO = "ResembleAI/chatterbox"
BACKEND_LEGACY = "legacy"
BACKEND_MULTILINGUAL = "multilingual"
DEFAULT_MULTILINGUAL_T3_MODEL = "v3"

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
_T3_NAMES = {
    "v2": "t3_mtl23ls_v2.safetensors",
    "t3_mtl23ls_v2": "t3_mtl23ls_v2.safetensors",
    "v3": "t3_mtl23ls_v3.safetensors",
    "t3_mtl23ls_v3": "t3_mtl23ls_v3.safetensors",
}

# Non-code model identifiers retained for configuration compatibility.
LEGACY_MODEL_FILES = list(_ENGLISH_ASSETS)
MULTILINGUAL_MODEL_FILES = list(_MULTILINGUAL_ASSETS)
MULTILINGUAL_T3_MODEL_ALIASES = {
    **_T3_NAMES,
    "t3_mtl23ls_v2.safetensors": _T3_NAMES["v2"],
    "t3_mtl23ls_v3.safetensors": _T3_NAMES["v3"],
}



class UnsupportedChatterboxRepoError(RuntimeError):
    """The requested repository does not contain compatible model assets."""


def resolve_multilingual_t3_model(value):
    requested = str(value or DEFAULT_MULTILINGUAL_T3_MODEL).strip()
    key = requested.lower()
    return _T3_NAMES.get(key.removesuffix(".safetensors"), requested)


def _has_parameter(method, name):
    """Avoid forwarding a keyword the installed engine version cannot handle."""
    try:
        return name in inspect.signature(method).parameters
    except (ValueError, TypeError):
        return False


def _fetch_assets(repo_id, names):
    location = snapshot_download(
        repo_id=repo_id, repo_type="model", revision="main",
        allow_patterns=list(names), token=os.getenv("HF_TOKEN"),
    )
    return Path(location)


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
        return getattr(self.instance, "device", "N/A")

    def generate(
        self, text, audio_prompt_path=None, exaggeration=0.5, temperature=0.8,
        cfg_weight=0.5, language_id=None, repetition_penalty=1.2,
        min_p=0.05, top_p=1.0,
    ):
        options = {
            "audio_prompt_path": audio_prompt_path,
            "exaggeration": exaggeration,
            "temperature": temperature,
            "cfg_weight": cfg_weight,
        }
        if self.backend == BACKEND_MULTILINGUAL:
            options.update(
                language_id=language_id or "en",
                repetition_penalty=repetition_penalty,
                min_p=min_p,
                top_p=top_p,
            )
        return self.instance.generate(text, **options)


# Public alias retained for callers of the old adapter's Python contract.
LoadedChatterboxModel = ChatterboxSession


def get_supported_languages_for_backend(backend):
    if backend == BACKEND_MULTILINGUAL:
        return ChatterboxMultilingualTTS.get_supported_languages()
    return {"en": "English"}


def _create_multilingual(repo_id, device, t3_choice):
    requested = resolve_multilingual_t3_model(t3_choice)
    # Official repository path is documented in the public speech-engine API.
    official_factory = getattr(ChatterboxMultilingualTTS, "from_pretrained", None)
    if (repo_id == DEFAULT_MODEL_REPO and callable(official_factory)
            and _has_parameter(official_factory, "t3_model")):
        return official_factory(device=device, t3_model=requested)

    checkpoint_dir = _fetch_assets(repo_id, _MULTILINGUAL_ASSETS)
    local_factory = ChatterboxMultilingualTTS.from_local
    if _has_parameter(local_factory, "t3_model"):
        return local_factory(checkpoint_dir, device, t3_model=requested)
    if requested != _T3_NAMES["v2"]:
        print("Installed multilingual engine does not support explicit T3 selection; "
              "using its built-in default.")
    return local_factory(checkpoint_dir, device)


def load_chatterbox_model(repo_id, backend, device, multilingual_t3_model=None):
    if backend not in (BACKEND_LEGACY, BACKEND_MULTILINGUAL):
        raise ValueError(f"Unknown Chatterbox backend: {backend}")
    try:
        if backend == BACKEND_MULTILINGUAL:
            engine = _create_multilingual(repo_id, device, multilingual_t3_model)
            languages = ChatterboxMultilingualTTS.get_supported_languages()
        else:
            engine = ChatterboxTTS.from_local(
                _fetch_assets(repo_id, _ENGLISH_ASSETS), device
            )
            languages = {"en": "English"}
    except EntryNotFoundError as exc:
        layout = "multilingual" if backend == BACKEND_MULTILINGUAL else "English"
        raise UnsupportedChatterboxRepoError(
            f"Model repository '{repo_id}' does not contain the required {layout} "
            "checkpoint assets; select a compatible repository or model version."
        ) from exc
    return ChatterboxSession(engine, backend, repo_id, languages)


def has_system_nvidia_gpu():
    try:
        result = subprocess.run(
            ("nvidia-smi", "-L"), capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return bool(result.stdout.strip())


def probe_usable_torch_cuda():
    if not torch.cuda.is_available():
        return False, "torch.cuda.is_available() returned False."
    try:
        capability = torch.cuda.get_device_capability(0)
        architecture = f"sm_{capability[0]}{capability[1]}"
        installed = set(torch.cuda.get_arch_list())
        if architecture not in installed:
            return False, (
                f"Installed PyTorch CUDA kernels do not include {architecture}. "
                f"Supported architectures: {sorted(installed)}"
            )
        # Inference requires both matrix operations and recurrent layers, not
        # merely a CUDA device that is visible to torch.
        matrix = torch.randn((8, 8), device="cuda")
        (matrix @ matrix).sum().item()
        recurrent = torch.nn.GRU(4, 4).to("cuda")
        recurrent(torch.randn((2, 1, 4), device="cuda"))
    except Exception as exc:
        return False, str(exc)
    return True, None
