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


PACKAGE = ROOT / "this_voice_thing"


def _torch_attribute_writes(tree):
    """Assignments to ``torch.<name>`` (at any depth, e.g. ``torch.serialization.load``) and
    ``setattr(torch..., ...)`` calls: any of them would change PyTorch for the whole process."""
    def is_torch(node):
        while isinstance(node, ast.Attribute):
            node = node.value
        return isinstance(node, ast.Name) and node.id == "torch"

    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets = [node.target]
        for target in targets:
            if isinstance(target, ast.Attribute) and is_torch(target.value):
                yield node.lineno, ast.unparse(target)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "setattr"
                and node.args and is_torch(node.args[0])):
            yield node.lineno, ast.unparse(node)


class NoProcessWideTorchPatches(unittest.TestCase):
    """The guard above covers ui/common.py; a patch moved to any other module is just as global."""

    def test_no_module_in_the_package_patches_torch(self):
        found = []
        for path in sorted(PACKAGE.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            found += [f"{path.relative_to(ROOT)}:{line}: {text}" for line, text in _torch_attribute_writes(tree)]
        self.assertEqual(found, [], "Sonic Rift must not patch torch process-wide")

    def test_the_scanner_catches_the_historical_patch(self):
        old = "import torch\ntorch_load_original = torch.load\ntorch.load = lambda *a, **k: None\n"
        self.assertEqual([line for line, _ in _torch_attribute_writes(ast.parse(old))], [3])
        self.assertTrue(list(_torch_attribute_writes(ast.parse("import torch\nsetattr(torch, 'load', print)\n"))))
        self.assertTrue(list(_torch_attribute_writes(ast.parse("import torch\ntorch.serialization.load = print\n"))))

    def test_importing_the_window_and_chatterbox_provider_leaves_torch_load_alone(self):
        # The app imports far more than ui.common at start-up: the main window pulls in every
        # page and the in-process Chatterbox provider. No window is created, nothing is loaded.
        script = """
from unittest.mock import patch
import torch
import nltk
original = torch.load
with patch.object(nltk.data, "find", return_value="already-cached"), (
        patch.object(nltk, "download", side_effect=AssertionError("unexpected NLTK download"))):
    import this_voice_thing.ui.main_window
    import this_voice_thing.engines.chatterbox_provider
assert torch.load is original, torch.load
assert torch.load.__module__ == "torch.serialization", torch.load.__module__
"""
        env = os.environ.copy()
        env.update({"PYTHONDONTWRITEBYTECODE": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                    "HF_DATASETS_OFFLINE": "1", "QT_QPA_PLATFORM": "offscreen"})
        proc = subprocess.run([sys.executable, "-c", script], cwd=str(ROOT), env=env, capture_output=True,
                              text=True, timeout=300, check=False)
        self.assertEqual(proc.returncode, 0, proc.stdout[-1000:] + proc.stderr[-2500:])


if __name__ == "__main__":
    unittest.main()
