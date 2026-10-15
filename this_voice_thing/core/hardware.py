"""Independent runtime hardware probes shared by all Sonic Rift engines.

An optional provider import must never determine whether the host exposes
NVIDIA hardware or whether the installed PyTorch build can use CUDA.
Importing this module does not import any TTS SDK or perform a GPU probe.
"""
import subprocess


def has_system_nvidia_gpu():
    """Detect an NVIDIA device without assuming the CUDA toolkit is usable."""
    try:
        completed = subprocess.run(
            ["nvidia-smi", "-L"], capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return bool(completed.stdout.strip())


def probe_usable_torch_cuda(torch_module=None):
    """Validate visible CUDA, compiled architecture, tensor operations and RNN.

    The optional parameter permits deterministic offline testing; production
    callers use the installed torch module. Return (usable, diagnostic).
    """
    if torch_module is None:
        import torch as torch_module

    cuda = torch_module.cuda
    if not cuda.is_available():
        return False, "torch.cuda.is_available() returned False."

    try:
        major, minor = cuda.get_device_capability(0)
        architecture = f"sm_{major}{minor}"
        built_architectures = set(cuda.get_arch_list())
        if architecture not in built_architectures:
            return False, (
                f"Installed PyTorch CUDA kernels do not include {architecture}. "
                f"Supported architectures: {sorted(built_architectures)}"
            )

        sample = torch_module.randn((8, 8), device="cuda")
        (sample @ sample).sum().item()

        rnn = torch_module.nn.GRU(4, 4).to("cuda")
        rnn(torch_module.randn((2, 1, 4), device="cuda"))
    except Exception as exc:
        return False, str(exc)
    return True, None
