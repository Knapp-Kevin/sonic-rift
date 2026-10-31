"""A worker that won't shut down is ended with everything it started, not just its launcher."""

import os
import subprocess
import sys
import time
import unittest
from unittest import mock

from this_voice_thing.engines import worker as engine_worker
from this_voice_thing.engines.worker import WorkerProcess, kill_tree


class KillTreeTests(unittest.TestCase):
    def test_close_kills_the_tree_when_shutdown_times_out(self):
        worker = WorkerProcess.__new__(WorkerProcess)
        worker.process = mock.Mock(pid=4242)
        worker.process.poll.return_value = None
        worker.process.wait.side_effect = [subprocess.TimeoutExpired("python", 10), 0]
        worker.request = mock.Mock(side_effect=RuntimeError("no reply"))
        with mock.patch.object(engine_worker.os, "name", "nt"), \
                mock.patch.object(engine_worker.subprocess, "run") as run:
            worker.close()
        self.assertEqual(run.call_args[0][0], ["taskkill", "/T", "/F", "/PID", "4242"])

    def test_elsewhere_the_process_is_killed_directly(self):
        process = mock.Mock(pid=7)
        process.poll.return_value = None
        with mock.patch.object(engine_worker.os, "name", "posix"), \
                mock.patch.object(engine_worker.subprocess, "run") as run:
            kill_tree(process)
        run.assert_not_called()
        process.kill.assert_called_once()

    @unittest.skipUnless(os.name == "nt", "Windows process trees")
    def test_a_real_child_process_does_not_survive(self):
        """A parent that starts a long-lived child, like a venv launcher does."""
        child_code = "import time; time.sleep(120)"
        parent_code = ("import subprocess, sys, time; "
                       f"p = subprocess.Popen([sys.executable, '-c', {child_code!r}]); "
                       "print(p.pid, flush=True); time.sleep(120)")
        parent = subprocess.Popen([sys.executable, "-c", parent_code], stdout=subprocess.PIPE, text=True,
                                  creationflags=engine_worker.NO_WINDOW)
        child_pid = int(parent.stdout.readline())
        kill_tree(parent)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and _alive(child_pid):
            time.sleep(0.1)
        self.assertIsNotNone(parent.poll())
        self.assertFalse(_alive(child_pid), "the child process outlived its parent")


class StderrPumpTests(unittest.TestCase):
    def test_a_line_the_log_cannot_write_does_not_stop_the_pump(self):
        worker = WorkerProcess.__new__(WorkerProcess)
        worker.tag, worker.skip = "fake", lambda _line: False
        worker.process = mock.Mock(stderr=iter(["first\n", "emoji \U0001f50d\n", "last\n"]))
        written = []

        def log(text):
            if "\U0001f50d" in text:
                text.encode("cp1252")         # what print() does on a cp1252 console
            written.append(text)
        worker.log = log
        worker._pump_stderr()
        self.assertEqual(written, ["[fake] first", "[fake] last"])


def _alive(pid):
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
    return str(pid) in out


if __name__ == "__main__":
    unittest.main()
