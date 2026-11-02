"""Resource limits for engine workers, set by the app through environment variables.

Each worker calls apply(torch) right after importing torch. The thread variables
(OMP_NUM_THREADS and friends) are already in the environment from the app; this also
caps PyTorch's own thread pools and the GPU memory it may allocate, so an engine that
needs more fails with a clear out-of-memory error instead of slowing the whole PC.
"""

import os


def apply(torch):
    threads = int(os.environ.get("SONIC_RIFT_CPU_THREADS", "0") or 0)
    if threads > 0:
        torch.set_num_threads(threads)
        try:
            torch.set_num_interop_threads(max(1, min(threads, 4)))
        except RuntimeError:            # already set once work has started
            pass
    cap_gb = float(os.environ.get("SONIC_RIFT_GPU_MEMORY_GB", "0") or 0)
    if cap_gb > 0 and torch.cuda.is_available():
        total_gb = torch.cuda.get_device_properties(0).total_memory / 2**30
        torch.cuda.set_per_process_memory_fraction(min(1.0, cap_gb / total_gb), 0)
    return {"threads": threads, "gpu_memory_gb": cap_gb}
