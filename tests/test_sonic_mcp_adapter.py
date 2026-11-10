"""Verify MCP adapter registration without downloading the optional SDK.

This checks tool wiring and fail-closed operations, but not SDK interoperability.
"""
import sys
import types
import unittest
from unittest.mock import patch

from this_voice_thing.integrations import sonic_mcp


class FakeMCPServer:
    def __init__(self, name, instructions=""):
        self.name = name
        self.instructions = instructions
        self.tools = {}

    def tool(self):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class McpWiringTests(unittest.TestCase):
    def build_fake(self):
        package = types.ModuleType("mcp")
        submodule = types.ModuleType("mcp.server")
        submodule.MCPServer = FakeMCPServer
        with patch.dict(sys.modules, {"mcp": package, "mcp.server": submodule}):
            return sonic_mcp.build_server()

    def test_only_four_readonly_tools_are_exposed(self):
        server = self.build_fake()
        self.assertEqual(set(server.tools), {
            "sonic_capabilities", "sonic_app_status",
            "sonic_voice_models", "sonic_plan_music",
        })
        self.assertIn("READ ONLY", server.instructions)
        self.assertFalse(server.tools["sonic_capabilities"]()["execution_enabled"])

    def test_plan_returns_digest_and_cannot_generate(self):
        server = self.build_fake()
        plan = server.tools["sonic_plan_music"]("ACE-Step/2B", "Original score", 30, 17, True)
        self.assertEqual(plan["status"], "plan_only")
        self.assertFalse(plan["execution_enabled"])
        self.assertNotIn("prompt", plan)
        rejected = server.tools["sonic_plan_music"]("../../private", "Original", 30, 0, True)
        self.assertEqual(rejected["status"], "rejected")
        self.assertFalse(rejected["execution_enabled"])

    def test_missing_token_reports_unavailable_not_traceback(self):
        server = self.build_fake()
        with patch.dict("os.environ", {"SONIC_RIFT_API_TOKEN": ""}):
            self.assertEqual(server.tools["sonic_app_status"]()["status"], "unavailable")
            self.assertEqual(server.tools["sonic_voice_models"]()["models"], [])


if __name__ == "__main__":
    unittest.main()
