"""Integration contracts: real loopback HTTP and the same MCP planner core.

No engines, Qt, downloads, GPU, user files or external network access.
"""
import json
from urllib import error, request
import unittest

from this_voice_thing.core.agent_jobs import capabilities, plan_request
from this_voice_thing.integrations.local_api import LocalApiServer


class ForbiddenBackend:
    def __getattr__(self, name):
        raise AssertionError("Planning must not reach UI, engine or backend: " + name)


class AgentPlanHttpTests(unittest.TestCase):
    def setUp(self):
        self.server = LocalApiServer(
            ForbiddenBackend(), port=0, token="private-local-test-token", log=lambda _: None)
        self.server.start()
        self.addCleanup(self.server.stop)
        self.headers = {"Authorization": "Bearer private-local-test-token"}
        self.sample = {"kind": "music.generate",
                       "model_id": "ACE-Step/Ace-Step1.5",
                       "prompt": "an entirely private studio test prompt",
                       "duration_seconds": 14, "seed": 11,
                       "instrumental": True}

    def fetch(self, path, *, body=None, headers=None):
        payload = None if body is None else json.dumps(body).encode("utf-8")
        h = dict(self.headers if headers is None else headers)
        if payload is not None:
            h["Content-Type"] = "application/json"
        req = request.Request(self.server.url + path, data=payload,
                              method="POST" if body is not None else "GET",
                              headers=h)
        try:
            with request.urlopen(req, timeout=5) as reply:
                return reply.status, json.loads(reply.read().decode("utf-8"))
        except error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_http_and_mcp_capability_contract_are_equal_and_nonexecuting(self):
        status, body = self.fetch("/v1/agent/capabilities")
        self.assertEqual(status, 200)
        self.assertEqual(body, capabilities())
        self.assertFalse(body["execution_enabled"])
        self.assertTrue(all(row["agent_execution"] is False
                            for row in body["capabilities"]))

    def test_http_and_mcp_plan_share_exact_deterministic_contract(self):
        status, body = self.fetch("/v1/agent/plans", body=self.sample)
        self.assertEqual(status, 200)
        self.assertEqual(body, plan_request(self.sample))
        self.assertEqual(body["status"], "plan_only")
        self.assertFalse(body["execution_enabled"])
        self.assertNotIn(self.sample["prompt"], json.dumps(body))
        other_status, other_body = self.fetch("/v1/agent/plans", body=self.sample)
        self.assertEqual(other_status, 200)
        self.assertEqual(other_body["plan_id"], body["plan_id"])

    def test_missing_or_wrong_token_never_exposes_agent_plans(self):
        for headers in ({}, {"Authorization": "Bearer incorrect"}):
            with self.subTest(headers=headers):
                code, response = self.fetch(
                    "/v1/agent/plans", body=self.sample, headers=headers)
                self.assertEqual(code, 401)
                self.assertNotIn(self.sample["prompt"], json.dumps(response))
                code, response = self.fetch(
                    "/v1/agent/capabilities", headers=headers)
                self.assertEqual(code, 401)

    def test_malformed_extra_fields_and_path_attacks_fail_closed(self):
        for invalid in (
                dict(self.sample, command="del C:\\Windows"),
                dict(self.sample, model_id="../sneaky"),
                dict(self.sample, prompt=""),
                dict(self.sample, duration_seconds=0),
                dict(self.sample, seed=True),
                dict(self.sample, remote_url="https://example.invalid"),
        ):
            with self.subTest(bad=invalid):
                code, response = self.fetch("/v1/agent/plans", body=invalid)
                self.assertEqual(code, 400)
                if invalid.get("prompt"):
                    self.assertNotIn(invalid["prompt"], str(response))
        status, _ = self.fetch("/v1/agent/execute", body=self.sample)
        self.assertEqual(status, 404)

    def test_no_token_mode_is_disabled_for_agent_endpoints(self):
        anonymous = LocalApiServer(
            ForbiddenBackend(), port=0, token="", log=lambda _: None)
        anonymous.start()
        self.addCleanup(anonymous.stop)
        for method, path in (
                ("GET", "/v1/agent/capabilities"),
                ("POST", "/v1/agent/plans")):
            payload = json.dumps(self.sample).encode() if method == "POST" else None
            req = request.Request(anonymous.url + path, data=payload, method=method)
            with self.assertRaises(error.HTTPError) as response:
                request.urlopen(req, timeout=5)
            self.assertEqual(response.exception.code, 403)
        self.assertEqual(anonymous.backend.__class__, ForbiddenBackend)


if __name__ == "__main__":
    unittest.main()
