"""Engine environment installs: unused dependencies with unacceptable licenses are removed."""

import unittest
from unittest.mock import patch

from this_voice_thing.engines import voxcpm, worker


class InstallEnvTests(unittest.TestCase):
    def test_remove_runs_after_the_installs(self):
        commands = []
        with patch.object(worker.shutil, "which", return_value="uv"), \
                patch.object(worker, "check_path_length"), \
                patch.object(worker.os, "makedirs"), \
                patch.object(worker, "_run", side_effect=lambda command, log, name: commands.append(command)):
            worker.install_env("demo", [["pkg"]], log=lambda _l: None, remove=["bad-dep"])
        self.assertEqual(commands[-1][1:3], ["pip", "uninstall"])
        self.assertIn("bad-dep", commands[-1])
        self.assertEqual(commands[-2][-1], "pkg")      # after the last install step

    def test_voxcpm_drops_funasr_and_kaldiio(self):
        with patch.object(worker, "install_env") as install_env:
            voxcpm.install(log=lambda _l: None)
        self.assertEqual(set(install_env.call_args.kwargs["remove"]), {"funasr", "kaldiio"})


if __name__ == "__main__":
    unittest.main()
