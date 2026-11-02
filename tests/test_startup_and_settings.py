"""Start-up log, console text, GPU probe, model list and app settings: behaviour the window
relies on. Everything is written to temporary folders, never to the real settings."""

import datetime
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from this_voice_thing.core import config_io, console_io, hardware  # noqa: E402


class ConsoleTextTests(unittest.TestCase):
    def test_matches_ascii_backslashreplace(self):
        samples = ["plain", "café", "€ 5", "emoji \U0001f600", "tab\tnew\nline", "\ud800 lone",
                   "Привет", "", 42, None]
        for value in samples:
            expected = str(value).encode("ascii", "backslashreplace").decode("ascii")
            self.assertEqual(console_io.safe_console_text(value), expected, repr(value))

    def test_stream_helpers_tolerate_missing_streams(self):
        self.assertFalse(console_io.stream_is_terminal(None))
        self.assertEqual(console_io.stream_encoding(None), "utf-8")
        self.assertEqual(console_io.stream_encoding(SimpleNamespace(encoding="cp1252")), "cp1252")


class StartupLogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from this_voice_thing import app
        cls.app = app

    def test_log_path_is_timestamped_in_logs_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            logs = os.path.join(folder, "logs")
            with patch.object(self.app.paths, "LOGS_DIR", logs):
                path = self.app.make_startup_log_path(datetime.datetime(2026, 3, 4, 5, 6, 7))
            self.assertEqual(path, os.path.join(logs, "app_startup_20260304_050607.log"))
            self.assertTrue(os.path.isdir(logs))
            self.assertFalse(os.path.exists(path))   # only the folder is created

    def test_tee_copies_to_log_and_console(self):
        console, log = io.StringIO(), io.StringIO()
        tee = self.app.TeeFile(console, log)
        self.assertEqual(tee.write("hello\n"), 6)
        self.assertEqual(tee.write(7), 1)
        tee.flush()
        self.assertEqual(log.getvalue(), "hello\n7")
        self.assertEqual(console.getvalue(), "hello\n7")
        self.assertFalse(tee.isatty())

    def test_tee_survives_missing_console_and_closed_log(self):
        log = io.StringIO()
        tee = self.app.TeeFile(None, log)
        self.assertEqual(tee.encoding, "utf-8")
        tee.write("kept")
        self.assertEqual(log.getvalue(), "kept")
        log.close()
        self.assertEqual(tee.write("late"), 4)   # a thread printing during shutdown
        tee.flush()

        broken = MagicMock()
        broken.write.side_effect = OSError("console gone")
        broken.flush.side_effect = OSError("console gone")
        tee = self.app.TeeFile(broken, io.StringIO())
        tee.write("x")
        tee.flush()

    def test_startup_error_message(self):
        user32 = MagicMock()
        with patch.object(self.app.ctypes, "windll", SimpleNamespace(user32=user32), create=True):
            self.app.show_startup_error("C:/logs/app.log", "ValueError: boom")
        _hwnd, text, title, flags = user32.MessageBoxW.call_args.args
        self.assertEqual(text, "Sonic Rift failed to start.\n\nLog file:\nC:/logs/app.log\n\n"
                               "Last error:\nValueError: boom")
        self.assertEqual(title, "Sonic Rift: Startup Error")
        self.assertEqual(flags, 0x10)

    def test_startup_error_without_message_box_is_silent(self):
        with patch.object(self.app.ctypes, "windll", None, create=True):
            self.app.show_startup_error("log", "error")


class GpuProbeTests(unittest.TestCase):
    def test_nvidia_smi_listing(self):
        listing = "GPU 0: NVIDIA GeForce RTX 5070 Ti (UUID: GPU-1)\nGPU 1: NVIDIA (UUID: GPU-2)\n"
        with patch.object(hardware.subprocess, "run", return_value=SimpleNamespace(stdout=listing)) as run:
            self.assertTrue(hardware.has_system_nvidia_gpu())
        self.assertEqual(run.call_args.args[0], ["nvidia-smi", "-L"])
        with patch.object(hardware.subprocess, "run", return_value=SimpleNamespace(stdout="  \n\n")):
            self.assertFalse(hardware.has_system_nvidia_gpu())
        with patch.object(hardware.subprocess, "run", side_effect=PermissionError):
            self.assertFalse(hardware.has_system_nvidia_gpu())
        with patch.object(hardware.subprocess, "run",
                          side_effect=subprocess.CalledProcessError(9, "nvidia-smi")):
            self.assertFalse(hardware.has_system_nvidia_gpu())

    def test_probe_reports_architecture_list_sorted(self):
        stub = SimpleNamespace(cuda=SimpleNamespace(
            is_available=lambda: True,
            get_device_capability=lambda _index: (12, 0),
            get_arch_list=lambda: ["sm_90", "sm_80", "sm_86"],
        ))
        self.assertEqual(hardware.probe_usable_torch_cuda(stub), (
            False, "Installed PyTorch CUDA kernels do not include sm_120. "
                   "Supported architectures: ['sm_80', 'sm_86', 'sm_90']"))

    def test_probe_failure_in_rnn_is_reported(self):
        class Tensor:
            def __matmul__(self, other):
                return self

            def sum(self):
                return self

            def item(self):
                return 0.0

        def broken_gru(*_args):
            raise RuntimeError("no kernel image is available")

        stub = SimpleNamespace(
            cuda=SimpleNamespace(is_available=lambda: True, get_device_capability=lambda _i: (8, 6),
                                 get_arch_list=lambda: ["sm_86"]),
            randn=lambda *a, **k: Tensor(),
            nn=SimpleNamespace(GRU=broken_gru),
        )
        self.assertEqual(hardware.probe_usable_torch_cuda(stub), (False, "no kernel image is available"))


class ConfigReadTests(unittest.TestCase):
    def test_unreadable_path_is_a_diagnostic(self):
        with tempfile.TemporaryDirectory() as folder:
            value, error = config_io.read_json(folder)   # a folder, not a file
            self.assertIsNone(value)
            self.assertIn(f"Failed to read '{folder}'", error)

    def test_non_utf8_file_is_a_diagnostic(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "app_settings.json")
            with open(path, "wb") as handle:
                handle.write(b'{"a": "\xff"}')
            value, error = config_io.read_json(path, error_label="settings")
            self.assertIsNone(value)
            self.assertTrue(error.startswith("Failed to read settings: "))


class ModelListTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from this_voice_thing.ui import common
        cls.common = common

    def load(self, payload):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "models.json")
            if payload is not None:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(payload if isinstance(payload, str) else json.dumps(payload))
            with patch("builtins.print"):
                models = self.common.load_models_config(path)
            if payload is not None:
                with open(path, encoding="utf-8") as handle:
                    self.assertEqual(handle.read(), payload if isinstance(payload, str) else json.dumps(payload))
            return models

    def default_entry(self):
        c = self.common
        first = c.DEFAULT_MODELS_CONFIG["models"][0]
        return {"repo_id": c.DEFAULT_MODEL_REPO, "label": first["label"], "enabled": True,
                "experimental": False, "test_text": first["test_text"], "notes": first["notes"],
                "backend": c.BACKEND_MULTILINGUAL, "language_id": "en",
                "multilingual_t3_model": c.DEFAULT_MULTILINGUAL_T3_MODEL,
                "test_texts": dict(c.DEFAULT_LANGUAGE_TEST_TEXTS)}

    def test_missing_or_damaged_file_gives_the_default_model(self):
        for payload in (None, "{not json", "[]", "null"):
            models = self.load(payload)
            self.assertEqual(len(models), 1, payload)
            self.assertEqual(models[0]["repo_id"], self.common.DEFAULT_MODEL_REPO)
            self.assertEqual(models[0]["backend"], self.common.BACKEND_MULTILINGUAL)

    def test_entries_are_cleaned_and_deduplicated(self):
        c = self.common
        payload = {"models": [
            "not an entry",
            {"label": "no repo"},
            {"repo_id": "  someone/voice  ", "backend": "legacy", "label": "  ", "language_id": " DE ",
             "test_texts": {" FR ": " Bonjour ", "": "x", "es": "   "}, "license": " MIT ",
             "download_bytes": 1234, "notes": " n ", "qwen_variant": " base "},
            {"repo_id": "someone/voice", "backend": "legacy", "label": "someone/voice"},   # duplicate
            {"repo_id": "someone/voice", "backend": "legacy", "label": "Other label", "enabled": 0,
             "download_bytes": -5, "test_texts": ["wrong type"]},
        ]}
        models = self.load(payload)
        self.assertEqual(models[0], self.default_entry())   # added first, the file leaves it out
        self.assertEqual(models[1], {
            "license": "mit", "download_bytes": 1234, "repo_id": "someone/voice",
            "label": "someone/voice", "enabled": True, "experimental": True, "test_text": "",
            "notes": "n", "backend": "legacy", "language_id": "de", "multilingual_t3_model": "",
            "qwen_variant": "base", "test_texts": {"fr": "Bonjour"}})
        self.assertEqual(list(models[1]), ["license", "download_bytes", "repo_id", "label", "enabled",
                                           "experimental", "test_text", "notes", "backend", "language_id",
                                           "multilingual_t3_model", "qwen_variant", "test_texts"])
        self.assertEqual(models[2]["label"], "Other label")
        self.assertFalse(models[2]["enabled"])
        self.assertEqual(models[2]["test_texts"], {})
        self.assertNotIn("download_bytes", models[2])
        self.assertEqual(len(models), 3)
        self.assertEqual(c.BACKEND_LEGACY, "legacy")

    def test_listed_default_model_is_kept_in_place(self):
        c = self.common
        payload = {"models": [
            {"repo_id": "a/b", "backend": "legacy"},
            {"repo_id": c.DEFAULT_MODEL_REPO, "label": "Mine", "experimental": True},
        ]}
        models = self.load(payload)
        self.assertEqual([m["repo_id"] for m in models], ["a/b", c.DEFAULT_MODEL_REPO])
        self.assertEqual(models[1]["label"], "Mine")
        self.assertTrue(models[1]["experimental"])
        self.assertTrue(models[0]["experimental"])
        self.assertEqual(models[1]["multilingual_t3_model"], c.resolve_multilingual_t3_model(c.DEFAULT_MULTILINGUAL_T3_MODEL))


# An app_settings.json as older versions wrote it (window keys, token, sampling, API, finishing).
OLDER_SETTINGS = {
    "hf_token": "",
    "window_geometry": "AdnQywADAAAAAAAAAAAAAAAAAAAAAA==",
    "window_maximized": False,
    "window_fullscreen": False,
    "sampling": {"repetition_penalty": 1.3, "min_p": 0.05, "top_p": 0.9},
    "api": {"enabled": True, "port": 8881, "token": "local"},
    "finishing": {"speed": 1.0, "normalize": True},
    "finishing_expanded": True,
    "tuning_expanded": False,
    "label": "Français ✓",
}


class AppSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication, QMainWindow
        from this_voice_thing.ui import main_window
        cls.qt_app = QApplication.instance() or QApplication([])
        cls.main_window = main_window

        class Window(QMainWindow):
            restore_window_state = main_window.SonicRiftApp.restore_window_state
            remember_window_state = main_window.SonicRiftApp.remember_window_state
            save_app_settings = main_window.SonicRiftApp.save_app_settings

        cls.Window = Window

    def make_window(self, settings, folder):
        window = self.Window()
        window.app_settings = settings
        window.app_settings_path = os.path.join(folder, "app_settings.json")
        window.showMaximized = MagicMock()
        window.showFullScreen = MagicMock()
        self.addCleanup(window.deleteLater)
        return window

    def test_older_settings_file_loads_and_saves_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "app_settings.json")
            old_text = json.dumps(OLDER_SETTINGS, indent=2, ensure_ascii=False)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(old_text)
            loaded = self.main_window.read_app_settings(path)
            self.assertEqual(loaded, OLDER_SETTINGS)
            self.assertEqual(list(loaded), list(OLDER_SETTINGS))
            self.make_window(loaded, folder).save_app_settings()
            with open(path, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), old_text)

    def test_missing_damaged_or_wrong_type_settings_give_empty(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "app_settings.json")
            self.assertEqual(self.main_window.read_app_settings(path), {})
            self.assertFalse(os.path.exists(path))
            for text in ("{broken", "[1, 2]", "null"):
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text)
                with patch("builtins.print"):
                    self.assertEqual(self.main_window.read_app_settings(path), {})
                with open(path, encoding="utf-8") as handle:
                    self.assertEqual(handle.read(), text)   # never rewritten on load

    def test_save_failure_warns_instead_of_raising(self):
        with tempfile.TemporaryDirectory() as folder:
            window = self.make_window({"a": 1}, folder)
            window.app_settings_path = folder   # a folder: writing fails
            with patch.object(self.main_window.QMessageBox, "warning") as warning:
                window.save_app_settings()
            self.assertIn("app_settings.json", warning.call_args.args[2])

    def test_geometry_round_trip_keeps_other_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            first = self.make_window({"hf_token": "x", "window_geometry": "old"}, folder)
            first.resize(731, 517)
            first.remember_window_state()
            saved = first.app_settings
            self.assertEqual(list(saved), ["hf_token", "window_geometry", "window_maximized",
                                           "window_fullscreen"])
            self.assertEqual(saved["hf_token"], "x")
            self.assertIsInstance(saved["window_geometry"], str)
            self.assertIs(saved["window_maximized"], False)
            first.save_app_settings()

            settings = self.main_window.read_app_settings(first.app_settings_path)
            second = self.make_window(settings, folder)
            second.restore_window_state()
            self.assertEqual((second.width(), second.height()), (731, 517))
            second.showMaximized.assert_not_called()
            second.showFullScreen.assert_not_called()

    def test_saved_state_is_shown(self):
        with tempfile.TemporaryDirectory() as folder:
            window = self.make_window({"window_maximized": True, "window_fullscreen": True}, folder)
            window.restore_window_state()
            window.showMaximized.assert_called_once()
            window.showFullScreen.assert_not_called()
            window = self.make_window({"window_fullscreen": True}, folder)
            window.restore_window_state()
            window.showFullScreen.assert_called_once()

    def test_corrupt_geometry_is_reported_not_raised(self):
        with tempfile.TemporaryDirectory() as folder:
            for value in ("ü not base64", "abc", 42, None, ""):
                window = self.make_window({"window_geometry": value}, folder)
                with patch("builtins.print") as printed:
                    window.restore_window_state()
                if value == "ü not base64" or value == "abc":
                    self.assertIn("window", printed.call_args.args[0])
                else:
                    printed.assert_not_called()

    def test_status_line_elides_and_refits(self):
        line = self.main_window.StatusLine("Status: Initializing...")
        self.addCleanup(line.deleteLater)
        line.resize(300, 20)
        self.assertEqual(line.text(), "Status: Initializing...")   # kept until the first message
        message = "A long status message " * 20
        line.show_message(message)
        self.assertEqual(line.toolTip(), message)
        short = line.text()
        self.assertTrue(short.endswith("…") and len(short) < len(message))
        line.resize(3000, 20)
        line.fit_message()
        self.assertGreater(len(line.text()), len(short))
        line.show_message("")
        self.assertEqual(line.text(), "")

    def test_geometry_text_helpers(self):
        self.assertEqual(self.main_window.geometry_to_text(b"\x01\xd9\xd0\xcb"), "AdnQyw==")
        self.assertEqual(self.main_window.geometry_from_text("AdnQyw=="), b"\x01\xd9\xd0\xcb")
        self.assertIsNone(self.main_window.geometry_from_text(""))
        self.assertIsNone(self.main_window.geometry_from_text(None))


if __name__ == "__main__":
    unittest.main()
