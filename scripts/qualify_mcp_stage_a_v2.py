"""Sonic Rift MCP v2 *real stdio* interoperability qualification.

Requires the official, separately installed MCP SDK v2.3.0 and a source checkout.
Does not install dependencies, start a generator or authorize write operations.
Success proves Stage A protocol and read-only tool behavior only, NOT v1 RC.
"""
import argparse
import asyncio
import importlib.metadata
import json
import os
import secrets
import sys

EXPECTED_TOOLS = {
    "sonic_capabilities", "sonic_app_status",
    "sonic_voice_models", "sonic_plan_music",
}
SDK_PIN = "2.3.0"


def _result_dict(result):
    value = getattr(result, "structured_content", None)
    if type(value) is dict:
        if set(value) == {"result"} and type(value["result"]) is dict:
            return value["result"]
        return value
    # Some SDK versions return a JSON-serialized TextContent instead.
    for block in getattr(result, "content", ()):
        text = getattr(block, "text", None)
        if type(text) is str:
            try:
                value = json.loads(text)
            except ValueError:
                continue
            if type(value) is dict:
                return value
    raise ValueError("Server returned no typed object")


async def _check(client, *, require_app):
    listing = await asyncio.wait_for(client.list_tools(), timeout=20)
    names = {tool.name for tool in listing.tools}
    if names != EXPECTED_TOOLS:
        raise ValueError("Unexpected MCP tool set: refuse extra or missing tools")

    caps = await asyncio.wait_for(client.call_tool("sonic_capabilities", {}), timeout=20)
    if caps.is_error:
        raise ValueError("Capabilities tool failed")
    info = _result_dict(caps)
    if info.get("execution_enabled") is not False:
        raise ValueError("MCP Stage A advertises an unsafe execution mode")
    rows = info.get("capabilities")
    if type(rows) is not list or any(
            type(item) is not dict or item.get("agent_execution") is not False
            for item in rows):
        raise ValueError("MCP reported an unreviewed execution capability")

    args = {"model_id": "ACE-Step/Ace-Step1.5", "prompt": "test fixture only",
            "duration_seconds": 8, "seed": 123, "instrumental": True}
    first = _result_dict(await asyncio.wait_for(
        client.call_tool("sonic_plan_music", args), timeout=20))
    second = _result_dict(await asyncio.wait_for(
        client.call_tool("sonic_plan_music", args), timeout=20))
    if (first.get("plan_id") != second.get("plan_id")
            or first.get("status") != "plan_only"
            or first.get("execution_enabled") is not False
            or args["prompt"] in str(first)):
        raise ValueError("MCP planning failed determinism or confidentiality")

    invalid = dict(args, duration_seconds=-10)
    refused = _result_dict(await asyncio.wait_for(
        client.call_tool("sonic_plan_music", invalid), timeout=20))
    if refused.get("status") != "rejected":
        raise ValueError("MCP did not reject invalid job input")

    status = _result_dict(await asyncio.wait_for(
        client.call_tool("sonic_app_status", {}), timeout=20))
    models = _result_dict(await asyncio.wait_for(
        client.call_tool("sonic_voice_models", {}), timeout=20))
    if require_app and (
            status.get("status") == "unavailable"
            or models.get("status") == "unavailable"):
        raise ValueError("Protected real Sonic Rift app is unavailable")
    if "status" not in status or type(models.get("models")) is not list:
        raise ValueError("MCP app discovery payload invalid")

    return {
        "registered_tools": sorted(names),
        "plan_stable": True,
        "invalid_job_rejected": True,
        "app_checked": bool(require_app),
        "live_app_status": status.get("status", "unknown") if require_app else "not_required",
        "audio_generated": False,
        "c2pa_signed": False,
    }


async def run(require_app):
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["HF_HUB_OFFLINE"] = "1"
    environment["TRANSFORMERS_OFFLINE"] = "1"
    if not require_app:
        # Refuse any live service to make standalone discovery/plan proof safe.
        environment["SONIC_RIFT_API_PORT"] = "1"
        environment["SONIC_RIFT_API_TOKEN"] = secrets.token_urlsafe(32)
    elif not os.environ.get("SONIC_RIFT_API_TOKEN"):
        raise ValueError("Protected app mode requires SONIC_RIFT_API_TOKEN")
    command = StdioServerParameters(
        command=sys.executable,
        args=["-m", "this_voice_thing.integrations.sonic_mcp"],
        env=environment,
    )
    async with Client(command, read_timeout_seconds=20) as client:
        return await asyncio.wait_for(_check(client, require_app=require_app), timeout=90)


def main():
    parser = argparse.ArgumentParser(description="Verify official v2 MCP stdio handshake")
    parser.add_argument("--require-app", action="store_true",
                        help="Also prove authenticated read access to a live Sonic Rift app")
    args = parser.parse_args()
    receipt = {"contract": "sonic-rift-mcp-stage-a-stdio/v1",
               "status": "NO_GO", "sdk_pin": SDK_PIN,
               "checks": {}, "note": "Protocol proof, not signed provenance or model execution."}
    try:
        actual = importlib.metadata.version("mcp")
        receipt["sdk_installed"] = actual
        if actual != SDK_PIN:
            raise ValueError("MCP SDK does not match pinned interoperability version")
        receipt["checks"] = asyncio.run(run(args.require_app))
        receipt["status"] = ("APP_AUTH_AND_MCP_STAGE_A_PROVED" if args.require_app
                             else "STDIO_STAGE_A_PROVED_APP_NOT_TESTED")
    except Exception as exc:
        # Do not print exceptions from transports, which may include secrets.
        receipt["failure_type"] = type(exc).__name__
    print(json.dumps(receipt, sort_keys=True, indent=2))
    return 0 if receipt["status"] != "NO_GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
