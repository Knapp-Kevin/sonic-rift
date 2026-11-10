"""Optional AES-256-GCM sealed *private* forensic appendix for Sonic Rift.

The public C2PA Content Credential must remain independently readable.
This envelope only protects optional sensitive generation details associated
with an app-observed event. Keys MUST be provided by an owner-approved OS/KMS
key custodian and are never saved or returned by this module.

Prototype only: no user key custody, rotation, backup, retention or UI consent
has been approved. Not integrated into exports; no raw prompt goes public.
"""
import base64
import json
import os
import re

EVENT_ID = re.compile(r"[a-f0-9]{32}\Z")
DIGEST = re.compile(r"[a-f0-9]{64}\Z")
KEY_REF = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
FIELDS = frozenset(("generation_prompt", "negative_prompt", "model_settings",
                    "seed", "voice_reference_sha256", "source_license_note"))
ENVELOPE_FIELDS = frozenset((
    "schema_version", "encryption_alg", "key_reference",
    "event_id", "source_sha256", "nonce", "ciphertext",
))
MAX_PLAINTEXT_BYTES = 65536
MAX_CIPHER_B64 = 90000


class PrivateEvidenceInvalid(ValueError):
    """Invalid private data or inaccessible authenticated evidence."""


def _ids(event_id, source_sha256, key_reference):
    if (type(event_id) is not str or EVENT_ID.fullmatch(event_id) is None
            or type(source_sha256) is not str or DIGEST.fullmatch(source_sha256) is None
            or type(key_reference) is not str
            or KEY_REF.fullmatch(key_reference) is None):
        raise PrivateEvidenceInvalid("Invalid forensic binding identifiers")


def _key(key):
    if type(key) is not bytes or len(key) != 32:
        raise PrivateEvidenceInvalid("A 256-bit owner-managed encryption key is required")


def _aad(event_id, source_sha256, key_reference):
    payload = {
        "event_id": event_id, "source_sha256": source_sha256,
        "key_reference": key_reference, "schema_version": 1,
    }
    return (b"sonic-rift-private-evidence-v1\0"
            + json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii"))


def _validate_details(details):
    if type(details) is not dict or not details or set(details) - FIELDS:
        raise PrivateEvidenceInvalid("Invalid private evidence fields")
    for name, value in details.items():
        if name in ("generation_prompt", "negative_prompt", "source_license_note"):
            if type(value) is not str or len(value) > 4000:
                raise PrivateEvidenceInvalid("Invalid bounded private text")
        elif name == "seed":
            if type(value) is not int or not 0 <= value < (1 << 32):
                raise PrivateEvidenceInvalid("Invalid source seed")
        elif name == "voice_reference_sha256":
            if type(value) is not str or DIGEST.fullmatch(value) is None:
                raise PrivateEvidenceInvalid("Invalid voice reference digest")
        elif name == "model_settings" and type(value) is not dict:
            raise PrivateEvidenceInvalid("Invalid model settings")
    try:
        raw = json.dumps(details, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, OverflowError) as exc:
        raise PrivateEvidenceInvalid("Private evidence is not valid JSON") from exc
    if len(raw) > MAX_PLAINTEXT_BYTES:
        raise PrivateEvidenceInvalid("Private evidence exceeds size limit")
    return raw


def seal_private_evidence(details, *, event_id, source_sha256, key_reference, key):
    """Authenticated encryption with a fresh random 96-bit nonce per record."""
    _ids(event_id, source_sha256, key_reference)
    _key(key)
    plaintext = _validate_details(details)
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = os.urandom(12)
    cipher = AESGCM(key).encrypt(
        nonce, plaintext, _aad(event_id, source_sha256, key_reference))
    return {
        "schema_version": 1,
        "encryption_alg": "AES-256-GCM",
        "key_reference": key_reference,
        "event_id": event_id,
        "source_sha256": source_sha256,
        "nonce": base64.urlsafe_b64encode(nonce).decode("ascii"),
        "ciphertext": base64.urlsafe_b64encode(cipher).decode("ascii"),
    }


def open_private_evidence(envelope, *, event_id, source_sha256, key_reference, key):
    """Reject changed ciphertext, IDs, nonce, keys or provenance context."""
    _ids(event_id, source_sha256, key_reference)
    _key(key)
    if (type(envelope) is not dict or set(envelope) != ENVELOPE_FIELDS
            or type(envelope["schema_version"]) is not int
            or envelope["schema_version"] != 1
            or envelope["encryption_alg"] != "AES-256-GCM"
            or envelope["event_id"] != event_id
            or envelope["source_sha256"] != source_sha256
            or envelope["key_reference"] != key_reference):
        raise PrivateEvidenceInvalid("Sealed evidence does not match expected source")
    for field in ("nonce", "ciphertext"):
        if (type(envelope[field]) is not str
                or len(envelope[field]) > MAX_CIPHER_B64
                or not envelope[field]):
            raise PrivateEvidenceInvalid("Malformed private evidence encoding")
    try:
        nonce = base64.b64decode(envelope["nonce"], altchars=b"-_", validate=True)
        cipher = base64.b64decode(envelope["ciphertext"], altchars=b"-_", validate=True)
        if len(nonce) != 12 or not 16 <= len(cipher) <= MAX_PLAINTEXT_BYTES + 16:
            raise PrivateEvidenceInvalid("Invalid authenticated-encryption size")
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        data = AESGCM(key).decrypt(
            nonce, cipher, _aad(event_id, source_sha256, key_reference))
        details = json.loads(data)
        if _validate_details(details) != data:
            # Enforce canonical serialization, not ambiguous JSON encodings.
            raise PrivateEvidenceInvalid("Private evidence has invalid encoding")
        return details
    except PrivateEvidenceInvalid:
        raise
    except Exception as exc:
        # Do not echo cryptography or plaintext errors into MCP/API responses.
        raise PrivateEvidenceInvalid("Private evidence authentication failed") from None
