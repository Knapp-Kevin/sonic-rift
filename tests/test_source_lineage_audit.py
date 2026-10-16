"""Offline regression tests for the Git-object ancestry evidence tool."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_source_lineage.py"
SPEC = importlib.util.spec_from_file_location("source_lineage", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class SourceLineageTests(unittest.TestCase):
    def test_parse_ls_tree_preserves_names_and_ignores_submodules(self):
        source = (
            b"100644 blob 0123456789abcdef\tRead me.md\0"
            b"100644 blob abcdef0123456789\tdocs/caf\xc3\xa9.txt\0"
            b"160000 commit 77777777\tvendored-submodule\0"
        )
        result = module.parse_tree(source)
        self.assertEqual(
            result,
            {"Read me.md": "0123456789abcdef",
             "docs/café.txt": "abcdef0123456789"},
        )

    def test_reject_malformed_git_tree(self):
        with self.assertRaisesRegex(ValueError, "Malformed git ls-tree"):
            module.parse_tree(b"this is not a Git tree entry\0")

    def test_exact_and_moved_blobs_not_confused_with_authorship(self):
        upstream = {
            "LICENSE": "sha-license",
            "main.py": "sha-original-app",
            "model_backends.py": "sha-engine",
            "requirements.in": "sha-old-req",
        }
        current = {
            "LICENSE": "sha-license",
            "this_voice_thing/ui/main_window.py": "sha-changed-shell",
            "this_voice_thing/engines/chatterbox_backend.py": "sha-new-facade",
            "requirements.in": "sha-new-req",
            "docs/historical_license.txt": "sha-license",
        }
        report = module.build_report(
            current, upstream, current_revision="head1", upstream_revision="original",
        )
        self.assertEqual(report["counts"]["current_paths_with_exact_upstream_blob"], 2)
        matches = {entry["current_path"] for entry in report["exact_blob_matches"]}
        self.assertEqual(matches, {"LICENSE", "docs/historical_license.txt"})
        mapped = {
            (row["upstream_path"], row["current_path"]): row["evidence"]
            for row in report["mapped_review_candidates"]
        }
        self.assertEqual(mapped[("LICENSE", "LICENSE")], "exact_same_blob")
        self.assertEqual(
            mapped[("requirements.in", "requirements.in")],
            "changed_blob_review_required",
        )
        self.assertEqual(
            mapped[("main.py", "this_voice_thing/ui/main_window.py")],
            "changed_blob_review_required",
        )
        self.assertIn("do not prove independent authorship", report["interpretation"])

    def test_missing_paths_are_not_independent_authorship(self):
        report = module.build_report(
            {"other.py": "sha"}, {"main.py": "old"},
            current_revision="HEAD", upstream_revision="base",
        )
        self.assertEqual(report["counts"]["current_paths_with_exact_upstream_blob"], 0)
        self.assertEqual(
            next(row["evidence"] for row in report["mapped_review_candidates"]
                 if row["current_path"] == "this_voice_thing/ui/threads.py"),
            "path_missing_or_unavailable",
        )

    def test_no_remote_fetch_and_git_revision_is_checked(self):
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, stdout=b"100644 blob abc\ta.txt\0")
        with patch.object(module.subprocess, "run", side_effect=run):
            result = module.git_tree(Path("/tmp/example"), "branch")
        self.assertEqual(result["a.txt"], "abc")
        self.assertEqual(
            [args[3:] for args in calls],
            [["rev-parse", "--verify", "branch^{commit}"],
             ["ls-tree", "-r", "-z", "branch"]],
        )
        self.assertTrue(all("fetch" not in args for args in calls))


if __name__ == "__main__":
    unittest.main()
