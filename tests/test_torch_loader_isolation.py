"""Regression tests for bootstrap loader isolation.

The historical UI replaced torch.load globally whenever common was imported.
Source inspection alone is insufficient: check the actual function object in
an isolated interpreter, with NLTK downloads disabled.
"""

import ast
import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT / "this_voice_thing" / "ui" / "common.py"


class TorchLoaderIsolationTests(unittest.TestCase):
    def test_bootstrap_has_no_direct_loader_reassignment(self):
        tree = ast.parse(COMMON.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                targets = [node.target]
            for target in targets:
                if (isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "torch"
                        and target.attr == "load"):
                    self.fail("ui.common must not replace torch.load")

    def test_fresh_import_preserves_process_loader_and_explicit_cpu_load(self):
        # Run outside the test runner to avoid an already-cached common module.
        # No network and no real model weights are needed for this parity gate.
        script = """
import io
from unittest.mock import patch
import torch
import nltk
original = torch.load
with patch.object(nltk.data, "find", return_value="already-cached"), (
        patch.object(nltk, "download", side_effect=AssertionError("unexpected NLTK download"))):
    import this_voice_thing.ui.common
assert torch.load is original, "bootstrap replaced torch.load"
buffer = io.BytesIO()
torch.save({"value": torch.tensor([1, 2, 3])}, buffer)
buffer.seek(0)
loaded = torch.load(buffer, map_location="cpu", weights_only=True)
assert loaded["value"].tolist() == [1, 2, 3]
"""
        env = os.environ.copy()
        env.update({
            "PYTHONDONTWRITEBYTECODE": "1",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
        })
        proc = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(ROOT), env=env, capture_output=True,
            text=True, timeout=120, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout[-1000:] + proc.stderr[-2500:])


if __name__ == "__main__":
    unittest.main()
