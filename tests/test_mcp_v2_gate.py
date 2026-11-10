"""No-SDK regression checks for the v2 MCP interoperability gate runner."""
from pathlib import Path
import asyncio
import json
import runpy
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

CHECKS = runpy.run_path(str(
    Path(__file__).resolve().parents[1] / "scripts" / "qualify_mcp_stage_a_v2.py"
))


def result(payload):
    return SimpleNamespace(structured_content=payload, content=[], is_error=False)


class McpGateTests(unittest.IsolatedAsyncioTestCase):
    def test_accepts_only_all_four_read_only_tools_and_deterministic_plan(self):
        expected = CHECKS["EXPECTED_TOOLS"]
        calls = {
            "sonic_capabilities": result({
                "execution_enabled": False,
                "capabilities": [{"agent_execution": False}]}),
            "sonic_plan_music": result({
                "plan_id": "a" * 64, "execution_enabled": False,
                "status": "plan_only"}),
            "sonic_app_status": result({"status": "ready"}),
            "sonic_voice_models": result({"models": []}),
        }
        async def call(name, kwargs):
            if name == "sonic_plan_music" and kwargs.get("duration_seconds") == -10:
                return result({"status": "rejected", "execution_enabled": False})
            return calls[name]
        client = SimpleNamespace(
            list_tools=AsyncMock(return_value=SimpleNamespace(
                tools=[SimpleNamespace(name=n) for n in sorted(expected)])),
            call_tool=call)
        check = await CHECKS["_check"](client, require_app=False)
        self.assertEqual(check["registered_tools"], sorted(expected))
        self.assertTrue(check["plan_stable"])
        self.assertFalse(check["audio_generated"])
        self.assertFalse(check["c2pa_signed"])

    def test_rejects_extra_tools_or_secret_plan_echo(self):
        extra = CHECKS["EXPECTED_TOOLS"] | {"sonic_execute_shell"}
        client = SimpleNamespace(
            list_tools=AsyncMock(return_value=SimpleNamespace(
                tools=[SimpleNamespace(name=n) for n in sorted(extra)])),
            call_tool=AsyncMock())
        with self.assertRaisesRegex(ValueError, "tool set"):
            await CHECKS["_check"](client, require_app=False)

    def test_structured_response_and_legacy_text_fallback(self):
        parse = CHECKS["_result_dict"]
        self.assertEqual(parse(result({"result": {"ok": True}})), {"ok": True})
        content = [SimpleNamespace(text=json.dumps({"ok": True}))]
        self.assertEqual(parse(SimpleNamespace(structured_content=None, content=content)),
                         {"ok": True})
        with self.assertRaisesRegex(ValueError, "no typed object"):
            parse(SimpleNamespace(structured_content=None, content=[]))


if __name__ == "__main__":
    unittest.main()
