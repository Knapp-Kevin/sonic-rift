"""Contract tests for the Sonic Rift wrapper around official Chatterbox APIs.

No torch, chatterbox, GPU or Hugging Face downloads are needed: the public
module is loaded under an isolated name with fake external SDK modules.
"""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


ADAPTER = Path(__file__).resolve().parents[1] / "this_voice_thing" / "engines" / "chatterbox_provider.py"


class FakeSpeechEngine:
    sr = 24000
    device = "cpu"

    def __init__(self):
        self.calls = []

    def generate(self, text, **kwargs):
        self.calls.append((text, kwargs))
        return "audio"


class FakeLegacy:
    calls = []

    @classmethod
    def from_local(cls, folder, device):
        cls.calls.append((folder, device))
        return FakeSpeechEngine()


class FakeMultilingual:
    pretrained_calls = []
    local_calls = []

    @classmethod
    def from_pretrained(cls, device, t3_model):
        cls.pretrained_calls.append((device, t3_model))
        return FakeSpeechEngine()

    @classmethod
    def from_local(cls, folder, device, t3_model=None):
        cls.local_calls.append((folder, device, t3_model))
        return FakeSpeechEngine()

    @classmethod
    def get_supported_languages(cls):
        return {"en": "English", "fr": "French"}


class ChatterboxProviderContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        def module(name):
            return types.ModuleType(name)

        torch = module("torch")
        torch.cuda = types.SimpleNamespace(is_available=lambda: False)
        hf = module("huggingface_hub")
        errors = module("huggingface_hub.errors")
        class EntryNotFoundError(Exception):
            pass
        errors.EntryNotFoundError = EntryNotFoundError
        hf.snapshot_download = lambda **_kwargs: "/tmp/fake-checkpoint"
        chatterbox = module("chatterbox")
        chatterbox.__path__ = []
        tts = module("chatterbox.tts")
        tts.ChatterboxTTS = FakeLegacy
        multilingual = module("chatterbox.mtl_tts")
        multilingual.ChatterboxMultilingualTTS = FakeMultilingual

        stubs = {
            "torch": torch, "huggingface_hub": hf,
            "huggingface_hub.errors": errors, "chatterbox": chatterbox,
            "chatterbox.tts": tts, "chatterbox.mtl_tts": multilingual,
        }
        spec = importlib.util.spec_from_file_location("sonic_rift_adapter_fixture", ADAPTER)
        loaded = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {**stubs, spec.name: loaded}):
            spec.loader.exec_module(loaded)
        cls.adapter = loaded

    def setUp(self):
        FakeLegacy.calls = []
        FakeMultilingual.pretrained_calls = []
        FakeMultilingual.local_calls = []

    def test_default_multilingual_uses_official_pretrained_factory(self):
        m = self.adapter
        session = m.load_chatterbox_model(m.DEFAULT_MODEL_REPO, m.BACKEND_MULTILINGUAL, "cpu", "v3")
        self.assertEqual(FakeMultilingual.pretrained_calls,
                         [("cpu", "t3_mtl23ls_v3.safetensors")])
        self.assertEqual(FakeMultilingual.local_calls, [])
        self.assertEqual(session.supported_languages["fr"], "French")
        self.assertEqual(session.sr, 24000)

    def test_custom_multilingual_repository_uses_local_checkpoint(self):
        m = self.adapter
        with patch.object(m, "_fetch_assets", return_value=Path("/fake")) as download:
            session = m.load_chatterbox_model("custom/audio", m.BACKEND_MULTILINGUAL, "cpu", "v2")
        download.assert_called_once()
        self.assertEqual(FakeMultilingual.local_calls,
                         [(Path("/fake"), "cpu", "t3_mtl23ls_v2.safetensors")])
        self.assertEqual(session.repo_id, "custom/audio")

    def test_english_uses_legacy_checkpoint_contract(self):
        m = self.adapter
        with patch.object(m, "_fetch_assets", return_value=Path("/legacy")):
            session = m.load_chatterbox_model("legacy/audio", m.BACKEND_LEGACY, "cpu")
        self.assertEqual(FakeLegacy.calls, [(Path("/legacy"), "cpu")])
        self.assertEqual(session.supported_languages, {"en": "English"})

    def test_unknown_backend_fails_before_loading(self):
        with self.assertRaisesRegex(ValueError, "Unknown Chatterbox backend"):
            self.adapter.load_chatterbox_model("repo", "other", "cpu")
        self.assertEqual(FakeLegacy.calls, [])
        self.assertEqual(FakeMultilingual.local_calls, [])

    def test_generation_forwards_multilingual_only_options_when_supported(self):
        m = self.adapter
        engine = FakeSpeechEngine()
        session = m.ChatterboxSession(engine, m.BACKEND_MULTILINGUAL, "r", {"en": "English"})
        self.assertEqual(session.generate("bonjour", language_id="fr", top_p=0.7), "audio")
        args = engine.calls[0][1]
        self.assertEqual(args["language_id"], "fr")
        self.assertEqual(args["top_p"], 0.7)
        session.backend = m.BACKEND_LEGACY
        session.generate("hello", language_id="fr")
        self.assertNotIn("language_id", engine.calls[1][1])
        self.assertNotIn("top_p", engine.calls[1][1])

    def test_unsupported_repo_error_preserves_root_cause(self):
        m = self.adapter
        from_error = m.EntryNotFoundError("assets not found")
        with patch.object(m, "_fetch_assets", side_effect=from_error):
            with self.assertRaises(m.UnsupportedChatterboxRepoError) as raised:
                m.load_chatterbox_model("absent/model", m.BACKEND_LEGACY, "cpu")
        self.assertIs(raised.exception.__cause__, from_error)

    def test_missing_cuda_cannot_report_usable_gpu(self):
        self.assertEqual(
            self.adapter.probe_usable_torch_cuda(),
            (False, "torch.cuda.is_available() returned False."),
        )


if __name__ == "__main__":
    unittest.main()
