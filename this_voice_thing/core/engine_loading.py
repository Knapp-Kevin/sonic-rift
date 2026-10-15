"""Provider-neutral contract for loading a selected audio model.

Keep this module independent of Qt, torch and individual model packages. Runtime
adapters supply factories from their respective installed provider environments.
"""
from dataclasses import dataclass
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class EngineRequest:
    backend: str
    repo_id: str
    device: str
    mode: str = "clone"
    multilingual_t3_model: str = "v3"


@dataclass(frozen=True)
class EngineProvider:
    load: Callable[[EngineRequest], Any]
    available: Callable[[], bool]
    unavailable_message: str


class EngineUnavailableError(RuntimeError):
    """The selected engine's dependencies are not usable."""


class UnsupportedEngineError(ValueError):
    """No runtime adapter is registered for the requested backend."""


def load_engine(request: EngineRequest, providers: Mapping[str, EngineProvider]):
    """Load exactly the requested backend; never silently fall back to another.

    The loaded model's optional `to` method remains part of the existing
    runtime contract. Many out-of-process models already live on their chosen
    device, so they need not implement it.
    """
    provider = providers.get(request.backend)
    if provider is None:
        raise UnsupportedEngineError(
            f"No registered audio engine for backend '{request.backend}'."
        )
    if not provider.available():
        raise EngineUnavailableError(provider.unavailable_message)
    model = provider.load(request)
    if model is None:
        raise RuntimeError(
            f"Audio engine '{request.backend}' returned no model instance."
        )
    move = getattr(model, "to", None)
    if callable(move):
        move(request.device)
    return model
