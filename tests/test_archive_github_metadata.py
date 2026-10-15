"""Offline contract tests for non-destructive GitHub metadata archive."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "archive_github_metadata.py"
spec = importlib.util.spec_from_file_location("sonic_rift_archiver", SCRIPT)
archiver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archiver)


class FakeReader:
    def __init__(self):
        self.calls = []

    def get(self, endpoint, params=None):
        self.calls.append((endpoint, params))
        if endpoint == "/repos/Knapp-Kevin/sonic-rift":
            return {"full_name": "Knapp-Kevin/sonic-rift", "fork": True}
        if endpoint.endswith("/issues"):
            return [{"number": 7, "title": "Issue"}, {"number": 12, "pull_request": {"url": "..."}}]
        if endpoint.endswith("/pulls"):
            return [{"number": 12, "title": "PR"}]
        if any(endpoint.endswith("/" + x) for x in archiver.COLLECTIONS):
            return []
        if "/issues/" in endpoint or "/pulls/" in endpoint:
            return [{"id": 1}]
        raise AssertionError(endpoint)


class ArchiveContractTests(unittest.TestCase):
    def test_complete_archive_is_verifiable_and_contains_pr_reviews(self):
        reader = FakeReader()
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "archive"
            manifest = archiver.collect("Knapp-Kevin/sonic-rift", output, reader)
            verified = archiver.verify(output)
            self.assertEqual(verified, manifest)
            self.assertEqual(manifest["totals"]["issues"], 2)
            self.assertEqual(manifest["totals"]["pulls"], 1)
            self.assertTrue((output / "pr-details" / "12" / "reviews.json").is_file())
            self.assertTrue((output / "issue-details" / "7" / "timeline.json").is_file())
            self.assertEqual(len(manifest["files"]), 1 + 7 + 2 * 3 + 1 * 4)
            self.assertTrue(all(name.startswith("/repos/") for name, _ in reader.calls))

    def test_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "export"
            archiver.collect("Knapp-Kevin/sonic-rift", root, FakeReader())
            (root / "collections" / "issues.json").write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                archiver.verify(root)

    def test_partial_archive_has_no_success_manifest(self):
        class Fails(FakeReader):
            def get(self, endpoint, params=None):
                if endpoint.endswith("/labels"):
                    raise RuntimeError("rate limit")
                return super().get(endpoint, params)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "partial"
            with self.assertRaisesRegex(RuntimeError, "rate limit"):
                archiver.collect("Knapp-Kevin/sonic-rift", target, Fails())
            self.assertFalse((target / "manifest.json").exists())

    def test_refuses_existing_data_or_invalid_repo(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "backup"
            target.mkdir()
            (target / "keep.txt").write_text("keep")
            with self.assertRaises(FileExistsError):
                archiver.collect("Knapp-Kevin/sonic-rift", target, FakeReader())
            with self.assertRaises(ValueError):
                archiver.collect("foo/../evil", Path(folder) / "new", FakeReader())

    def test_pagination_header_parser(self):
        header = '<https://api.github.com/repos/a/b/issues?page=2>; rel="next", <x>; rel="last"'
        self.assertEqual(archiver.parse_next(header), "https://api.github.com/repos/a/b/issues?page=2")
        self.assertIsNone(archiver.parse_next(""))

    def test_canonical_json_round_trip(self):
        obj = {"name": "Français", "z": 1, "a": 2}
        blob = archiver.canonical_json(obj)
        self.assertEqual(json.loads(blob), obj)
        self.assertEqual(hashlib.sha256(blob).hexdigest(), hashlib.sha256(blob).hexdigest())


if __name__ == "__main__":
    unittest.main()
