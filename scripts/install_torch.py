"""Pick, install and check the PyTorch build for this machine.

setup_env.bat / setup_env.sh run this inside the app's venv. It looks for an
NVIDIA CUDA runtime, then walks a short list of wheel builds (newest CUDA
first, CPU last) until one installs and passes a real runtime check.
Exit code 0 means a working build is installed; 1 means every build failed.
Messages go to stdout and, when CHATTERBOX_INSTALL_LOG is set, to that file.
"""
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass

TORCH_WHEEL_ROOT = "https://download.pytorch.org/whl/"


@dataclass(frozen=True)
class Build:
    """One PyTorch wheel set and the CUDA runtime it needs (None = CPU)."""
    tag: str
    min_cuda: int | None
    torch: str
    torchvision: str
    torchaudio: str

    @property
    def index_url(self):
        return TORCH_WHEEL_ROOT + self.tag

    @property
    def is_cuda(self):
        return self.min_cuda is not None

    def requirements(self):
        return [f"torch=={self.torch}", f"torchvision=={self.torchvision}",
                f"torchaudio=={self.torchaudio}"]


# Newest CUDA first. cu128 (Blackwell-capable) ships 2.8.0; the older runtimes stay on 2.6.0.
CUDA_BUILDS = (
    Build("cu128", 128, "2.8.0", "0.23.0", "2.8.0"),
    Build("cu124", 124, "2.6.0", "0.21.0", "2.6.0"),
    Build("cu121", 121, "2.6.0", "0.21.0", "2.6.0"),
    Build("cu118", 118, "2.6.0", "0.21.0", "2.6.0"),
)
CPU_BUILD = Build("cpu", None, "2.6.0", "0.21.0", "2.6.0")
NEWEST_CUDA = CUDA_BUILDS[0]


class InstallLog:
    """Echo to the console and, when given a path, to the installer log as well."""

    def __init__(self, path=None):
        # Line-buffered so the log stays readable if the install is interrupted.
        self.file = open(path, "a", encoding="utf-8", buffering=1) if path else None

    def __call__(self, text):
        print(text)
        if self.file is not None:
            self.file.write(f"{text}\n")

    def output(self, stream_name, text):
        """Copy captured tool output, each line tagged with its stream."""
        if text:
            self("\n".join(f"[uv {stream_name}] {line}" for line in text.splitlines()))

    def close(self):
        if self.file is not None:
            self.file.close()


# --- step 1: find the CUDA runtime --------------------------------------------

def cuda_number(text):
    """'12.8' or '12.8.1' -> 128; anything unreadable -> None."""
    match = re.match(r"\s*(\d+)\.(\d+)", text or "")
    return int(match[1]) * 10 + int(match[2]) if match else None


def _first_line(text):
    return next((line for line in text.splitlines() if line.strip()), "")


def _smi_header(text):
    # Newer drivers print "CUDA UMD Version" and reject the cuda_version query.
    match = re.search(r"CUDA (?:UMD )?Version:\s*(\d+\.\d+)", text)
    return match[1] if match else ""


def _nvcc_release(text):
    match = re.search(r"release\s+(\d+\.\d+)", text)
    return match[1] if match else ""


# Tried in order; the first one that yields a version wins.
CUDA_PROBES = (
    ("nvidia-smi", ["nvidia-smi", "--query-gpu=cuda_version", "--format=csv,noheader"], _first_line),
    ("nvidia-smi header", ["nvidia-smi"], _smi_header),
    ("nvcc", ["nvcc", "--version"], _nvcc_release),
)


def find_cuda(run=None):
    """Return (cuda number such as 128, probe name) or (None, None)."""
    run = run or subprocess.check_output
    for source, argv, extract in CUDA_PROBES:
        try:
            text = run(argv, text=True, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.CalledProcessError):
            continue
        number = cuda_number(extract(text))
        if number is not None:
            return number, source
    return None, None


# --- step 2: decide which builds to try ---------------------------------------

def builds_to_try(cuda):
    """Builds in the order they should be attempted for this CUDA number."""
    if cuda is None:
        return [CPU_BUILD]
    if cuda >= NEWEST_CUDA.min_cuda:
        # Older runtimes lack kernels for the newest GPUs, so don't bother with them.
        return [NEWEST_CUDA, CPU_BUILD]
    usable = [build for build in CUDA_BUILDS if build.min_cuda <= cuda]
    return usable + [CPU_BUILD]


# --- step 3: install -----------------------------------------------------------

def uv_command(build, python=None):
    """The uv command that force-installs exactly this build into `python`."""
    return [
        "uv", "pip", "install", "--python", python or sys.executable,
        "--upgrade", "--reinstall", "--strict", "--no-deps",
        *build.requirements(),
        "--index-url", build.index_url,
    ]


# --- step 4: check the installed runtime ---------------------------------------

# Runs in a fresh interpreter so a broken import cannot take this script down.
RUNTIME_CHECK = r'''
import json
info = {"ok": False, "error": None, "cuda_runtime_ok": False, "cuda_runtime_error": None}
try:
    import torch
except Exception as exc:
    info["error"] = repr(exc)
else:
    cuda = torch.cuda
    has_gpu = bool(cuda.is_available())
    info.update(ok=True, torch_version=getattr(torch, "__version__", "unknown"),
                torch_cuda_version=getattr(torch.version, "cuda", None),
                cuda_available=has_gpu, device_count=0, arch_list=[], device_capability=None)
    if has_gpu:
        info.update(device_count=int(cuda.device_count()), arch_list=list(cuda.get_arch_list()),
                    device_capability=list(cuda.get_device_capability(0)))
        try:
            m = torch.randn((8, 8), device="cuda")
            (m @ m).sum().item()
            rnn = torch.nn.GRU(4, 4).to("cuda")
            rnn(torch.randn((2, 1, 4), device="cuda"))
            info["cuda_runtime_ok"] = True
        except Exception as exc:
            info["cuda_runtime_error"] = repr(exc)
print(json.dumps(info))
'''


def read_runtime(python=None, run=None):
    """Run RUNTIME_CHECK and return its JSON report."""
    run = run or subprocess.run
    done = run([python or sys.executable, "-c", RUNTIME_CHECK],
               check=True, capture_output=True, text=True)
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    if not lines:
        return {"ok": False, "error": "No verification output"}
    return json.loads(lines[-1])


def runtime_ok(report, needs_cuda):
    """True when torch imports and, for a CUDA build, the GPU actually computes."""
    if not report.get("ok"):
        return False
    return not needs_cuda or bool(report.get("cuda_available") and report.get("cuda_runtime_ok"))


def failure_summary(report):
    keys = ("cuda_available", "torch_cuda", "arch_list", "device_capability", "runtime_error", "error")
    values = (report.get("cuda_available"), report.get("torch_cuda_version"), report.get("arch_list"),
              report.get("device_capability"), report.get("cuda_runtime_error"), report.get("error"))
    return "verification failed: " + " ".join(f"{k}={v}" for k, v in zip(keys, values))


# --- driver ------------------------------------------------------------------

def try_build(build, say, run=None):
    """Install one build and check it. Returns (worked, reason if it did not)."""
    run = run or subprocess.run   # looked up per call so tests can replace it
    command = uv_command(build)
    say(f"Installing from: {build.index_url}")
    say(f"Running command: {' '.join(command)}")
    try:
        done = run(command, check=True, capture_output=True, text=True)
        say.output("stdout", done.stdout)
        say.output("stderr", done.stderr)
        report = read_runtime(run=run)
    except subprocess.CalledProcessError as failure:
        say.output("stdout", failure.stdout)
        say.output("stderr", failure.stderr)
        return False, f"installer exited with code {failure.returncode}"
    say(f"Verification payload for {build.tag}: {json.dumps(report, ensure_ascii=False)}")
    if not runtime_ok(report, build.is_cuda):
        return False, failure_summary(report)
    mode = "CUDA" if report.get("cuda_available") else "CPU"
    say(f"PyTorch verification succeeded. Mode={mode}, torch={report.get('torch_version')}, "
        f"torch_cuda={report.get('torch_cuda_version')}, devices={report.get('device_count')}")
    return True, None


def main(say=None):
    say = say or InstallLog(os.getenv("CHATTERBOX_INSTALL_LOG"))
    cuda, source = find_cuda()
    if cuda is None:
        say("No NVIDIA CUDA runtime detected. Installing CPU PyTorch build.")
    else:
        say(f"Detected NVIDIA CUDA capability {cuda} via {source}.")
    plan = builds_to_try(cuda)
    say("Install candidates: " + ", ".join(f"{b.tag} ({b.index_url})" for b in plan))

    failed = {}
    for position, build in enumerate(plan):
        say(f"Trying PyTorch target: {build.tag}")
        worked, reason = try_build(build, say)
        if worked:
            return 0
        say(f"PyTorch target {build.tag} failed: {reason}")
        failed[build.tag] = reason
        if position + 1 < len(plan):
            say("Falling back to the next compatible PyTorch runtime.")

    say("Unable to install a working PyTorch configuration.")
    say("Attempts:")
    for tag, reason in failed.items():
        say(f"  - {tag}: {reason}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
