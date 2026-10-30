"""Regression guard for global PyTorch loader mutation in the app bootstrap."""
import ast
from pathlib import Path
import unittest

COMMON = Path(__file__).resolve().parents[1] / "this_voice_thing/ui/common.py"


class TorchLoaderIsolationTests(unittest.TestCase):
    def test_common_does_not_override_global_loader(self):
        tree = ast.parse(COMMON.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if (isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "torch"
                        and target.attr == "load"):
                    self.fail("common.py must not override torch.load")


if __name__ == "__main__":
    unittest.main()
