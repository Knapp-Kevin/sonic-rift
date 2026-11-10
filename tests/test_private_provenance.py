"""Private provenance envelope: authenticated, source-bound and not public C2PA."""
from copy import deepcopy
import importlib.util
import json
import os
import unittest

from this_voice_thing.core.private_provenance import (
    PrivateEvidenceInvalid, seal_private_evidence, open_private_evidence,
)

EVENT = "c" * 32
SOURCE = "d" * 64
KEY_REF = "owner-key-v1"


@unittest.skipUnless(importlib.util.find_spec("cryptography"),
                     "approved cryptography library not installed")
class PrivateEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.key = os.urandom(32)
        self.details = {
            "generation_prompt": "private lyrics and studio prompts",
            "seed": 12345,
            "model_settings": {"guidance_scale": 5.0, "steps": 20},
        }
        self.args = {
            "event_id": EVENT,
            "source_sha256": SOURCE,
            "key_reference": KEY_REF,
            "key": self.key,
        }

    def seal(self):
        return seal_private_evidence(self.details, **self.args)

    def test_roundtrip_and_no_plaintext_in_json_envelope(self):
        envelope = self.seal()
        self.assertEqual(envelope["encryption_alg"], "AES-256-GCM")
        self.assertEqual(envelope["schema_version"], 1)
        self.assertNotIn("private lyrics", json.dumps(envelope))
        self.assertNotIn("guidance_scale", json.dumps(envelope))
        self.assertEqual(open_private_evidence(envelope, **self.args), self.details)
        self.assertNotIn("private_key", envelope)

    def test_two_seals_use_distinct_nonces_and_ciphertext(self):
        first, second = self.seal(), self.seal()
        self.assertNotEqual(first["nonce"], second["nonce"])
        self.assertNotEqual(first["ciphertext"], second["ciphertext"])
        self.assertEqual(open_private_evidence(first, **self.args),
                         open_private_evidence(second, **self.args))

    def test_wrong_key_or_context_fails_authentication(self):
        envelope = self.seal()
        for changes in ({"key": os.urandom(32)},
                        {"event_id": "e" * 32},
                        {"source_sha256": "e" * 64},
                        {"key_reference": "other-key"}):
            with self.subTest(changes=list(changes)):
                with self.assertRaises(PrivateEvidenceInvalid):
                    open_private_evidence(envelope, **{**self.args, **changes})

    def test_tampered_nonce_ciphertext_and_schema_fail(self):
        envelope = self.seal()
        for field, replacement in (
                ("nonce", "AAAAAAAAAAAAAAAA"),
                ("ciphertext", "AAAAAAAAAAAA"),
                ("encryption_alg", "AES-ECB"),
                ("schema_version", 2)):
            changed = deepcopy(envelope)
            changed[field] = replacement
            with self.subTest(field=field), self.assertRaises(PrivateEvidenceInvalid):
                open_private_evidence(changed, **self.args)

    def test_refuses_unbounded_or_sensitive_unknown_fields(self):
        for bad in (
                {"username": "never-capture-private-identity"},
                {"generation_prompt": "x" * 5000},
                {"seed": -1},
                {"seed": True},
                {"model_settings": {"invalid": float("nan")}},
                {}):
            with self.subTest(details=str(list(bad))):
                with self.assertRaises(PrivateEvidenceInvalid):
                    seal_private_evidence(bad, **self.args)

    def test_refuses_missing_key_without_plaintext_fallback(self):
        with self.assertRaisesRegex(PrivateEvidenceInvalid, "256-bit"):
            seal_private_evidence(self.details, **{**self.args, "key": b""})
        with self.assertRaises(PrivateEvidenceInvalid):
            seal_private_evidence(self.details, **{
                **self.args, "event_id": "../../path"})


if __name__ == "__main__":
    unittest.main()
