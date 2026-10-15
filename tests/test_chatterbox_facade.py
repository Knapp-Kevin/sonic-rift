"""The historical import path still exposes the old backend's public names."""

import unittest

HISTORICAL = ["BACKEND_LEGACY", "BACKEND_MULTILINGUAL", "DEFAULT_MODEL_REPO", "DEFAULT_MULTILINGUAL_T3_MODEL",
              "LEGACY_MODEL_FILES", "MULTILINGUAL_MODEL_FILES", "MULTILINGUAL_T3_MODEL_ALIASES",
              "LoadedChatterboxModel", "UnsupportedChatterboxRepoError", "get_supported_languages_for_backend",
              "has_system_nvidia_gpu", "load_chatterbox_model", "probe_usable_torch_cuda",
              "resolve_multilingual_t3_model"]


class ChatterboxFacadeTests(unittest.TestCase):
    def test_facade_reexports_the_provider(self):
        try:
            from this_voice_thing.engines import chatterbox_backend, chatterbox_provider
        except ImportError as exc:      # chatterbox-tts not installed in this environment
            self.skipTest(f"chatterbox-tts unavailable: {exc}")
        for name in HISTORICAL:
            self.assertIs(getattr(chatterbox_backend, name), getattr(chatterbox_provider, name), name)


if __name__ == "__main__":
    unittest.main()
