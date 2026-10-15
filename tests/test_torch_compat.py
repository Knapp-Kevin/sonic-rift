"""Offline regression tests for Sonic Rift's PyTorch loading compatibility hook."""
from types import SimpleNamespace
import unittest

from this_voice_thing.core.torch_compat import (
    install_default_load_device,
    preferred_load_device,
)


class TorchStub:
    def __init__(self):
        self.calls = []
        self.load = self.original_load
        self.cuda = SimpleNamespace(is_available=lambda: False)
        self.backends = SimpleNamespace(mps=SimpleNamespace(is_available=lambda: False))

    def original_load(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return "loaded"


class TorchCompatibilityTests(unittest.TestCase):
    def test_device_precedence(self):
        torch = TorchStub()
        self.assertEqual(preferred_load_device(torch), "cpu")
        torch.backends.mps.is_available = lambda: True
        self.assertEqual(preferred_load_device(torch), "mps")
        torch.cuda.is_available = lambda: True
        self.assertEqual(preferred_load_device(torch), "cuda")

    def test_broken_accelerator_probe_falls_back_safely(self):
        torch = TorchStub()
        def bad():
            raise RuntimeError("driver mismatch")
        torch.cuda.is_available = bad
        self.assertEqual(preferred_load_device(torch), "cpu")
        torch.backends.mps.is_available = lambda: True
        self.assertEqual(preferred_load_device(torch), "mps")

    def test_default_load_device_and_explicit_override(self):
        torch = TorchStub()
        original = torch.load
        self.assertIs(install_default_load_device(torch, "cuda"), original)
        self.assertEqual(torch.load("weights.bin"), "loaded")
        self.assertEqual(torch.calls[-1], (("weights.bin",), {"map_location": "cuda"}))
        torch.load("other.bin", map_location="cpu")
        self.assertEqual(torch.calls[-1][1]["map_location"], "cpu")
        torch.load("third.bin", map_location=None)
        self.assertIsNone(torch.calls[-1][1]["map_location"])

    def test_repeated_install_does_not_wrap_twice(self):
        torch = TorchStub()
        original = install_default_load_device(torch, "cuda")
        first_wrapper = torch.load
        self.assertIs(install_default_load_device(torch, "cpu"), original)
        self.assertIs(first_wrapper, torch.load)
        torch.load("weights.bin")
        self.assertEqual(len(torch.calls), 1)
        self.assertEqual(torch.calls[0][1]["map_location"], "cpu")

    def test_none_available_without_backend_attribute(self):
        torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
        self.assertEqual(preferred_load_device(torch), "cpu")

    def test_wrap_preserves_callable_identity_metadata(self):
        torch = TorchStub()
        original = torch.load
        install_default_load_device(torch, "cpu")
        self.assertIs(torch.load.__wrapped__, original)
        self.assertTrue(torch.load._sonic_rift_default_load)


if __name__ == "__main__":
    unittest.main()
