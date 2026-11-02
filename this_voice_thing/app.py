"""Start-up entry point: copies console output into a timestamped log under logs/, runs the
main window, and shows a message box (with the log's location) if start-up fails."""

import ctypes
import datetime
import os
import runpy
import sys
import traceback

from this_voice_thing import paths
from this_voice_thing.core.console_io import stream_encoding, stream_is_terminal

MB_ICONERROR = 0x10
STARTUP_ERROR_TITLE = "Sonic Rift: Startup Error"


def make_startup_log_path(now=None):
    """A new log file path, logs/app_startup_<YYYYmmdd_HHMMSS>.log; creates logs/ if needed."""
    when = now or datetime.datetime.now()
    name = "app_startup_" + when.strftime("%Y%m%d_%H%M%S") + ".log"
    os.makedirs(paths.LOGS_DIR, exist_ok=True)
    return os.path.join(paths.LOGS_DIR, name)


LOG_PATH = make_startup_log_path(datetime.datetime.now())


def _try_console(console, method, *args):
    """Call a console stream method; no console (pythonw gives None) or a failing one is ignored."""
    try:
        getattr(console, method)(*args)
    except Exception:
        pass


class TeeFile:
    """A sys.stdout/sys.stderr stand-in that copies everything into the startup log too.

    The log gets each write first (flushed, so it survives a crash); the console copy is
    best effort."""

    def __init__(self, console, log_file):
        self.console, self.log = console, log_file

    @property
    def encoding(self):
        return stream_encoding(self.console)

    def _to_log(self, text=""):
        if self.log.closed:
            return   # a background thread may still print after main() has closed the log
        if text:
            self.log.write(text)
        self.log.flush()

    def write(self, value):
        text = f"{value}"
        self._to_log(text)
        _try_console(self.console, "write", text)
        return len(text)

    def flush(self):
        self._to_log()
        _try_console(self.console, "flush")

    def isatty(self):
        return stream_is_terminal(self.console)


def startup_error_text(log_path, last_error):
    """What the start-up error box says."""
    return "\n\n".join(("Sonic Rift failed to start.", f"Log file:\n{log_path}", f"Last error:\n{last_error}"))


def _windows_message_box(text, title, icon):
    """Show a native message box; does nothing off Windows or without a desktop session."""
    user32 = getattr(getattr(ctypes, "windll", None), "user32", None)
    if user32 is None:
        return
    try:
        user32.MessageBoxW(None, text, title, icon)
    except Exception:
        pass


def show_startup_error(log_path, last_error):
    """Tell the user start-up failed, where the log is, and the last error line."""
    _windows_message_box(startup_error_text(log_path, last_error), STARTUP_ERROR_TITLE, MB_ICONERROR)


def main():
    previous = sys.stdout, sys.stderr
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        sys.stdout, sys.stderr = (TeeFile(console, log_file) for console in (sys.__stdout__, sys.__stderr__))
        try:
            _run_window()
        finally:
            # The window ends with sys.exit(), which leaves this block and closes the log.
            # Put the original streams back first: Python flushes sys.stdout at shutdown, and a
            # flush into the closed log turned every clean exit into exit code 120.
            sys.stdout, sys.stderr = previous


def _startup_banner():
    """What the log records about this launch before anything else."""
    return "\n".join((
        f"Launching Sonic Rift at {datetime.datetime.now().isoformat()}",
        "Python executable: " + sys.executable,
        "Working directory: " + os.getcwd(),
    ))


def _report_startup_failure(details):
    """Log the full traceback and show its final line to the user."""
    print(details)
    lines = details.strip().splitlines()
    show_startup_error(LOG_PATH, lines[-1] if lines else "Unknown startup error")


def _run_window():
    print(_startup_banner())
    try:
        runpy.run_module("this_voice_thing.ui.main_window", run_name="__main__", alter_sys=True)
    except Exception:
        _report_startup_failure(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
