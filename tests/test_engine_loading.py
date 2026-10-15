"""Pure-Python tests for the engine-independent model loader."""
import unittest

from this_voice_thing.core.engine_loading import (
    EngineProvider,
    EngineRequest,
    EngineUnavailableError,
    UnsupportedEngineError,
    load_engine,
)


class DeviceModel:
    def __init__(self):
        self.moves = []

    def to(self, target):
        self.moves.append(target)


class EngineLoadingTests(unittest.TestCase):
    def request(self, backend="kokoro"):
        return EngineRequest(
            backend=backend, repo_id="example/model",
            device="cpu", mode="design", multilingual_t3_model="v3",
        )

    def test_selected_provider_receives_full_request_and_moves_model(self):
        calls = []
        model = DeviceModel()
        providers = {
            "kokoro": EngineProvider(
                load=lambda request: calls.append(request) or model,
                available=lambda: True,
                unavailable_message="not installed",
            ),
        }
        self.assertIs(load_engine(self.request(), providers), model)
        self.assertEqual(calls, [self.request()])
        self.assertEqual(model.moves, ["cpu"])

    def test_all_supported_engines_dispatch_without_chatterbox(self):
        backends = ["qwen3", "kokoro", "voxcpm", "omnivoice", "vibevoice"]
        calls = []
        providers = {
            backend: EngineProvider(
                load=lambda request: calls.append(request.backend) or object(),
                available=lambda: True,
                unavailable_message="not installed",
            ) for backend in backends
        }
        for backend in backends:
            self.assertIsNotNone(load_engine(self.request(backend), providers))
        self.assertEqual(calls, backends)

    def test_unavailable_engine_does_not_invoke_factory(self):
        called = []
        providers = {
            "qwen3": EngineProvider(
                load=lambda request: called.append(request),
                available=lambda: False,
                unavailable_message="Install Qwen first.",
            ),
        }
        with self.assertRaisesRegex(EngineUnavailableError, "Install Qwen first"):
            load_engine(self.request("qwen3"), providers)
        self.assertEqual(called, [])

    def test_unknown_backend_fails_closed(self):
        with self.assertRaisesRegex(UnsupportedEngineError, "unknown"):
            load_engine(self.request("unknown"), {})

    def test_backend_returning_none_is_not_success(self):
        providers = {
            "kokoro": EngineProvider(
                load=lambda _request: None, available=lambda: True,
                unavailable_message="missing",
            ),
        }
        with self.assertRaisesRegex(RuntimeError, "returned no model"):
            load_engine(self.request(), providers)

    def test_out_of_process_model_does_not_need_to_method(self):
        model = object()
        providers = {
            "vibevoice": EngineProvider(
                load=lambda _request: model,
                available=lambda: True,
                unavailable_message="missing",
            ),
        }
        self.assertIs(load_engine(self.request("vibevoice"), providers), model)

    def test_factory_exception_propagates_without_fallback(self):
        def failing(_request):
            raise OSError("bad checkpoint")
        providers = {
            "kokoro": EngineProvider(failing, lambda: True, "missing"),
            "multilingual": EngineProvider(
                lambda _request: self.fail("must not fallback to Chatterbox"),
                lambda: True, "missing",
            ),
        }
        with self.assertRaisesRegex(OSError, "bad checkpoint"):
            load_engine(self.request("kokoro"), providers)


if __name__ == "__main__":
    unittest.main()
