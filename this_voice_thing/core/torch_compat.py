"""Compatibility setup for third-party model loaders using torch.load.

Torch is injected: importing this module never loads PyTorch, tests never need a
GPU, and the rest of the app can eventually replace this process-wide hook
with explicit, scoped model-loading calls.
"""
from functools import wraps


def preferred_load_device(torch_module):
    """CUDA > Apple MPS > CPU, with diagnostics-safe accelerator inspection."""
    def usable(accelerator):
        probe = getattr(accelerator, "is_available", None)
        if not callable(probe):
            return False
        try:
            return bool(probe())
        except Exception:
            return False

    if usable(getattr(torch_module, "cuda", None)):
        return "cuda"
    if usable(getattr(getattr(torch_module, "backends", None), "mps", None)):
        return "mps"
    return "cpu"


def install_default_load_device(torch_module, device):
    """Install at most one wrapper; return the original torch.load callable.

    This deliberately preserves the historical default map_location policy.
    A caller-provided map_location, including None, always wins. Reinstalling
    updates the default instead of nesting wrappers during Qt/dev reloads.
    """
    load = torch_module.load
    if getattr(load, "_sonic_rift_default_load", False):
        load._sonic_rift_load_device = device
        return load.__wrapped__

    @wraps(load)
    def load_with_default_device(*args, **kwargs):
        if "map_location" not in kwargs:
            kwargs["map_location"] = load_with_default_device._sonic_rift_load_device
        return load(*args, **kwargs)

    load_with_default_device._sonic_rift_default_load = True
    load_with_default_device._sonic_rift_load_device = device
    torch_module.load = load_with_default_device
    return load
