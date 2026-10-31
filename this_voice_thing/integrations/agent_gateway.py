"""Fail-closed, read-only local API bridge for an optional MCP subprocess.

No arbitrary URL, path, file, subprocess, shell, engine or secret is exposed.
Do not use this as the transport for remote clients.
"""
import json
import os
from urllib import error, request

MAX_RESPONSE = 64 * 1024
TIMEOUT_SECONDS = 3


class GatewayUnavailable(RuntimeError):
    pass


class LocalGateway:
    def __init__(self, *, port=8765, token=None):
        if type(port) is not int or not 1 <= port <= 65535:
            raise GatewayUnavailable("Invalid loopback API port.")
        if token is None:
            token = os.environ.get("SONIC_RIFT_API_TOKEN", "")
        if type(token) is not str or not token.strip():
            raise GatewayUnavailable("Set SONIC_RIFT_API_TOKEN; unauthenticated MCP access is disabled.")
        self._url = f"http://127.0.0.1:{port}"
        self._token = token.strip()

    @classmethod
    def from_environment(cls):
        raw = os.environ.get("SONIC_RIFT_API_PORT", "8765")
        if not raw.isdecimal():
            raise GatewayUnavailable("SONIC_RIFT_API_PORT must be numeric.")
        return cls(port=int(raw))

    def _get(self, path, *, authenticated):
        if path not in ("/v1/health", "/v1/models"):
            raise GatewayUnavailable("Unsupported API endpoint.")
        headers = {"Accept": "application/json"}
        if authenticated:
            headers["Authorization"] = "Bearer " + self._token
        req = request.Request(self._url + path, headers=headers, method="GET")
        with request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise GatewayUnavailable("Unexpected local API response.")
            body = response.read(MAX_RESPONSE + 1)
            if len(body) > MAX_RESPONSE:
                raise GatewayUnavailable("Local API response exceeded the size limit.")
        value = json.loads(body.decode("utf-8"))
        if type(value) is not dict:
            raise GatewayUnavailable("Local API did not return an object.")
        return value

    def _require_real_auth(self):
        # The existing app can run its HTTP API with no token. Refuse that
        # configuration instead of passing an env token to an unprotected API.
        try:
            self._get("/v1/health", authenticated=False)
        except error.HTTPError as exc:
            if exc.code == 401:
                return
            raise GatewayUnavailable("Local API must require Bearer authentication.") from None
        except (error.URLError, TimeoutError, OSError, UnicodeError, ValueError, json.JSONDecodeError):
            raise GatewayUnavailable("Local API unavailable or not verifiably protected.") from None
        raise GatewayUnavailable("Local API allows anonymous requests; enable its token first.")

    def read(self, path):
        self._require_real_auth()
        try:
            return self._get(path, authenticated=True)
        except (error.HTTPError, error.URLError, TimeoutError, OSError, UnicodeError, ValueError):
            raise GatewayUnavailable("Authenticated local API request failed.") from None

    def health(self):
        value = self.read("/v1/health")
        return {
            "status": str(value.get("status") or "unknown")[:64],
            "loaded_model": str(value.get("model") or "")[:128],
            "device": str(value.get("device") or "")[:64],
        }

    def voice_models(self):
        value = self.read("/v1/models")
        data = value.get("data")
        if type(data) is not list:
            raise GatewayUnavailable("Local API models payload is invalid.")
        rows = []
        for item in data[:40]:
            if type(item) is not dict:
                raise GatewayUnavailable("Local API model entry is invalid.")
            rows.append({
                "id": str(item.get("id") or "")[:128],
                "engine": str(item.get("engine") or "")[:64],
                "capability": str(item.get("capability") or "")[:64],
                "installed": item.get("installed") is True,
                "loaded": item.get("loaded") is True,
            })
        return {"models": rows, "shown": len(rows), "truncated": len(data) > len(rows),
                "kind": "speech_and_voice_only"}
