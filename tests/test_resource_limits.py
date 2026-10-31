"""Resource limits: machine-based defaults, saved limits clamped to the PC, engine workers held to
them (threads, priority, GPU memory), and an explicit warning before heavy jobs."""

import glob
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "engines"))

from this_voice_thing.core import resources  # noqa: E402
from this_voice_thing.core.resources import JobCost, ResourceLimits, SystemInfo  # noqa: E402
from this_voice_thing.engines import worker as engine_worker  # noqa: E402
import worker_limits  # noqa: E402

PC = SystemInfo(cpu_threads=16, ram_gb=31.0, gpu_name="NVIDIA GeForce RTX 5070 Ti", gpu_gb=15.9)


class Defaults(unittest.TestCase):
    def test_recommended_limits_come_from_the_machine(self):
        self.assertEqual(resources.recommended(PC), ResourceLimits(8, "below_normal", 15.4, True))
        self.assertEqual(resources.recommended(SystemInfo(1, 8.0)).cpu_threads, 1)
        self.assertEqual(resources.recommended(SystemInfo(4, 8.0)).gpu_memory_gb, 0.0)

    def test_saved_limits_are_clamped_to_this_pc(self):
        limits = resources.from_settings({"cpu_threads": 64, "priority": "turbo", "gpu_memory_gb": 99,
                                          "warn_heavy_jobs": False}, PC)
        self.assertEqual(limits, ResourceLimits(16, "below_normal", 15.9, False))
        self.assertEqual(resources.from_settings({"cpu_threads": "x", "gpu_memory_gb": None}, PC),
                         resources.recommended(PC))
        self.assertEqual(resources.from_settings(None, PC), resources.recommended(PC))

    def test_detect_reports_this_machine(self):
        info = resources.detect()
        self.assertGreaterEqual(info.cpu_threads, 1)
        self.assertGreater(info.ram_gb, 0)


class WorkerEnforcement(unittest.TestCase):
    limits = ResourceLimits(6, "below_normal", 12.0)

    def test_environment_carries_thread_and_gpu_limits(self):
        env = resources.worker_env(self.limits)
        for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "SONIC_RIFT_CPU_THREADS"):
            self.assertEqual(env[name], "6")
        self.assertEqual(env["SONIC_RIFT_GPU_MEMORY_GB"], "12")
        self.assertEqual(resources.worker_env(None), {})

    def test_windows_priority_flags(self):
        with mock.patch.object(resources.os, "name", "nt"):
            self.assertEqual(resources.creation_flags(self.limits), 0x4000)
            self.assertEqual(resources.creation_flags(ResourceLimits(1, "low", 0)), 0x40)
            self.assertEqual(resources.creation_flags(ResourceLimits(1, "normal", 0)), 0x20)

    def test_worker_process_starts_within_the_limits(self):
        resources.set_current(self.limits)
        self.addCleanup(resources.set_current, None)
        with mock.patch.object(engine_worker.subprocess, "Popen") as popen, \
                mock.patch.object(engine_worker.WorkerProcess, "_read_reply", return_value={"ok": True}), \
                mock.patch.object(engine_worker.threading, "Thread"):
            engine_worker.WorkerProcess("python", "worker.py", "test", env={"OMP_NUM_THREADS": "2"})
        kwargs = popen.call_args.kwargs
        self.assertEqual(kwargs["env"]["SONIC_RIFT_GPU_MEMORY_GB"], "12")
        self.assertEqual(kwargs["env"]["OMP_NUM_THREADS"], "2")         # an engine's own setting wins
        if os.name == "nt":
            self.assertTrue(kwargs["creationflags"] & 0x4000)

    def test_every_engine_worker_applies_the_limits(self):
        workers = sorted(glob.glob(str(ROOT / "engines" / "*" / "*_worker.py")))
        self.assertGreaterEqual(len(workers), 7)
        for path in workers:
            self.assertIn("worker_limits.apply(torch)", Path(path).read_text(encoding="utf-8"), path)

    def test_worker_side_caps_threads_and_gpu_memory(self):
        torch = SimpleNamespace(set_num_threads=mock.Mock(), set_num_interop_threads=mock.Mock(),
                                cuda=SimpleNamespace(is_available=lambda: True,
                                                     get_device_properties=lambda _i: SimpleNamespace(total_memory=16 * 2**30),
                                                     set_per_process_memory_fraction=mock.Mock()))
        with mock.patch.dict(os.environ, {"SONIC_RIFT_CPU_THREADS": "6", "SONIC_RIFT_GPU_MEMORY_GB": "12"}):
            worker_limits.apply(torch)
        torch.set_num_threads.assert_called_once_with(6)
        torch.cuda.set_per_process_memory_fraction.assert_called_once_with(0.75, 0)

    def test_no_limits_in_the_environment_changes_nothing(self):
        torch = SimpleNamespace(set_num_threads=mock.Mock(), cuda=SimpleNamespace(is_available=lambda: True))
        with mock.patch.dict(os.environ, {"SONIC_RIFT_CPU_THREADS": "", "SONIC_RIFT_GPU_MEMORY_GB": ""}):
            worker_limits.apply(torch)
        torch.set_num_threads.assert_not_called()


class Warnings(unittest.TestCase):
    limits = resources.recommended(PC)

    def test_heavy_means_long_or_a_large_share_of_the_gpu(self):
        self.assertTrue(resources.heavy(JobCost("x", 3.0), self.limits))
        self.assertTrue(resources.heavy(JobCost("x", 0.5, gpu_gb=12), self.limits))
        self.assertFalse(resources.heavy(JobCost("x", 0.5, gpu_gb=2), self.limits))

    def test_over_budget_names_the_limit(self):
        problems = resources.over_budget(JobCost("Music", 5, gpu_gb=15.2, ram_gb=28), replace_gpu(self.limits, 8), PC)
        self.assertEqual(len(problems), 2)
        self.assertIn("limit is 8 GB", problems[0])

    def test_warning_states_time_resources_and_where_to_change_them(self):
        text = resources.warning_text(JobCost("2 takes with MOSS", 1.8, gpu_gb=15.2), self.limits, PC)
        for fact in ("about 2 minutes", "15 GB of GPU memory", "8 of 16 CPU threads", "below normal",
                     "Settings › Performance", "close games"):
            self.assertIn(fact, text)


def replace_gpu(limits, gb):
    from dataclasses import replace
    return replace(limits, gpu_memory_gb=gb)


class SettingsCard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        from this_voice_thing import paths
        from this_voice_thing.ui import main_window
        cls.app = QApplication.instance() or QApplication([])
        cls.tmp = tempfile.mkdtemp()
        sys.argv = ["main.py"]
        with mock.patch.object(paths, "ROOT", cls.tmp), \
                mock.patch.object(main_window.ChatterboxApp, "start_default_model_load", lambda self: None), \
                mock.patch.object(main_window.ChatterboxApp, "restart_api_server", lambda self: None), \
                mock.patch.object(resources, "detect", return_value=PC):
            cls.window = main_window.ChatterboxApp()
        cls.window.start_discover = lambda: None

    @classmethod
    def tearDownClass(cls):
        cls.window.close()
        resources.set_current(None)

    def test_limits_are_in_force_at_start_and_on_the_settings_page(self):
        w = self.window
        self.assertEqual(resources.current(), resources.recommended(PC))
        w.show_page(w.PAGE_ADVANCED)
        self.assertEqual((w.perf_threads_spin.value(), w.perf_priority_combo.currentData(), w.perf_gpu_spin.value()),
                         (8, "below_normal", 15.4))
        self.assertEqual(w.perf_threads_spin.maximum(), 16)

    def test_changes_are_saved_applied_and_can_be_reset(self):
        w = self.window
        w.perf_threads_spin.setValue(4)
        w.perf_priority_combo.setCurrentIndex(w.perf_priority_combo.findData("low"))
        self.assertEqual(w.app_settings["performance"]["cpu_threads"], 4)
        self.assertEqual(resources.current().priority, "low")
        w.reset_resource_limits()
        self.assertEqual(resources.current(), resources.recommended(PC))

    def test_heavy_job_warns_and_cancel_stops_it(self):
        w = self.window
        from PySide6.QtWidgets import QMessageBox
        with mock.patch.object(QMessageBox, "exec"), mock.patch.object(QMessageBox, "clickedButton", return_value=None):
            self.assertFalse(w.confirm_heavy_job(JobCost("Music", 6, gpu_gb=9), "Music"))
        self.assertTrue(w.confirm_heavy_job(JobCost("A short line", 0.2, gpu_gb=2), "Speech"))

    def test_a_job_over_the_limit_is_refused_with_the_reason(self):
        w = self.window
        with mock.patch("this_voice_thing.ui.pages.performance.QMessageBox.warning") as warned:
            self.assertFalse(w.confirm_heavy_job(JobCost("MOSS", 1, gpu_gb=20), "Sounds"))
        self.assertIn("Settings › Performance", warned.call_args[0][2])

    def test_moss_render_cost_is_estimated(self):
        from this_voice_thing.core.soundscape import catalog, render
        w = self.window
        request = render.SoundRequest(engine="moss_sfx_v2", seconds=60.0, candidates=3, prompt="rain")
        cost = w.sound_job_cost(request, catalog.MOSS_SFX_V2)
        self.assertEqual(cost.gpu_gb, 15.2)
        self.assertAlmostEqual(cost.minutes, (3 * 3 * 23 + 60) / 60, places=2)   # 62 s loop: 3 chunks


if __name__ == "__main__":
    unittest.main()
