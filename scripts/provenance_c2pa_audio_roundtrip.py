"""Opt-in C2PA audio **test-signing** round-trip, never a release signer.

Requires externally provisioned disposable ES256 lab cert/key and a separately
qualified c2pa-python native SDK. Never installs SDKs, creates keys, mutates
source audio or claims public issuer trust. This is an *interop probe* for
WAV/MP3/OGG capabilities, embedding and decoded-signal parity. The manifest
is deliberately a generic test creation claim, NOT a multi-model disclosure.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import tempfile

MIME = {
    "wav": ("audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave"),
    "mp3": ("audio/mpeg", "audio/mp3"),
    "ogg": ("audio/ogg", "application/ogg", "audio/vorbis"),
}
MAX_BYTES = 256 * 1024 * 1024


class RoundtripBlocked(ValueError):
    pass


def _digest_file(path):
    result = hashlib.sha256()
    with path.open("rb") as reader:
        for block in iter(lambda: reader.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _safe_file(path, name):
    if path.is_symlink() or not path.is_file():
        raise RoundtripBlocked(name + " must be a regular non-linked file")
    if path.stat().st_size > MAX_BYTES:
        raise RoundtripBlocked(name + " exceeds bounded size")


def generic_test_manifest(mime):
    """C2PA spec-compatible creation assertion; DOES NOT claim AI provenance."""
    return {
        "claim_generator_info": [{"name": "Sonic Rift format qualification",
                                  "version": "0.0-test-only"}],
        "format": mime,
        "title": "Sonic Rift disposable C2PA format fixture",
        "ingredients": [],
        "assertions": [{
            "label": "c2pa.actions",
            "data": {"actions": [{
                "action": "c2pa.created",
                "digitalSourceType":
                    "http://cv.iptc.org/newscodes/digitalsourcetype/digitalCreation",
            }]},
        }],
    }


def compare_decoded_audio(original, signed, suffix):
    """Check that inserting metadata does not alter actual audio samples."""
    import numpy as np
    import soundfile as sf

    before, before_rate = sf.read(original, always_2d=True, dtype="float32")
    after, after_rate = sf.read(signed, always_2d=True, dtype="float32")
    if before_rate != after_rate or before.shape != after.shape:
        raise RoundtripBlocked("Signed file changes sample rate, channels or duration")
    if suffix == "wav":
        np.testing.assert_array_equal(before, after)
    else:
        # Both files must already use the same lossy codec: metadata insertion
        # should not trigger re-encoding or meaningful decoded-signal changes.
        np.testing.assert_allclose(before, after, atol=1e-6, rtol=0)
    return {"sample_rate": int(before_rate), "frames": int(before.shape[0]),
            "channels": int(before.shape[1]), "decoded_audio_equal": True}


def qualify(*, source, output_dir, test_cert, test_key):
    import c2pa  # optional native library, imported only in explicit test mode

    source = Path(source)
    destination_dir = Path(output_dir)
    if source.is_symlink() or destination_dir.is_symlink():
        raise RoundtripBlocked("Linked source or output directory is not permitted")
    source = source.resolve(strict=True)
    destination_dir = destination_dir.resolve(strict=True)
    if not destination_dir.is_dir():
        raise RoundtripBlocked("Output directory must be an existing directory")
    suffix = source.suffix.lower().lstrip(".")
    if suffix not in MIME:
        raise RoundtripBlocked("Only wav/mp3/ogg test fixtures are supported")
    _safe_file(source, "Source")
    cert = Path(test_cert)
    key = Path(test_key)
    if cert.is_symlink() or key.is_symlink():
        raise RoundtripBlocked("Linked test credentials are not accepted")
    cert = cert.resolve(strict=True)
    key = key.resolve(strict=True)
    _safe_file(cert, "Test certificate")
    _safe_file(key, "Test private key")
    if source.parent == destination_dir:
        raise RoundtripBlocked("Output directory must be separate from input")
    reader_mimes = set(c2pa.Reader.get_supported_mime_types())
    builder_mimes = set(c2pa.Builder.get_supported_mime_types())
    choices = MIME[suffix]
    suitable = next((mime for mime in choices
                     if mime in reader_mimes and mime in builder_mimes), None)
    if suitable is None:
        raise RoundtripBlocked("Installed SDK cannot both sign and read this audio format")

    final = destination_dir / ("sonic-c2pa-lab-" + source.name)
    if final.exists() or final.is_symlink():
        raise RoundtripBlocked("Refusing to replace an existing test output")
    temp = None
    result = None
    initial_sha = _digest_file(source)
    try:
        with tempfile.NamedTemporaryFile(
                dir=destination_dir, prefix=".c2pa-test-",
                suffix=source.suffix, delete=False) as holder:
            temp = Path(holder.name)
        # Production use requires a secure hardware/OS-backed key provider,
        # explicitly owner-approved issuer and independent validator. This
        # lab-only signer reads disposable test credentials provided by user.
        signer_info = c2pa.C2paSignerInfo(
            alg=c2pa.C2paSigningAlg.ES256,
            sign_cert=cert.read_bytes(),
            private_key=key.read_bytes(),
            ta_url=None,
        )
        with c2pa.Signer.from_info(signer_info) as signer:
            with c2pa.Builder(generic_test_manifest(suitable)) as builder:
                builder.sign_file(source, temp, signer)
        with c2pa.Reader(temp) as reader:
            if not reader.is_embedded():
                raise RoundtripBlocked("C2PA manifest was not embedded in the audio")
            manifest = json.loads(reader.json())
            if not manifest.get("active_manifest"):
                raise RoundtripBlocked("Signed file has no active Content Credential")
            validation_state = reader.get_validation_state()
        if temp.stat().st_size > MAX_BYTES + (1024 * 1024):
            raise RoundtripBlocked("Signed output exceeds bounded file size")
        parity = compare_decoded_audio(source, temp, suffix)
        if _digest_file(source) != initial_sha:
            raise RoundtripBlocked("Input audio changed during signing")
        output_sha256 = _digest_file(temp)
        native_version = c2pa.sdk_version()
        package_version = importlib.metadata.version("c2pa-python")
        result = {
            "status": "LAB_EMBEDDED_UNTRUSTED_PROOF_ONLY",
            "sdk_package_version": package_version,
            "native_sdk_version": native_version,
            "format": suffix,
            "mime": suitable,
            "test_file": final.name,
            "output_sha256": output_sha256,
            "source_unchanged": True,
            "c2pa_embedded": True,
            "reported_validation_state": validation_state,
            "independent_validator": "NOT_RUN",
            "issuer_publicly_trusted": False,
            "ai_provenance_claimed": False,
            "production_release_qualified": False,
            **parity,
        }
        # Same-directory hardlink is an exclusive, no-overwrite promotion.
        # All checks and receipt generation finish *before* publication.
        # Unsupported or unusual Windows filesystems must fail closed.
        os.link(temp, final)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()
    return result


def main():
    parser = argparse.ArgumentParser(
        description="C2PA lab-format probe; no public-trust or real AI-origin claim")
    parser.add_argument("--test-only", action="store_true", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--test-cert", required=True)
    parser.add_argument("--test-key", required=True)
    args = parser.parse_args()
    try:
        output = qualify(source=args.source, output_dir=args.output_dir,
                         test_cert=args.test_cert, test_key=args.test_key)
    except Exception as exc:
        # Never print keys, full paths, native error text or user media details.
        output = {"status": "LAB_NO_GO", "failure_type": type(exc).__name__,
                  "production_release_qualified": False}
    print(json.dumps(output, sort_keys=True, indent=2))
    return 0 if output["status"] == "LAB_EMBEDDED_UNTRUSTED_PROOF_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
