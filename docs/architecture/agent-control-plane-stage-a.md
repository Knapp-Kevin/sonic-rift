# Sonic Rift Agent Control Plane: Stage A, read-only MCP prototype

**Status: implementation candidate, NOT Windows/MCP-client qualified.**  
**Branch:** `feature/agent-control-plane-readonly-mcp-20261031-no-ci`  
**Baseline:** `main` `28bc39e` (October 31, 2026).  
**Tracking:** [#130](https://github.com/Knapp-Kevin/sonic-rift/issues/130) · [Music #128](https://github.com/Knapp-Kevin/sonic-rift/issues/128) · [Windows #61](https://github.com/Knapp-Kevin/sonic-rift/issues/61).

## Principle

An AI agent is a **director**, not a shell with GPU privileges. Sonic Rift is the trusted executor of exact typed jobs. A deterministic plan hash identifies identical request *intent*, not a guarantee of bit-identical music across model versions, seeds, platforms or hardware. The agent reads concise receipts and authorized previews, not raw megabyte audio streams. UI, Local API and future MCP all pass through the *same* resource-ownership, authorization and artifact services.

Stage A implements only discovery and side-effect-free request planning. It cannot install, generate, edit, export, transcribe, delete, arbitrarily read a path or inspect user voices. **Nothing in this branch adds generation to MCP.** The existing UI/local HTTP API remains independent.

## Real first-slice code

| Module | Role |
| --- | --- |
| `this_voice_thing/core/agent_jobs.py` | Independent stdlib request contract, 0.1.0; known capabilities, strict bounds, fail-closed field validation, canonical SHA-256 intent ID, prompt hash and compact plan. Returns no prompt text. |
| `this_voice_thing/integrations/agent_gateway.py` | Loopback-only client for pre-existing `GET /v1/health` and `GET /v1/models`; requires `SONIC_RIFT_API_TOKEN`, **tests that the app rejects anonymous reads**, limits payload bytes and removes private/sensitive response fields. Does not accept a caller-provided URL. |
| `this_voice_thing/integrations/sonic_mcp.py` | Optional official Python SDK v2 stdio MCP adapter with four tools: `sonic_capabilities`, `sonic_app_status`, `sonic_voice_models`, `sonic_plan_music`. SDK is lazy-imported. No Qt/model/GPU work in the MCP subprocess. |
| `tests/test_agent_jobs.py`, `tests/test_agent_gateway.py` | Stdlib contract and adversarial tests: no arbitrary paths or commands, schema and type limits, deterministic plan identity, no prompt echo, token required, anonymous service rejection, loopback-only URL and bounded metadata. |

**Important current limitation:** the app's existing Local API permits no-token mode. Stage A refuses MCP catalog/status in that configuration even if a token is supplied on the agent side. Configure a non-empty API token *in Sonic Rift Settings*, then pass the same value to the agent MCP process via its private environment. A token set only in the agent's environment does not secure the app. Never commit a token or put it on the command line.

## Local host setup and acceptance (once exact SDK is pinned)

1. Create a separate **optional MCP-only Python 3.11+ environment**. The host application requirements and all speech-engine venvs must not be altered. Install the official `mcp` **2.x** SDK *within that venv only*, then freeze its full dependency lock before claiming reproducibility. The code targets [the v2 server API](https://py.sdk.modelcontextprotocol.io/), not v1 or legacy SSE.
2. In the Sonic Rift UI, explicitly enable the existing loopback local API on the desired port with a strong bearer token. Save securely per local host's approved mechanism; do not log it. The MCP host must launch `python -m this_voice_thing.integrations.sonic_mcp` with cwd set to this repository, with environment variables `SONIC_RIFT_API_TOKEN` and (if not default) `SONIC_RIFT_API_PORT`. No special shell script, filesystem permissions or cloud endpoint is installed by this branch.
3. Connect a real local STDIO MCP host (Claude Desktop/Code, or desktop Codex where supported), verify the four declared tools and results. First verify that a no-token/unprotected API is REFUSED, then verify protected catalog/status, offline/unavailable handling, malformed plan rejection, and repeated plan IDs. Tool calls must not alter model state, create files or use GPU.
4. Run `python -m unittest -v tests.test_agent_jobs tests.test_agent_gateway` and `python -m unittest discover -s tests` on the **exact branch head** in a separate Windows worktree/profile. Confirm unchanged owner data/media and no Actions runs.
5. Only then mark Stage A protocol interoperability GO. **It is not GO for enabling write tools.** Remote access, OAuth and the Secure MCP Tunnel are a separate owner-authorized security track.

## Host compatibility and boundaries

- **Local desktop agents:** STDIO subprocess works without making a network-listening MCP server. Standard SDK handles MCP 2026-07-28 protocol semantics; client tests still needed.
- **Hosted ChatGPT:** it cannot directly reach your local `127.0.0.1` MCP process. Supported custom MCP integrations use **public HTTPS or Secure MCP Tunnel** with workspace/plan permissions. Do not open the app's legacy HTTP port to the internet, turn off token checks or claim direct cloud access. See [OpenAI custom MCP](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt) and [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).
- **Model/context budget:** local models consume local GPU and electricity, not hosted inference tokens; Claude/ChatGPT planning and feedback still consume their own context/tool tokens. Return handles, hashes and concise results by default, not waveforms or full prompts.
- **No connection-level trust:** MCP protocol sessions and process connections must not grant standing authorization to edit a project; authority must be bound to a scope, authenticated caller, specific request, expiry and optimistic revision. Current Stage A has **no mutation authority**.
- **Existing HTTP API:** has synthesis endpoints that write generated files and can run with an empty token. Never make those write endpoints available to MCP by a raw generic proxy. Stage B must add independent server-side authorization and job custody first.

## Follow-on work (not included here)

1. **Stage B** app-owned job queue and scheduling with bounded active jobs, per-provider GPU leases shared with GUI/API, model and cache registration, resource/quota validation, idempotency keys, lifecycle/timeout, true cancel and durable receipts. The existing Engine WorkerProcess serializes *its own* JSONL requests but is not a cross-provider durable scheduler.
2. **Stage C** consented execution tools: `submit_generation(plan_id, authorization)`, `job_status(id)`, `cancel_job(id)`, `artifact_inspect(id)`. Avoid dumping prompts or local file paths to a cloud agent. No arbitrary raw-output export.
3. **Stage D** safe `studio_import(asset_id, project_id, expected_revision)` and `studio_export(project_id, expected_revision, format)`, using existing `ProjectSession` and bounded mixer; fail on stale projects, protect source files and require explicit owner grants.
4. **Stage E** music ACE-Step/Stable Audio music worker adapter only after [#128](https://github.com/Knapp-Kevin/sonic-rift/issues/128) model/rights/Windows bench approval, plus real full-chain test across Music + Speech + Sounds into Studio, owner listening, export hashes, empty/negative tests and local token/VRAM accounting.

## Security / release NO-GO boundaries

No SDK/client handshake, environment installation, live generation, Windows regression or owner runtime test was performed simply by committing these source files. Releasing the adapter, accepting untrusted agents, mounting arbitrary directories, installing weights or exposing external HTTP before these gates would be a security and governance failure. Keep PR draft until exact-head tests and protocol handshake, and retain source-rights requirements under #55/#60 and normal Windows acceptance under #61.
