"""Main-app side of the music engines.

Each engine runs in its own environment (engines/<dir>/.venv) built from the upstream
lock file at a pinned commit, with weights fetched at a pinned revision into
engines/<dir>/checkpoints. The worker runs with Hugging Face offline, so a start never
downloads anything; installing is the only step that does, after the user consents.
"""

import os
import shutil
import subprocess
from dataclasses import dataclass

from this_voice_thing.core.music import catalog
from this_voice_thing.engines import worker as engine_worker


@dataclass(frozen=True)
class MusicSpec:
    key: str
    directory: str              # engines/<directory>
    worker: str
    python_version: str
    required_files: tuple       # relative to checkpoints/; all present = downloaded
    load_request: dict


SPECS = {
    "ace_step_15": MusicSpec(
        key="ace_step_15", directory="acestep", worker="acestep_worker.py", python_version="3.12",
        required_files=("acestep-v15-turbo/model.safetensors", "acestep-5Hz-lm-1.7B/model.safetensors",
                        "Qwen3-Embedding-0.6B/model.safetensors", "vae/diffusion_pytorch_model.safetensors"),
        load_request={"cmd": "load", "dit": "acestep-v15-turbo", "lm": "acestep-5Hz-lm-1.7B"}),
}


def engine_dir(key):
    return engine_worker.engine_dir(SPECS[key].directory)


def checkpoints_dir(key):
    return os.path.join(engine_dir(key), "checkpoints")


def worker_path(key):
    return os.path.join(engine_dir(key), SPECS[key].worker)


def missing_files(key):
    """Weights the engine needs that aren't on disk yet (relative paths)."""
    root = checkpoints_dir(key)
    return [name for name in SPECS[key].required_files if not os.path.isfile(os.path.join(root, name))]


def is_installed(key):
    spec = SPECS[key]
    return (os.path.exists(engine_worker.venv_python(spec.directory)) and os.path.exists(worker_path(key))
            and not missing_files(key))


def _run(command, log, cwd=None, env=None):
    log("Running: " + " ".join(str(part) for part in command[:4]) + " ...")
    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace",
                               creationflags=engine_worker.NO_WINDOW)
    for line in process.stdout:
        log(line.rstrip())
    if process.wait() != 0:
        raise RuntimeError(f"Music engine install step failed: {' '.join(str(p) for p in command[:3])}")


def install(key, log=print):
    """Source at its pinned commit, the environment from upstream's lock file, then the
    weights at their pinned revision. Safe to run again: finished steps are kept."""
    spec, engine = SPECS[key], catalog.ENGINES[key]
    uv, git = shutil.which("uv"), shutil.which("git")
    if not uv or not git:
        raise RuntimeError("Installing a music engine needs uv and git on PATH.")
    engine_worker.check_path_length(spec.directory)
    root = engine_dir(key)
    source = os.path.join(root, "src")
    if not os.path.isdir(os.path.join(source, ".git")):
        _run([git, "clone", "--quiet", engine.source_url, source], log)
    _run([git, "-C", source, "checkout", "--quiet", engine.source_revision], log)
    env = dict(os.environ, UV_PROJECT_ENVIRONMENT=os.path.join(root, ".venv"))
    sync = [uv, "sync", "--frozen", "--no-dev", "--python"]
    try:
        _run(sync + [spec.python_version], log, cwd=source, env=env)
    except RuntimeError:
        interpreter = engine_worker._managed_python(uv, spec.python_version)   # uv's Windows link bug
        if not interpreter:
            raise
        _run(sync + [interpreter], log, cwd=source, env=env)
    script = ("import sys\nfrom huggingface_hub import snapshot_download\n"
              "snapshot_download(sys.argv[1], revision=sys.argv[2], local_dir=sys.argv[3])\n")
    _run([engine_worker.venv_python(spec.directory), "-c", script, engine.repo_id, engine.model_revision,
          checkpoints_dir(key)], log)
    if missing_files(key):
        raise RuntimeError(f"{engine.label} downloaded, but these files are missing: {', '.join(missing_files(key))}")


class MusicModel:
    """A running music worker. generate_take() writes one WAV and returns the worker's reply."""

    def __init__(self, key, log=print):
        engine = catalog.ENGINES[key]
        if not is_installed(key):
            raise RuntimeError(f"{engine.label} isn't installed yet.")
        self.key, self.engine, self.spec = key, engine, SPECS[key]
        env = {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "ACESTEP_CHECKPOINTS_DIR": "",
               "TORCHDYNAMO_DISABLE": "1", "TOKENIZERS_PARALLELISM": "false"}
        self.worker = engine_worker.WorkerProcess(
            engine_worker.venv_python(self.spec.directory), worker_path(key), self.spec.directory, log,
            skip=lambda line: "warn" in line.lower(), env=env)
        try:
            reply = self.worker.request(**self.spec.load_request, project_root=engine_dir(key))
        except Exception:
            self.worker.close()
            raise
        self.device = reply.get("device", self.worker.device)
        self.load_seconds = reply.get("seconds", 0.0)

    def generate_take(self, out_path, caption, seconds, seed, lyrics="", instrumental=True, bpm=None,
                      key="", time_signature=None):
        return self.worker.request(
            cmd="generate", out_path=out_path, caption=caption, lyrics=lyrics, instrumental=bool(instrumental),
            seconds=float(seconds), seed=int(seed), bpm=bpm, key=key, time_signature=time_signature)

    def alive(self):
        return self.worker.process.poll() is None

    def terminate(self):
        """Stop at once, mid-take (Cancel): the worker process ends and the model unloads.

        A venv's python.exe on Windows is a launcher that runs the real interpreter as a child,
        so the whole process tree is ended; killing only the launcher left the model on the GPU."""
        if not self.alive():
            return
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.worker.process.pid)],
                           capture_output=True, creationflags=engine_worker.NO_WINDOW)
        else:
            self.worker.process.kill()
        self.worker.process.wait(timeout=10)

    def close(self):
        self.worker.close()
