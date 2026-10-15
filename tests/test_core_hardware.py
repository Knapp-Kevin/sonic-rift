"""Offline hardware checks independent of optional Chatterbox dependencies."""
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from this_voice_thing.core import hardware


class _Tensor:
    def __matmul__(self, other):
        return self

    def sum(self):
        return self

    def item(self):
        return 1


class _RNN:
    def to(self, device):
        assert device == "cuda"
        return self

    def __call__(self, value):
        return value


class HardwareProbeTests(unittest.TestCase):
    def test_nvidia_device_detection(self):
        with patch.object(hardware.subprocess, "run", return_value=SimpleNamespace(stdout="GPU 0: NVIDIA")):
            self.assertTrue(hardware.has_system_nvidia_gpu())
        with patch.object(hardware.subprocess, "run", return_value=SimpleNamespace(stdout="")):
            self.assertFalse(hardware.has_system_nvidia_gpu())

    def test_absent_nvidia_utility_does_not_crash(self):
        with patch.object(hardware.subprocess, "run", side_effect=FileNotFoundError):
            self.assertFalse(hardware.has_system_nvidia_gpu())
        with patch.object(hardware.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "nvidia-smi")):
            self.assertFalse(hardware.has_system_nvidia_gpu())

    def test_cuda_unavailable(self):
        stub = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
        self.assertEqual(
            hardware.probe_usable_torch_cuda(stub),
            (False, "torch.cuda.is_available() returned False."),
        )

    def test_missing_kernel_architecture_fails_before_gpu_allocation(self):
        stub = SimpleNamespace(cuda=SimpleNamespace(
            is_available=lambda: True,
            get_device_capability=lambda _index: (8, 9),
            get_arch_list=lambda: ["sm_86"],
        ))
        usable, diagnostic = hardware.probe_usable_torch_cuda(stub)
        self.assertFalse(usable)
        self.assertIn("sm_89", diagnostic)

    def test_gpu_tensor_and_rnn_smoke(self):
        stub = SimpleNamespace(
            cuda=SimpleNamespace(
                is_available=lambda: True,
                get_device_capability=lambda _index: (8, 9),
                get_arch_list=lambda: ["sm_89"],
            ),
            randn=lambda *args, **kwargs: _Tensor(),
            nn=SimpleNamespace(GRU=lambda *_args: _RNN()),
        )
        self.assertEqual(hardware.probe_usable_torch_cuda(stub), (True, None))

    def test_kernel_exception_is_diagnostic_not_crash(self):
        stub = SimpleNamespace(
            cuda=SimpleNamespace(
                is_available=lambda: True,
                get_device_capability=lambda _index: (8, 9),
                get_arch_list=lambda: ["sm_89"],
            ),
            randn=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("CUDA kernel failed")),
        )
        usable, diagnostic = hardware.probe_usable_torch_cuda(stub)
        self.assertFalse(usable)
        self.assertIn("CUDA kernel failed", diagnostic)


if __name__ == "__main__":
    unittest.main()
