"""Shared plumbing for engines that run in their own Python environment.

Each such engine lives in engines/<name>/ with its own .venv and a worker
script that speaks JSON lines: one request per line on stdin, one reply per
line on stdout, with library output on stderr (shown on the Log page).
"""

import glob
import json
import os
import shutil
import subprocess
import threading

import numpy as np

from this_voice_thing import paths

BASE_DIR = paths.ROOT  # engines/<name>/ live in the project folder
TORCH_INDEX = "https://download.pytorch.org/whl/cu128"
TORCH_PACKAGES = ["torch==2.8.0", "torchaudio==2.8.0"]
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def engine_dir(name):
    return os.path.join(BASE_DIR, "engines", name)


def venv_python(name):
    return os.path.join(engine_dir(name), ".venv", "Scripts" if os.name == "nt" else "bin",
                        "python.exe" if os.name == "nt" else "python")


def _run(command, log, name):
    log("Running: " + " ".join(command[1:5]) + " ...")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
    for line in process.stdout:
        log(line.rstrip())
    if process.wait() != 0:
        raise RuntimeError(f"{name} engine install step failed: {' '.join(command[1:4])}")


def _managed_python(uv, version):
    """Path of a uv-managed CPython `version`, installing it if needed.

    On Windows uv (0.12) links e.g. cpython-3.12 -> cpython-3.12.15 with a junction it
    then fails to follow ("Missing expected target directory for Python minor version
    link"), so `uv venv --python 3.12` fails even though the interpreter is there.
    Pointing uv at the real interpreter works.
    """
    root = subprocess.run([uv, "python", "dir"], capture_output=True, text=True,
                          creationflags=NO_WINDOW).stdout.strip()

    def found():
        exe = "python.exe" if os.name == "nt" else os.path.join("bin", "python3")
        matches = sorted(glob.glob(os.path.join(root, f"cpython-{version}.*", exe)))
        return matches[-1] if matches else None

    if not found():
        subprocess.run([uv, "python", "install", version], capture_output=True, creationflags=NO_WINDOW)
    return found()


# Deepest file in an engine environment, relative to engines/<name> (a transformers module).
_DEEPEST_RELATIVE = len(r"\.venv\Lib\site-packages	ransformers\modelsudio_spectrogram_transformer"
                        r"\configuration_audio_spectrogram_transformer.py") + 10


def long_paths_enabled():
    if os.name != "nt":
        return True
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem") as key:
            return bool(winreg.QueryValueEx(key, "LongPathsEnabled")[0])
    except OSError:
        return False


def check_path_length(name):
    """Windows' 260-character path limit silently drops files deep inside an environment
    (the install "succeeds", then imports fail). Refuse up front with a way out."""
    if os.name == "nt" and not long_paths_enabled() and len(engine_dir(name)) + _DEEPEST_RELATIVE > 259:
        raise RuntimeError(
            f"This app's folder path is too long for the {name} engine on Windows "
            f"({len(engine_dir(name))} characters to engines\\{name}). Move the app to a shorter "
            "folder (e.g. C:\\Apps\\ThisVoiceThing), or turn on Windows long paths "
            "(LongPathsEnabled), then install again.")


def install_env(name, package_steps, log=print, python_version="3.11", torch_packages=None):
    """Create engines/<name>/.venv with CUDA PyTorch, then install each step's packages.

    PyTorch comes from the uv cache when another engine already downloaded it. Engines
    whose upstream pins a different torch or Python pass their own.
    """
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError(f"uv was not found on PATH; it is needed to install the {name} engine.")
    check_path_length(name)
    os.makedirs(engine_dir(name), exist_ok=True)
    python = venv_python(name)
    steps = [[uv, "venv", os.path.join(engine_dir(name), ".venv"), "--python", python_version, "--clear"],
             [uv, "pip", "install", "--python", python, *(torch_packages or TORCH_PACKAGES),
              "--index-url", TORCH_INDEX]]
    steps += [[uv, "pip", "install", "--python", python, *packages] for packages in package_steps]
    try:
        _run(steps[0], log, name)
    except RuntimeError:
        interpreter = _managed_python(uv, python_version)
        if not interpreter:
            raise
        log(f"Retrying with the Python {python_version} interpreter at {interpreter}")
        _run(steps[0][:-3] + ["--python", interpreter, "--clear"], log, name)
    for command in steps[1:]:
        _run(command, log, name)


class WorkerProcess:
    """One long-lived worker process; requests are serialised with a lock."""

    def __init__(self, python, script, tag, log=print, skip=None, env=None):
        """skip(line) -> True hides a noisy stderr line from the Log page; env adds variables."""
        self.tag = tag
        self.log = log
        self.skip = skip or (lambda _line: False)
        self.lock = threading.Lock()
        env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8", **(env or {}))
        self.process = subprocess.Popen(
            [python, script], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1, env=env,
            creationflags=NO_WINDOW)
        threading.Thread(target=self._pump_stderr, daemon=True).start()
        ready = self._read_reply()
        if not ready.get("ok"):
            raise RuntimeError(ready.get("error", f"The {tag} worker failed to start."))
        self.device = "cuda" if ready.get("cuda") else "cpu"

    def _pump_stderr(self):
        for line in self.process.stderr:
            line = line.rstrip()
            if line and not self.skip(line):
                self.log(f"[{self.tag}] {line}")

    def _read_reply(self):
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError(f"The {self.tag} worker stopped unexpectedly. See the Log page.")
        return json.loads(line)

    def request(self, **payload):
        with self.lock:
            if self.process.poll() is not None:
                raise RuntimeError(f"The {self.tag} worker is not running.")
            self.process.stdin.write(json.dumps(payload) + "\n")
            self.process.stdin.flush()
            reply = self._read_reply()
        if not reply.get("ok"):
            raise RuntimeError(reply.get("error", f"{self.tag} request failed."))
        return reply

    def close(self):
        if self.process.poll() is None:
            try:
                self.request(cmd="shutdown")
            except Exception:
                pass
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()


class PerthWatermark:
    """Adds the inaudible Perth watermark Chatterbox uses, for engines that don't mark audio."""

    def __init__(self):
        self._watermarker = None

    def apply(self, wav, sr, engine_name):
        try:
            if self._watermarker is None:
                import perth
                self._watermarker = perth.PerthImplicitWatermarker()
            return np.asarray(self._watermarker.apply_watermark(wav, sample_rate=sr), dtype=np.float32)
        except Exception as exc:
            print(f"Perth watermark could not be applied to {engine_name} audio: {exc}")
            return wav
