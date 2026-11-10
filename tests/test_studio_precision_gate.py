"""The offline Studio qualification runner must fail closed before testing bad heads."""
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "studio_precision_gate.py"


class StudioPrecisionGateTests(unittest.TestCase):
    def test_wrong_head_creates_no_go_receipt_without_running_tests(self):
        with tempfile.TemporaryDirectory() as folder:
            run = subprocess.run([
                sys.executable, str(RUNNER),
                "--expected-head", "0" * 40,
                "--receipt-dir", folder,
            ], cwd=ROOT, text=True, capture_output=True, timeout=30)
            self.assertEqual(run.returncode, 2, run.stderr)
            receipts = list(Path(folder).glob("studio-precision-*/receipt.json"))
            self.assertEqual(len(receipts), 1)
            payload = json.loads(receipts[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["expected_head"], "0" * 40)
            self.assertEqual(payload["status"], "NO_GO")
            self.assertEqual(payload["stages"], [])
            self.assertEqual(payload["owner_gui_audio_acceptance"], "NOT_RUN")
            self.assertEqual(payload["run_id"], receipts[0].parent.name)

    def test_consecutive_runs_preserve_distinct_receipts_and_log_directories(self):
        with tempfile.TemporaryDirectory() as folder:
            for _ in range(2):
                run = subprocess.run([
                    sys.executable, str(RUNNER),
                    "--expected-head", "0" * 40,
                    "--receipt-dir", folder,
                    "--full",
                ], cwd=ROOT, text=True, capture_output=True, timeout=30)
                self.assertEqual(run.returncode, 2, run.stderr)
            receipts = sorted(Path(folder).glob("studio-precision-*/receipt.json"))
            self.assertEqual(len(receipts), 2)
            self.assertNotEqual(receipts[0].parent, receipts[1].parent)
            for path in receipts:
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(payload["run_id"], path.parent.name)
                self.assertEqual(payload["status"], "NO_GO")
                self.assertEqual(payload["stages"], [])

    def test_windows_test_environment_redirects_profile_and_caches(self):
        isolated_test_env = runpy.run_path(str(RUNNER))["isolated_test_env"]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            initial_home = os.environ.get("USERPROFILE")
            env = isolated_test_env(root)
            redirected = (
                "USERPROFILE", "HOME", "APPDATA", "LOCALAPPDATA",
                "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME",
                "HF_HOME", "TORCH_HOME", "MPLCONFIGDIR", "TEMP", "TMP", "TMPDIR",
            )
            for name in redirected:
                with self.subTest(name=name):
                    destination = Path(env[name])
                    self.assertTrue(destination.is_dir())
                    self.assertTrue(destination.is_relative_to(root))
            self.assertEqual(env["QT_QPA_PLATFORM"], "offscreen")
            self.assertEqual(env["HF_HUB_OFFLINE"], "1")
            self.assertEqual(env["TRANSFORMERS_OFFLINE"], "1")
            self.assertEqual(env["PIP_NO_INDEX"], "1")
            self.assertEqual(os.environ.get("USERPROFILE"), initial_home)

    def test_receipts_in_source_tree_are_refused(self):
        run = subprocess.run([
            sys.executable, str(RUNNER),
            "--expected-head", "0" * 40,
            "--receipt-dir", str(ROOT / "temporary-gate-output"),
        ], cwd=ROOT, text=True, capture_output=True, timeout=20)
        self.assertEqual(run.returncode, 2)
        self.assertIn("outside the source checkout", run.stderr)


if __name__ == "__main__":
    unittest.main()
