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

        class LocalEntryNotFoundError(EntryNotFoundError):   # as in huggingface_hub
            pass

        class RepositoryNotFoundError(Exception):
            pass
        errors.EntryNotFoundError = EntryNotFoundError
        errors.LocalEntryNotFoundError = LocalEntryNotFoundError
        errors.RepositoryNotFoundError = RepositoryNotFoundError
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

    def _snapshot_with(self, files):
        """A fake snapshot folder holding `files`; records the patterns requested."""
        import shutil
        import tempfile
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        for name in files:
            (folder / name).write_bytes(b"x")
        requested = []

        def snapshot_download(**kwargs):
            requested.append(kwargs["allow_patterns"])
            return str(folder)
        return folder, requested, snapshot_download

    def test_custom_multilingual_downloads_only_what_the_loader_reads(self):
        m = self.adapter
        needed = ["ve.pt", "s3gen.pt", "grapheme_mtl_merged_expanded_v1.json", "t3_mtl23ls_v3.safetensors"]
        folder, requested, fake = self._snapshot_with(needed)
        with patch.object(m, "snapshot_download", fake):
            m.load_chatterbox_model("custom/audio", m.BACKEND_MULTILINGUAL, "cpu", "v3")
        self.assertEqual(FakeMultilingual.local_calls, [(folder, "cpu", "t3_mtl23ls_v3.safetensors")])
        patterns = set(requested[0])
        self.assertIn("t3_mtl23ls_v3.safetensors", patterns)
        for unused in ("t3_mtl23ls_v2.safetensors", "t3_23lang.safetensors", "s3gen_v3.pt", "s3gen_v3.safetensors"):
            self.assertNotIn(unused, patterns)

    def test_repository_missing_files_gets_a_clear_error(self):
        m = self.adapter
        _folder, _requested, fake = self._snapshot_with(["ve.pt"])   # e.g. some other model's repo
        with patch.object(m, "snapshot_download", fake):
            with self.assertRaises(m.UnsupportedChatterboxRepoError) as raised:
                m.load_chatterbox_model("other/model", m.BACKEND_MULTILINGUAL, "cpu", "v3")
        message = str(raised.exception)
        self.assertIn("s3gen.pt", message)
        self.assertIn("t3_mtl23ls_v3.safetensors", message)
        self.assertNotIn("multilingual_t3_model", message)      # a different model entirely: no hint
        self.assertEqual(FakeMultilingual.local_calls, [])

        older = ["ve.pt", "s3gen.pt", "grapheme_mtl_merged_expanded_v1.json", "t3_mtl23ls_v2.safetensors"]
        _folder, _requested, fake = self._snapshot_with(older)  # an older repository: no v3 weights
        with patch.object(m, "snapshot_download", fake):
            with self.assertRaisesRegex(m.UnsupportedChatterboxRepoError, "multilingual_t3_model to v2"):
                m.load_chatterbox_model("older/model", m.BACKEND_MULTILINGUAL, "cpu", "v3")

        _folder, _requested, fake = self._snapshot_with([])
        with patch.object(m, "snapshot_download", fake):
            with self.assertRaisesRegex(m.UnsupportedChatterboxRepoError, "t3_cfg.safetensors"):
                m.load_chatterbox_model("other/model", m.BACKEND_LEGACY, "cpu")
        self.assertEqual(FakeLegacy.calls, [])

    def test_v2_hint_only_when_v3_was_requested_and_is_the_only_gap(self):
        m = self.adapter
        base = ["ve.pt", "s3gen.pt", "grapheme_mtl_merged_expanded_v1.json"]
        _folder, _requested, fake = self._snapshot_with(base)        # v2 requested, v2 missing
        with patch.object(m, "snapshot_download", fake):
            with self.assertRaises(m.UnsupportedChatterboxRepoError) as raised:
                m.load_chatterbox_model("custom/audio", m.BACKEND_MULTILINGUAL, "cpu", "v2")
        self.assertIn("t3_mtl23ls_v2.safetensors", str(raised.exception))
        self.assertNotIn("set its multilingual_t3_model to v2", str(raised.exception))
        _folder, _requested, fake = self._snapshot_with(base)        # v3 requested, v3 missing
        with patch.object(m, "snapshot_download", fake):
            with self.assertRaises(m.UnsupportedChatterboxRepoError) as raised:
                m.load_chatterbox_model("custom/audio", m.BACKEND_MULTILINGUAL, "cpu", "v3")
        self.assertIn("set its multilingual_t3_model to v2", str(raised.exception))
        self.assertEqual(raised.exception.missing, ["t3_mtl23ls_v3.safetensors"])
        self.assertIsInstance(raised.exception.__cause__, m.UnsupportedChatterboxRepoError)

    def test_offline_without_cache_is_not_called_incompatible(self):
        m = self.adapter
        error = m.LocalEntryNotFoundError("offline")
        with patch.object(m, "snapshot_download", side_effect=error):
            with self.assertRaises(m.UnsupportedChatterboxRepoError) as raised:
                m.load_chatterbox_model("custom/audio", m.BACKEND_MULTILINGUAL, "cpu", "v3")
        self.assertIn("unreachable or offline", str(raised.exception))
        self.assertIs(raised.exception.__cause__, error)

    def test_resolver_matches_the_previous_backend(self):
        resolve = self.adapter.resolve_multilingual_t3_model
        cases = {None: "t3_mtl23ls_v3.safetensors", "": "t3_mtl23ls_v3.safetensors",
                 "v2": "t3_mtl23ls_v2.safetensors", " V3 ": "t3_mtl23ls_v3.safetensors",
                 "T3_MTL23LS_V2.safetensors": "t3_mtl23ls_v2.safetensors",
                 "v2.safetensors": "v2.safetensors",                      # a repository's own file name
                 "t3_23lang.safetensors": "t3_23lang.safetensors", "Custom_T3": "Custom_T3"}
        for value, expected in cases.items():
            self.assertEqual(resolve(value), expected, value)

    def test_older_engine_without_t3_selection_uses_the_full_download_set(self):
        m = self.adapter

        class OlderMultilingual(FakeMultilingual):
            from_pretrained = None
            calls = []

            @classmethod
            def from_local(cls, folder, device):          # no t3_model parameter
                cls.calls.append((folder, device))
                return FakeSpeechEngine()

        folder, requested, fake = self._snapshot_with(["ve.pt", "s3gen.pt"])
        with patch.object(m, "ChatterboxMultilingualTTS", OlderMultilingual), \
                patch.object(m, "snapshot_download", fake):
            m.load_chatterbox_model(m.DEFAULT_MODEL_REPO, m.BACKEND_MULTILINGUAL, "cpu", "v2")
        self.assertEqual(OlderMultilingual.calls, [(folder, "cpu")])
        self.assertEqual(set(requested[0]), set(m.MULTILINGUAL_MODEL_FILES))

    def test_unknown_or_gated_repository_is_explained(self):
        m = self.adapter
        error = m.RepositoryNotFoundError("401 Client Error")
        with patch.object(m, "snapshot_download", side_effect=error):
            with self.assertRaises(m.UnsupportedChatterboxRepoError) as raised:
                m.load_chatterbox_model("nobody/nothing", m.BACKEND_MULTILINGUAL, "cpu", "v3")
        self.assertIn("wasn't found on Hugging Face", str(raised.exception))
        self.assertIs(raised.exception.__cause__, error)

    def test_missing_cuda_cannot_report_usable_gpu(self):
        self.assertEqual(
            self.adapter.probe_usable_torch_cuda(),
            (False, "torch.cuda.is_available() returned False."),
        )


if __name__ == "__main__":
    unittest.main()
