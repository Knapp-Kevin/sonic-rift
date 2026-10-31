"""MCP gateway never accepts an anonymous or non-loopback application service."""
import io
import json
import os
import unittest
from unittest.mock import patch
from urllib import error, request

from this_voice_thing.integrations.agent_gateway import (
    GatewayUnavailable, LocalGateway, MAX_RESPONSE, _RefuseRedirects, _open_loopback,
)


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.body = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size=-1):
        return self.body[:size]


class GatewayTests(unittest.TestCase):
    def test_token_is_required_even_if_app_is_unprotected(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(GatewayUnavailable, "SONIC_RIFT_API_TOKEN"):
                LocalGateway()
        with self.assertRaises(GatewayUnavailable):
            LocalGateway(token="")
        with self.assertRaises(GatewayUnavailable):
            LocalGateway(port=0, token="private")

    def test_anonymous_local_api_is_refused(self):
        gateway = LocalGateway(token="not-printed")
        with patch("this_voice_thing.integrations.agent_gateway._open_loopback",
                   return_value=FakeResponse({"status": "ready"})):
            with self.assertRaisesRegex(GatewayUnavailable, "anonymous"):
                gateway.health()

    def test_protected_api_returns_compact_fields_only(self):
        calls = []
        def urlopen(req, timeout):
            calls.append((req.full_url, req.get_header("Authorization"), timeout))
            if not req.get_header("Authorization"):
                raise error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)
            return FakeResponse({"status": "ready", "model": "Chatterbox",
                                 "device": "cuda", "voice": "private-person",
                                 "endpoints": ["sensitive"]})
        gateway = LocalGateway(port=8765, token="not-printed")
        with patch("this_voice_thing.integrations.agent_gateway._open_loopback",
                   side_effect=urlopen):
            self.assertEqual(gateway.health(),
                             {"status": "ready", "loaded_model": "Chatterbox",
                              "device": "cuda"})
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(url.startswith("http://127.0.0.1:8765/v1/") for url, _, _ in calls))
        self.assertIsNone(calls[0][1])
        self.assertEqual(calls[1][1], "Bearer not-printed")

    def test_model_catalog_is_bounded_and_explicitly_voice_only(self):
        def urlopen(req, timeout):
            if not req.get_header("Authorization"):
                raise error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)
            return FakeResponse({"object": "list", "data": [
                {"id": f"engine-{i}", "engine": "Chatterbox", "installed": True,
                 "loaded": False, "repo_id": "never-echo-this-path"}
                for i in range(45)
            ]})
        gateway = LocalGateway(token="not-printed")
        with patch("this_voice_thing.integrations.agent_gateway._open_loopback",
                   side_effect=urlopen):
            payload = gateway.voice_models()
        self.assertEqual(payload["shown"], 40)
        self.assertTrue(payload["truncated"])
        self.assertEqual(payload["kind"], "speech_and_voice_only")
        self.assertNotIn("repo_id", payload["models"][0])

    def test_no_arbitrary_url_or_endpoint(self):
        gateway = LocalGateway(token="not-printed")
        with self.assertRaises(GatewayUnavailable):
            gateway._get("http://remote.invalid/secrets", authenticated=True)

    def test_redirects_always_fail_closed(self):
        with self.assertRaisesRegex(GatewayUnavailable, "redirects are forbidden"):
            _RefuseRedirects().redirect_request(
                None, None, 302, "redirect", {},
                "http://example.invalid/steal-token",
            )

    def test_explicitly_disables_environment_http_proxies(self):
        req = request.Request("http://127.0.0.1:8765/v1/health")
        with patch("this_voice_thing.integrations.agent_gateway.request.build_opener") as make:
            _open_loopback(req)
        handlers = make.call_args.args
        self.assertEqual(handlers[0].proxies, {})
        self.assertIsInstance(handlers[1], _RefuseRedirects)
        self.assertEqual(make.return_value.open.call_args.kwargs["timeout"], 3)

    def test_response_size_limit(self):
        gateway = LocalGateway(token="not-printed")
        large = b"{" + b"x" * MAX_RESPONSE + b"}"
        class BigResponse:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return False
            def read(self, _n):
                return large
        with patch("this_voice_thing.integrations.agent_gateway._open_loopback",
                   return_value=BigResponse()):
            with self.assertRaisesRegex(GatewayUnavailable, "size limit"):
                gateway._get("/v1/health", authenticated=True)


if __name__ == "__main__":
    unittest.main()
