"""Read-only installed C2PA Python/native SDK capability probe.

No installs, network access, test keys, signatures, file mutations or secrets.
The native builder/reader format lists are a *preflight*, not a round-trip test.
"""
import importlib.metadata
import json
import platform
import sys


AUDIO_CANDIDATES = {
    "wav": ("audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave"),
    "mp3": ("audio/mpeg", "audio/mp3"),
    "ogg": ("audio/ogg", "application/ogg", "audio/vorbis"),
}


def capability_report(c2pa):
    """Inspect exactly what this native wheel advertises, without signing."""
    reader = sorted(set(c2pa.Reader.get_supported_mime_types()))
    builder = sorted(set(c2pa.Builder.get_supported_mime_types()))
    supported = {}
    for fmt, possible_mimes in AUDIO_CANDIDATES.items():
        supported[fmt] = {
            "reader": any(mime in reader for mime in possible_mimes),
            "builder": any(mime in builder for mime in possible_mimes),
        }
    native = getattr(c2pa, "sdk_version", None)
    return {
        "status": "probe_only_not_qualified",
        "native_sdk_version": native() if callable(native) else None,
        "reader_mime_types": reader,
        "builder_mime_types": builder,
        "audio_format_candidates": supported,
        "warning": "MIME capability listing does not prove working audio embedding, trusted signing, or decoded PCM parity.",
    }


def main():
    result = {
        "contract": "sonic-rift-c2pa-sdk-capability-probe-v1",
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "status": "SDK_UNAVAILABLE",
        "c2pa_python_version": None,
    }
    try:
        import c2pa  # optional dependency, intentionally not auto-installed
    except ImportError:
        result["reason"] = "c2pa-python is not installed; do not claim support"
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2

    try:
        result["c2pa_python_version"] = importlib.metadata.version("c2pa-python")
        result.update(capability_report(c2pa))
        result["status"] = "PROBED_NOT_QUALIFIED"
    except (Exception,) as exc:
        result["status"] = "SDK_PROBE_FAILED"
        result["error_type"] = type(exc).__name__
        result["reason"] = "Native SDK capability query failed"
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PROBED_NOT_QUALIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
