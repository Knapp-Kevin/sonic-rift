"""scripts/install_torch.py: CUDA detection, build choice and the install/verify loop.

Nothing here installs packages, touches the network or uses a GPU; subprocess calls are faked.
"""
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install_torch.py"
spec = importlib.util.spec_from_file_location("install_torch_under_test", SCRIPT)
install_torch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install_torch)


def _no_real_processes(*args, **_kwargs):
    raise AssertionError(f"test tried to start a real process: {args[:1]}")


# Fail-safe: a test that forgets to fake a call must fail, never run uv or touch a venv.
_guards = [patch.object(install_torch.subprocess, name, _no_real_processes)
           for name in ("run", "check_output", "Popen", "call", "check_call")]


def setUpModule():
    for guard in _guards:
        guard.start()


def tearDownModule():
    for guard in _guards:
        guard.stop()


class Recorder:
    """Stands in for InstallLog and keeps every message."""

    def __init__(self):
        self.lines = []

    def __call__(self, text):
        self.lines.append(text)

    def output(self, stream_name, text):
        for line in (text or "").splitlines():
            self.lines.append(f"[uv {stream_name}] {line}")

    def joined(self):
        return "\n".join(self.lines)


def fake_check_output(answers):
    """answers maps argv[0:2] tuples to output text or an exception instance."""
    def run(argv, **_kwargs):
        answer = answers.get(tuple(argv[:2]), FileNotFoundError(argv[0]))
        if isinstance(answer, BaseException):
            raise answer
        return answer
    return run


def tags(builds):
    return [build.tag for build in builds]


class CudaDetectionTests(unittest.TestCase):
    def test_cuda_number(self):
        self.assertEqual(install_torch.cuda_number("12.8"), 128)
        self.assertEqual(install_torch.cuda_number(" 11.8.89 "), 118)
        self.assertEqual(install_torch.cuda_number("13.0"), 130)
        self.assertIsNone(install_torch.cuda_number("12"))
        self.assertIsNone(install_torch.cuda_number("N/A"))
        self.assertIsNone(install_torch.cuda_number(""))

    def test_query_field_wins(self):
        run = fake_check_output({("nvidia-smi", "--query-gpu=cuda_version"): "\n12.4\n"})
        self.assertEqual(install_torch.find_cuda(run), (124, "nvidia-smi"))

    def test_plain_header_when_query_is_rejected(self):
        header = "| NVIDIA-SMI 580.00   Driver Version: 580.00   CUDA UMD Version: 13.0 |"
        run = fake_check_output({
            ("nvidia-smi", "--query-gpu=cuda_version"): subprocess.CalledProcessError(2, "nvidia-smi"),
            ("nvidia-smi",): header,
        })
        self.assertEqual(install_torch.find_cuda(run), (130, "nvidia-smi header"))

    def test_nvcc_when_no_driver_tool(self):
        nvcc = "Cuda compilation tools, release 12.1, V12.1.105"
        run = fake_check_output({("nvcc", "--version"): nvcc})
        self.assertEqual(install_torch.find_cuda(run), (121, "nvcc"))

    def test_nothing_found(self):
        self.assertEqual(install_torch.find_cuda(fake_check_output({})), (None, None))


class BuildChoiceTests(unittest.TestCase):
    def test_no_cuda_means_cpu_only(self):
        self.assertEqual(tags(install_torch.builds_to_try(None)), ["cpu"])

    def test_newest_runtime_skips_older_cuda_builds(self):
        self.assertEqual(tags(install_torch.builds_to_try(128)), ["cu128", "cpu"])
        self.assertEqual(tags(install_torch.builds_to_try(130)), ["cu128", "cpu"])

    def test_older_runtime_tries_every_compatible_build_newest_first(self):
        self.assertEqual(tags(install_torch.builds_to_try(126)), ["cu124", "cu121", "cu118", "cpu"])
        self.assertEqual(tags(install_torch.builds_to_try(121)), ["cu121", "cu118", "cpu"])
        self.assertEqual(tags(install_torch.builds_to_try(118)), ["cu118", "cpu"])

    def test_too_old_runtime_falls_to_cpu(self):
        self.assertEqual(tags(install_torch.builds_to_try(110)), ["cpu"])

    def test_pinned_versions_and_indexes(self):
        by_tag = {b.tag: b for b in (*install_torch.CUDA_BUILDS, install_torch.CPU_BUILD)}
        self.assertEqual(by_tag["cu128"].requirements(),
                         ["torch==2.8.0", "torchvision==0.23.0", "torchaudio==2.8.0"])
        for tag in ("cu124", "cu121", "cu118", "cpu"):
            self.assertEqual(by_tag[tag].requirements(),
                             ["torch==2.6.0", "torchvision==0.21.0", "torchaudio==2.6.0"])
            self.assertEqual(by_tag[tag].index_url, f"https://download.pytorch.org/whl/{tag}")
        self.assertFalse(install_torch.CPU_BUILD.is_cuda)

    def test_uv_command(self):
        command = install_torch.uv_command(install_torch.CUDA_BUILDS[0], python="py.exe")
        self.assertEqual(command[:5], ["uv", "pip", "install", "--python", "py.exe"])
        for flag in ("--upgrade", "--reinstall", "--strict", "--no-deps"):
            self.assertIn(flag, command)
        self.assertEqual(command[-2:], ["--index-url", "https://download.pytorch.org/whl/cu128"])
        self.assertIn("torch==2.8.0", command)


class RuntimeCheckTests(unittest.TestCase):
    def test_check_script_is_valid_python(self):
        compile(install_torch.RUNTIME_CHECK, "<runtime check>", "exec")

    def test_runtime_ok(self):
        good_gpu = {"ok": True, "cuda_available": True, "cuda_runtime_ok": True}
        self.assertTrue(install_torch.runtime_ok(good_gpu, needs_cuda=True))
        self.assertTrue(install_torch.runtime_ok({"ok": True, "cuda_available": False}, needs_cuda=False))
        self.assertFalse(install_torch.runtime_ok({"ok": True, "cuda_available": False}, needs_cuda=True))
        self.assertFalse(install_torch.runtime_ok({"ok": True, "cuda_available": True,
                                                   "cuda_runtime_ok": False}, needs_cuda=True))
        self.assertFalse(install_torch.runtime_ok({"ok": False}, needs_cuda=False))

    def test_read_runtime_takes_the_last_json_line(self):
        out = 'some warning\n{"ok": true, "torch_version": "2.6.0+cpu"}\n\n'
        run = lambda *a, **k: SimpleNamespace(stdout=out)
        self.assertEqual(install_torch.read_runtime(python="py", run=run)["torch_version"], "2.6.0+cpu")

    def test_read_runtime_without_output(self):
        run = lambda *a, **k: SimpleNamespace(stdout="")
        self.assertEqual(install_torch.read_runtime(python="py", run=run),
                         {"ok": False, "error": "No verification output"})


class InstallLoopTests(unittest.TestCase):
    def runner(self, reports, failing_tags=()):
        """Fake subprocess.run: uv installs (failing for failing_tags), then canned reports."""
        reports = list(reports)

        def run(argv, **_kwargs):
            if argv[0] == "uv":
                tag = argv[-1].rsplit("/", 1)[-1]
                if tag in failing_tags:
                    raise subprocess.CalledProcessError(2, argv, output="out", stderr="no wheel")
                return SimpleNamespace(stdout="Installed 3 packages", stderr="")
            return SimpleNamespace(stdout=json.dumps(reports.pop(0)))
        return run

    def test_successful_cuda_build(self):
        say = Recorder()
        report = {"ok": True, "cuda_available": True, "cuda_runtime_ok": True,
                  "torch_version": "2.8.0+cu128", "torch_cuda_version": "12.8", "device_count": 1}
        worked, reason = install_torch.try_build(install_torch.CUDA_BUILDS[0], say, run=self.runner([report]))
        self.assertTrue(worked)
        self.assertIsNone(reason)
        self.assertIn("[uv stdout] Installed 3 packages", say.lines)
        self.assertIn("PyTorch verification succeeded. Mode=CUDA, torch=2.8.0+cu128", say.joined())

    def test_failed_install_reports_exit_code(self):
        say = Recorder()
        worked, reason = install_torch.try_build(install_torch.CUDA_BUILDS[0], say,
                                                 run=self.runner([], failing_tags={"cu128"}))
        self.assertFalse(worked)
        self.assertEqual(reason, "installer exited with code 2")
        self.assertIn("[uv stderr] no wheel", say.lines)

    def test_cuda_build_without_working_gpu_fails_verification(self):
        report = {"ok": True, "cuda_available": True, "cuda_runtime_ok": False,
                  "cuda_runtime_error": "no kernel image"}
        worked, reason = install_torch.try_build(install_torch.CUDA_BUILDS[0], Recorder(),
                                                 run=self.runner([report]))
        self.assertFalse(worked)
        self.assertTrue(reason.startswith("verification failed:"))
        self.assertIn("runtime_error=no kernel image", reason)

    def test_main_falls_back_to_cpu(self):
        say = Recorder()
        cpu = {"ok": True, "cuda_available": False, "torch_version": "2.6.0+cpu"}
        with patch.object(install_torch, "find_cuda", return_value=(128, "nvidia-smi")), \
                patch.object(install_torch.subprocess, "run", self.runner([cpu], failing_tags={"cu128"})):
            self.assertEqual(install_torch.main(say), 0)
        text = say.joined()
        self.assertIn("Detected NVIDIA CUDA capability 128 via nvidia-smi.", text)
        self.assertIn("PyTorch target cu128 failed: installer exited with code 2", text)
        self.assertIn("Falling back to the next compatible PyTorch runtime.", text)
        self.assertIn("Mode=CPU", text)

    def test_main_returns_1_when_everything_fails(self):
        say = Recorder()
        with patch.object(install_torch, "find_cuda", return_value=(None, None)), \
                patch.object(install_torch.subprocess, "run", self.runner([], failing_tags={"cpu"})):
            self.assertEqual(install_torch.main(say), 1)
        self.assertIn("No NVIDIA CUDA runtime detected. Installing CPU PyTorch build.", say.lines)
        self.assertEqual(say.lines[-3:], ["Unable to install a working PyTorch configuration.",
                                          "Attempts:", "  - cpu: installer exited with code 2"])


class InstallLogTests(unittest.TestCase):
    def test_writes_console_and_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "installer.log")
            say = install_torch.InstallLog(path)
            with patch("builtins.print") as printed:
                say("hello")
                say.output("stderr", "a\nb")
                say.output("stdout", "")
            say.close()
            with open(path, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "hello\n[uv stderr] a\n[uv stderr] b\n")
            self.assertEqual(printed.call_count, 2)

    def test_console_only_without_a_path(self):
        with patch("builtins.print") as printed:
            install_torch.InstallLog(None)("x")
        printed.assert_called_once_with("x")


if __name__ == "__main__":
    unittest.main()
