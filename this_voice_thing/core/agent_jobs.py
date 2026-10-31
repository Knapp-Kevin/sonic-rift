"""Side-effect-free, versioned agent job planning for Sonic Rift.

This module deliberately imports no Qt, model, worker, or filesystem code.
An agent plan is NOT an authorization, reservation, or executable job.
"""

import hashlib
import json
import re

CONTRACT_VERSION = "0.1.0"
CAPABILITIES = {
    "speech.generate": ("Existing speech UI/API; MCP execution not enabled", "ui_only"),
    "sound.generate": ("Existing Sounds UI; MCP execution not enabled", "ui_only"),
    "music.generate": ("Music model and rights qualification pending #128", "research_only"),
}
_ALLOWED_FIELDS = frozenset({
    "kind", "model_id", "prompt", "duration_seconds", "seed", "instrumental",
})
_MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._/-]{0,95}\Z")
MAX_PROMPT_CHARS = 4000
MAX_DURATION_SECONDS = 600
MAX_SEED = 2 ** 32 - 1


class InvalidJob(ValueError):
    """Request failed closed before touching an app or model."""


def capabilities():
    """Describe capabilities without claiming an installed or active engine."""
    return {
        "contract_version": CONTRACT_VERSION,
        "control_plane": "read_only",
        "execution_enabled": False,
        "capabilities": [
            {"id": key, "status": status, "description": description,
             "agent_execution": False}
            for key, (description, status) in sorted(CAPABILITIES.items())
        ],
    }


def plan_request(request):
    """Validate a closed schema and return a digest, never the prompt or paths.

    Matching request digests represent identical *instructions*, not identical
    generated audio. Execution and user approval are separate future contracts.
    """
    if type(request) is not dict:
        raise InvalidJob("Request must be a JSON object.")
    unknown = set(request) - _ALLOWED_FIELDS
    if unknown:
        raise InvalidJob("Unsupported request fields.")
    kind = request.get("kind")
    if type(kind) is not str or kind not in CAPABILITIES:
        raise InvalidJob("Unknown generation capability.")
    model = request.get("model_id")
    if (type(model) is not str or not _MODEL_ID.fullmatch(model)
            or any(part in (".", "..") for part in model.split("/"))
            or "//" in model):
        raise InvalidJob("model_id must be a bounded model label, not a path or URL.")
    prompt = request.get("prompt")
    if (type(prompt) is not str or not prompt.strip()
            or len(prompt) > MAX_PROMPT_CHARS
            or any(ord(c) < 32 and c not in "\n\r\t" for c in prompt)):
        raise InvalidJob("prompt must be 1-4000 readable characters.")
    seconds = request.get("duration_seconds")
    if type(seconds) is not int or not 1 <= seconds <= MAX_DURATION_SECONDS:
        raise InvalidJob("duration_seconds must be an integer between 1 and 600.")
    seed = request.get("seed", 0)
    if type(seed) is not int or not 0 <= seed <= MAX_SEED:
        raise InvalidJob("seed must be an unsigned 32-bit integer.")
    instrumental = request.get("instrumental", True)
    if type(instrumental) is not bool:
        raise InvalidJob("instrumental must be true or false.")
    if kind != "music.generate" and "instrumental" in request:
        raise InvalidJob("instrumental is only valid for music generation.")
    normalized = {
        "contract_version": CONTRACT_VERSION,
        "kind": kind,
        "model_id": model,
        "prompt": prompt.strip(),
        "duration_seconds": seconds,
        "seed": seed,
    }
    if kind == "music.generate":
        normalized["instrumental"] = instrumental
    identity = json.dumps(normalized, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False).encode("utf-8")
    return {
        "plan_id": hashlib.sha256(identity).hexdigest(),
        "prompt_sha256": hashlib.sha256(normalized["prompt"].encode("utf-8")).hexdigest(),
        "kind": kind,
        "model_id": model,
        "duration_seconds": seconds,
        "seed": seed,
        "instrumental": instrumental if kind == "music.generate" else None,
        "prompt_chars": len(normalized["prompt"]),
        "status": "plan_only",
        "execution_enabled": False,
        "requires_authorized_execution": True,
        "model_installed": "unverified",
        "deterministic_output": "not_guaranteed",
    }
