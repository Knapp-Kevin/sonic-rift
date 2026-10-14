"""A missing chatterbox-tts library must only block the Chatterbox engine (#55 audit)."""

import unittest
from unittest.mock import patch

from this_voice_thing.ui import common, threads


class _Model:
    device = "cpu"

    def to(self, _device):
        return self


class ChatterboxGateTests(unittest.TestCase):
    def run_loader(self, backend):
        thread = threads.ModelLoaderThread(repo_id="some/repo", backend=backend)
        loaded, errors = [], []
        thread.model_loaded.connect(lambda model, device: loaded.append(model))
        thread.error_occurred.connect(errors.append)
        thread.run()                      # synchronously; no event loop needed for direct signals
        return loaded, errors

    def test_other_engines_load_without_chatterbox(self):
        with patch.object(threads, "CHATTERBOX_AVAILABLE", False), \
                patch.object(threads.kokoro_engine, "load_kokoro_model", return_value=_Model()):
            loaded, errors = self.run_loader(common.KOKORO_BACKEND)
        self.assertEqual(errors, [])
        self.assertEqual(len(loaded), 1)

    def test_chatterbox_backend_reports_clearly(self):
        with patch.object(threads, "CHATTERBOX_AVAILABLE", False):
            loaded, errors = self.run_loader(common.BACKEND_MULTILINGUAL)
        self.assertEqual(loaded, [])
        self.assertIn("Other engines still work", errors[0])

    def test_needs_chatterbox(self):
        self.assertTrue(common.needs_chatterbox(common.BACKEND_MULTILINGUAL))
        self.assertTrue(common.needs_chatterbox(common.BACKEND_LEGACY))
        for backend in common.WORKER_BACKENDS:
            self.assertFalse(common.needs_chatterbox(backend))


if __name__ == "__main__":
    unittest.main()
