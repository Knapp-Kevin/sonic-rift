"""Local MCP v2 stdio adapter: discovery and planning only.

The agent process never imports models or PySide6 and cannot start a job.
Requires the optional official MCP Python SDK v2 in a separate environment.
"""
from this_voice_thing.core.agent_jobs import InvalidJob, capabilities, plan_request
from this_voice_thing.integrations.agent_gateway import GatewayUnavailable, LocalGateway


def build_server():
    # Import lazily; normal Sonic Rift app setup does not install the MCP SDK.
    from mcp.server import MCPServer

    server = MCPServer("Sonic Rift", instructions=(
        "READ ONLY: no model inference, installation, file operations or project edits. "
        "Use sonic_capabilities and sonic_voice_models to discover; sonic_plan_music "
        "only validates a proposed request and never executes it. Do not assume a "
        "plan is authorization or a reservation. Never submit secrets in a prompt."
    ))

    @server.tool()
    def sonic_capabilities() -> dict:
        """List bounded agent capabilities, including explicitly disabled execution."""
        return capabilities()

    @server.tool()
    def sonic_app_status() -> dict:
        """Return only compact state of the existing authenticated local app."""
        try:
            return LocalGateway.from_environment().health()
        except GatewayUnavailable as exc:
            return {"status": "unavailable", "reason": str(exc)}

    @server.tool()
    def sonic_voice_models() -> dict:
        """List locally configured speech models. Does not install or load them."""
        try:
            return LocalGateway.from_environment().voice_models()
        except GatewayUnavailable as exc:
            return {"models": [], "status": "unavailable", "reason": str(exc)}

    @server.tool()
    def sonic_plan_music(model_id: str, prompt: str,
                         duration_seconds: int = 30, seed: int = 0,
                         instrumental: bool = True) -> dict:
        """Validate a proposed music job and return a digest; never generate."""
        try:
            return plan_request({
                "kind": "music.generate",
                "model_id": model_id,
                "prompt": prompt,
                "duration_seconds": duration_seconds,
                "seed": seed,
                "instrumental": instrumental,
            })
        except InvalidJob as exc:
            return {"status": "rejected", "execution_enabled": False, "reason": str(exc)}

    return server


if __name__ == "__main__":
    build_server().run(transport="stdio")
