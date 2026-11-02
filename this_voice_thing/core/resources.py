"""How much of the PC Sonic Rift's generation may use, and what a heavy job will cost.

Defaults come from the machine: half the CPU threads, below-normal priority for engine
workers (so games and other apps stay smooth), and GPU memory with headroom left for the
desktop. The user can change each limit in Settings. Engine workers read the limits from
environment variables (engines/worker_limits.py); a limit applies from the next engine start.

Qt-free so the job service and future agent adapter can check the same budget.
"""

import ctypes
import os
import subprocess
from dataclasses import asdict, dataclass

PRIORITIES = ("normal", "below_normal", "low")
PRIORITY_LABELS = {"normal": "Normal", "below_normal": "Below normal (recommended)", "low": "Low (only when idle)"}
GPU_HEADROOM_GB = 0.5           # hard cap: the display needs some; the largest model (MOSS, ~15.2 GB) still fits 16 GB
COMFORT_HEADROOM_GB = 2.0       # below this much free, other apps and games will struggle: warn
_WINDOWS_PRIORITY = {"normal": 0x00000020, "below_normal": 0x00004000, "low": 0x00000040}


@dataclass(frozen=True)
class SystemInfo:
    cpu_threads: int
    ram_gb: float
    gpu_name: str = ""
    gpu_gb: float = 0.0


@dataclass(frozen=True)
class ResourceLimits:
    cpu_threads: int                # math threads per engine (PyTorch, OpenMP, MKL)
    priority: str                   # engine worker process priority
    gpu_memory_gb: float            # most GPU memory one engine may allocate (0 = no GPU)
    warn_heavy_jobs: bool = True    # explain the cost before a long or heavy job

    def to_dict(self):
        return asdict(self)


def _ram_gb():
    if os.name == "nt":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return status.ullTotalPhys / 2**30
        return 0.0
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30
    except (ValueError, OSError, AttributeError):
        return 0.0


def _gpu():
    """(name, GB) of the first NVIDIA GPU via nvidia-smi (no CUDA context is created)."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        name, mib = out.strip().splitlines()[0].rsplit(",", 1)
        return name.strip(), int(mib) / 1024
    except Exception:
        return "", 0.0


def detect():
    name, gpu_gb = _gpu()
    return SystemInfo(cpu_threads=os.cpu_count() or 1, ram_gb=round(_ram_gb(), 1), gpu_name=name,
                      gpu_gb=round(gpu_gb, 1))


def recommended(system):
    """Default maximums for this machine."""
    gpu = max(0.0, round(system.gpu_gb - GPU_HEADROOM_GB, 1)) if system.gpu_gb else 0.0
    return ResourceLimits(cpu_threads=max(1, system.cpu_threads // 2), priority="below_normal",
                          gpu_memory_gb=gpu, warn_heavy_jobs=True)


def from_settings(stored, system):
    """Saved limits, each clamped to what this machine has; missing values use the defaults."""
    base = recommended(system)
    stored = stored or {}
    try:
        threads = int(stored.get("cpu_threads", base.cpu_threads))
    except (TypeError, ValueError):
        threads = base.cpu_threads
    try:
        gpu = float(stored.get("gpu_memory_gb", base.gpu_memory_gb))
    except (TypeError, ValueError):
        gpu = base.gpu_memory_gb
    priority = stored.get("priority", base.priority)
    return ResourceLimits(
        cpu_threads=min(max(1, threads), system.cpu_threads),
        priority=priority if priority in PRIORITIES else base.priority,
        gpu_memory_gb=round(min(max(0.0, gpu), system.gpu_gb), 1) if system.gpu_gb else 0.0,
        warn_heavy_jobs=bool(stored.get("warn_heavy_jobs", base.warn_heavy_jobs)))


_current = None


def set_current(limits):
    global _current
    _current = limits


def current():
    """The limits in force (the app sets them at start and when Settings change)."""
    return _current


def worker_env(limits):
    """Environment variables that hold an engine worker to `limits`."""
    if limits is None:
        return {}
    threads = str(limits.cpu_threads)
    return {"OMP_NUM_THREADS": threads, "MKL_NUM_THREADS": threads, "OPENBLAS_NUM_THREADS": threads,
            "NUMEXPR_MAX_THREADS": threads, "SONIC_RIFT_CPU_THREADS": threads,
            "SONIC_RIFT_GPU_MEMORY_GB": f"{limits.gpu_memory_gb:g}"}


def creation_flags(limits):
    """Windows process-priority flag for a new worker; its child processes inherit it."""
    if os.name != "nt" or limits is None:
        return 0
    return _WINDOWS_PRIORITY[limits.priority]


def lower_priority_posix(limits):
    """preexec_fn for POSIX workers (None on Windows or at normal priority)."""
    if os.name == "nt" or limits is None or limits.priority == "normal":
        return None
    amount = 10 if limits.priority == "below_normal" else 19
    return lambda: os.nice(amount)


@dataclass(frozen=True)
class JobCost:
    """What a job is expected to take, for the warning before it runs."""
    label: str
    minutes: float
    gpu_gb: float = 0.0
    ram_gb: float = 0.0


def heavy(cost, limits):
    """Whether `cost` is worth a warning: long, or a large share of the GPU budget."""
    return cost.minutes >= 2 or bool(limits.gpu_memory_gb and cost.gpu_gb >= 0.6 * limits.gpu_memory_gb)


def over_budget(cost, limits, system):
    """Plain-language reasons `cost` doesn't fit the limits or this machine (empty when it fits)."""
    problems = []
    if cost.gpu_gb and cost.gpu_gb > limits.gpu_memory_gb:
        problems.append(f"needs about {cost.gpu_gb:.0f} GB of GPU memory and your limit is "
                        f"{limits.gpu_memory_gb:g} GB")
    if cost.ram_gb and system.ram_gb and cost.ram_gb > 0.8 * system.ram_gb:
        problems.append(f"needs about {cost.ram_gb:.0f} GB of RAM and this PC has {system.ram_gb:.0f} GB")
    return problems


def warning_text(cost, limits, system):
    lines = [f"{cost.label} will take about {_duration(cost.minutes)}."]
    uses = []
    if cost.gpu_gb:
        uses.append(f"about {cost.gpu_gb:.0f} GB of GPU memory (limit {limits.gpu_memory_gb:g} GB)")
    if cost.ram_gb:
        uses.append(f"about {cost.ram_gb:.0f} GB of RAM (of {system.ram_gb:.0f} GB)")
    uses.append(f"up to {limits.cpu_threads} of {system.cpu_threads} CPU threads at "
                f"{PRIORITY_LABELS[limits.priority].split(' (')[0].lower()} priority")
    lines.append("It uses " + ", ".join(uses) + ".")
    if cost.gpu_gb and system.gpu_gb and system.gpu_gb - cost.gpu_gb < COMFORT_HEADROOM_GB:
        lines.append(f"That leaves under {COMFORT_HEADROOM_GB:g} GB of GPU memory for everything else: close "
                     "games and other GPU apps first, or they may stutter or fail.")
    lines.append("Games, video and other heavy apps may run slower meanwhile. You can change these "
                 "limits in Settings › Performance.")
    return "\n\n".join(lines)


def _duration(minutes):
    if minutes < 1:
        return "under a minute"
    if minutes < 90:
        return f"{minutes:.0f} minute{'s' if round(minutes) != 1 else ''}"
    return f"{minutes / 60:.1f} hours"
