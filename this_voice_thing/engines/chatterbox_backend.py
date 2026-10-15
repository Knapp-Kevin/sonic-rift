"""Backwards-compatible import path for the Sonic Rift Chatterbox provider.

The prior implementation originated in AcTePuKc/Chatterbox-TTS-UI. This file
now delegates to Sonic Rift's adapter; its historical MIT notice must remain
recorded while other upstream-derived implementation survives elsewhere.
"""
from this_voice_thing.engines.chatterbox_provider import (  # noqa: F401
    BACKEND_LEGACY,
    BACKEND_MULTILINGUAL,
    DEFAULT_MODEL_REPO,
    DEFAULT_MULTILINGUAL_T3_MODEL,
    LEGACY_MODEL_FILES,
    MULTILINGUAL_MODEL_FILES,
    MULTILINGUAL_T3_MODEL_ALIASES,
    ChatterboxSession,
    LoadedChatterboxModel,
    UnsupportedChatterboxRepoError,
    get_supported_languages_for_backend,
    has_system_nvidia_gpu,
    load_chatterbox_model,
    probe_usable_torch_cuda,
    resolve_multilingual_t3_model,
)
