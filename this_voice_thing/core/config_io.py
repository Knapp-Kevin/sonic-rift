"""Sonic Rift configuration-file I/O with explicit missing-file semantics.

No UI framework, audio engine, model registry or startup side effects belong
here. Higher-level callers decide whether missing configuration is an error.
"""
import json
from pathlib import Path


def read_json(path, *, missing_error=None, error_label=None):
    """Return (decoded value, diagnostic); never create or modify a file.

    When missing_error is None, a missing settings file is expected on fresh
    installs. Other read/parse failures always return a diagnostic string.
    """
    def failure(exc):
        what = error_label or f"'{path}'"
        return None, f"Failed to read {what}: {exc}"

    # Two steps, so a file that can't be read and a file that isn't JSON are both reported.
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, missing_error
    except (OSError, UnicodeError) as exc:
        return failure(exc)
    try:
        return json.loads(text), None
    except (ValueError, TypeError) as exc:
        return failure(exc)


def write_json(path, payload):
    """Write human-readable UTF-8 configuration without ASCII escaping.

    The caller owns backup/atomic-update requirements. This helper deliberately
    matches the current serialized format; it never moves existing user data.
    """
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
