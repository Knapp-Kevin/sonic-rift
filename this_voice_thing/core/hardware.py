"""Independent runtime hardware probes shared by all Sonic Rift engines.

An optional provider import must never determine whether the host exposes
NVIDIA hardware or whether the installed PyTorch build can use CUDA.
Importing this module does not import any TTS SDK or perform a GPU probe.
"""
import contextlib
import subprocess

CUDA_NOT_AVAILABLE = "torch.cuda.is_available() returned False."
NVIDIA_SMI_LIST = ["nvidia-smi", "-L"]   # prints one line per NVIDIA GPU


def _nvidia_smi_devices():
    """The GPU lines nvidia-smi lists, or [] when the tool is missing or fails."""
    output = ""
    with contextlib.suppress(OSError, subprocess.CalledProcessError):   # no NVIDIA driver, or it failed
        output = subprocess.run(NVIDIA_SMI_LIST, check=True, capture_output=True, text=True).stdout or ""
    return [line for line in output.splitlines() if line.strip()]


def has_system_nvidia_gpu():
    """Detect an NVIDIA device without assuming the CUDA toolkit is usable."""
    return len(_nvidia_smi_devices()) > 0


def _missing_kernel_problem(cuda):
    """Why GPU 0 can't run this PyTorch build's kernels, or None when its sm_XY is included."""
    needed = "sm_{}{}".format(*cuda.get_device_capability(0))
    compiled = set(cuda.get_arch_list())
    if needed in compiled:
        return None
    return (f"Installed PyTorch CUDA kernels do not include {needed}. "
            f"Supported architectures: {sorted(compiled)}")


def _gpu_smoke_test(torch_module):
    """Run a matrix multiply and a small GRU on the GPU; raises if CUDA kernels fail.
    (Some builds list an architecture yet fail at the first real kernel; RNNs use cuDNN.)"""
    square = torch_module.randn((16, 16), device="cuda")
    float((square @ square).sum().item())   # .item() waits for the GPU, so errors surface here
    gru = torch_module.nn.GRU(8, 8).to("cuda")
    gru(torch_module.randn((3, 1, 8), device="cuda"))


def probe_usable_torch_cuda(torch_module=None):
    """Validate visible CUDA, compiled architecture, tensor operations and RNN.

    The optional parameter permits deterministic offline testing; production
    callers use the installed torch module. Return (usable, diagnostic).
    """
    if torch_module is None:
        import torch as torch_module

    if not torch_module.cuda.is_available():
        return False, CUDA_NOT_AVAILABLE
    try:
        problem = _missing_kernel_problem(torch_module.cuda)
        if problem is None:
            _gpu_smoke_test(torch_module)
    except Exception as exc:
        problem = str(exc)
    return (problem is None), problem
