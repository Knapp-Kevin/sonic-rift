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
    """Call a console stream method, ignoring a missing console (pythonw) or one that fails."""
    if console is None:
        return
    try:
        getattr(console, method)(*args)
    except Exception:
        pass


class TeeFile:
    """A sys.stdout/sys.stderr stand-in that copies everything into the startup log too.

    The log gets each write first (flushed, so it survives a crash); the console copy is
    best effort."""

    def __init__(self, console, log_file):
        self.console = console
        self.log = log_file
        self.encoding = stream_encoding(console)

    def _log_is_open(self):
        # A background thread may still print after main() has closed the log.
        return not self.log.closed

    def write(self, value):
        text = str(value)
        if self._log_is_open():
            self.log.write(text)
            self.log.flush()
        _try_console(self.console, "write", text)
        return len(text)

    def flush(self):
        if self._log_is_open():
            self.log.flush()
        _try_console(self.console, "flush")

    def isatty(self):
        return stream_is_terminal(self.console)


def show_startup_error(log_path, last_error):
    """Tell the user start-up failed, where the log is, and the last error line.

    Uses a Windows message box; elsewhere (or if that fails) it does nothing."""
    sections = (
        "Sonic Rift failed to start.",
        "Log file:\n" + str(log_path),
        "Last error:\n" + str(last_error),
    )
    try:
        user32 = ctypes.windll.user32
        user32.MessageBoxW(None, "\n\n".join(sections), STARTUP_ERROR_TITLE, MB_ICONERROR)
    except Exception:
        pass


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
