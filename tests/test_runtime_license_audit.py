"""No-install checks for current-environment license-inventory review."""
import importlib.util
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("audit_runtime_licenses", HERE / "scripts" / "audit_runtime_licenses.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class RuntimeLicenseAuditTests(unittest.TestCase):
    def test_normalization_and_conservative_flags(self):
        pkg = {"name": "Praat_Parselmouth", "version": "0.4", "license_expression": "GPL-3.0",
               "license_field": "", "license_classifiers": []}
        self.assertEqual(audit.canonical_name(pkg["name"]), "praat-parselmouth")
        self.assertIn("known_dependency_review", audit.classify(pkg))
        self.assertIn("copyleft_or_dual_license_review", audit.classify(pkg))
        self.assertIn("no_license_metadata", audit.classify({"name": "unknown", "version": "1"}))

    def test_version_aware_evaluation_package_review_does_not_claim_ban(self):
        old = {"name": "kaldiio", "version": "2.18.1", "license_expression": "MIT", "license_field": ""}
        flagged = audit.review_environment("engine", [old])
        row = flagged["distributions"][0]
        self.assertIn("known_dependency_review", row["review_flags"])
        self.assertIn("actual LICENSE", row["manual_review_reason"])
        self.assertNotIn("license_cleared", row)

    def test_duplicate_metadata_and_malformed_records_fail(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            audit.review_environment("main", [{"name": "foo_bar", "version": "1"}, {"name": "foo-bar", "version": "2"}])
        with self.assertRaisesRegex(ValueError, "Invalid"):
            audit.review_environment("main", [{"name": "x", "version": None}])

    def test_interpreter_command_isolation_and_no_shell_or_network(self):
        args = []
        def run(command, **kwargs):
            args.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps([{
                "name": "TestLib", "version": "1", "license_expression": "MIT",
                "license_field": "", "license_classifiers": [], "license_field_truncated": False,
            }]), stderr="")
        with patch.object(audit.subprocess, "run", side_effect=run):
            data = audit.inspect_python("C:/App Env/python.exe")
        self.assertEqual(data[0]["name"], "TestLib")
        self.assertEqual(args[0][0][0], "C:/App Env/python.exe")
        self.assertEqual(args[0][0][1:3], ["-I", "-c"])
        self.assertNotIn("shell", args[0][1])

    def test_real_current_interpreter_inventory_in_scratch_json(self):
        distributions = audit.inspect_python(sys.executable)
        summary = audit.review_environment("scratch", distributions)
        self.assertGreater(summary["distribution_count"], 0)
        self.assertEqual(len(summary["distributions"]), summary["distribution_count"])
        self.assertIn("review_flags", summary["distributions"][0])

    def test_cli_explicit_output_and_strict_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.json"
            self.assertEqual(audit.main(["--python", f"qa={sys.executable}", "--output", str(output)]), 0)
            report = json.loads(output.read_text())
            self.assertEqual(report["license_decision"], "not_cleared_manual_review_required")
            self.assertEqual(report["environments"][0]["environment"], "qa")
            self.assertGreater(report["environments"][0]["distribution_count"], 0)


if __name__ == "__main__":
    unittest.main()
