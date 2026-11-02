"""ACE-Step 1.5 worker: runs inside engines/acestep/.venv and serves the main app.

The environment is built from upstream's uv.lock at the commit pinned in
this_voice_thing/core/music/catalog.py; weights live in engines/acestep/checkpoints.
The app starts this worker with Hugging Face offline, and load refuses to run if a
weight file is missing, so nothing is ever downloaded from here.

Protocol: one JSON request per line on stdin, one JSON reply per line on the
original stdout. Everything libraries print goes to stderr (the app's log).

Requests:
  {"cmd": "load", "project_root": "...engines/acestep", "dit": "acestep-v15-turbo", "lm": "acestep-5Hz-lm-1.7B"}
  {"cmd": "generate", "out_path": "...wav", "caption": "...", "lyrics": "", "instrumental": true,
   "seconds": 30, "seed": 7, "bpm": null, "key": "", "time_signature": null, "plan": true}
  {"cmd": "ping"} / {"cmd": "shutdown"}
"""

import json
import os
import shutil
import sys
import tempfile
import time
import traceback
import warnings

# ACE-Step writes ./.cache (progress estimates); keep it in engines/acestep, not the app folder.
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")   # no Triton on Windows; run eagerly

REPLY = sys.stdout
sys.stdout = sys.stderr
warnings.filterwarnings("ignore")


def reply(**payload):
    REPLY.write(json.dumps(payload) + "\n")
    REPLY.flush()


def main():
    import soundfile as sf
    import torch
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import worker_limits
    worker_limits.apply(torch)    # the app's CPU-thread and GPU-memory limits
    from acestep.handler import AceStepHandler
    from acestep.inference import GenerationConfig, GenerationParams, generate_music
    from acestep.llm_inference import LLMHandler

    cuda = torch.cuda.is_available()
    state = {"dit": None, "lm": None}

    def load(req):
        root = req["project_root"]
        checkpoints = os.path.join(root, "checkpoints")
        for name in (req["dit"], req["lm"], "vae", "Qwen3-Embedding-0.6B"):
            if not os.path.isdir(os.path.join(checkpoints, name)):
                raise RuntimeError(f"Model folder {name} is missing from {checkpoints}; install the engine again.")
        started = time.monotonic()
        # Everything resident needs more than 16 GB (it spilled into shared memory and ran at
        # ~2% GPU). Moving every idle part to the CPU fits but costs 25-70 s of copying per
        # take, so by default only the planner (the biggest part, idle while rendering) moves.
        offload_dit = bool(req.get("offload_dit", True))
        offload_lm = bool(req.get("offload_lm", True))
        dit = AceStepHandler()
        message, ok = dit.initialize_service(project_root=root, config_path=req["dit"],
                                             device="cuda" if cuda else "cpu", offload_to_cpu=offload_dit)
        if not ok:
            raise RuntimeError(f"ACE-Step model didn't load: {message}")
        lm = LLMHandler()
        message, ok = lm.initialize(checkpoint_dir=checkpoints, lm_model_path=req["lm"], backend="pt",
                                    device="cuda" if cuda else "cpu", offload_to_cpu=offload_lm)
        if not ok:
            raise RuntimeError(f"ACE-Step planner didn't load: {message}")
        state.update(dit=dit, lm=lm)
        return {"device": "cuda" if cuda else "cpu", "seconds": round(time.monotonic() - started, 1)}

    def generate(req):
        if state["dit"] is None:
            raise RuntimeError("No ACE-Step model is loaded.")
        if cuda:
            torch.cuda.reset_peak_memory_stats()
        instrumental = bool(req.get("instrumental", True))
        params = GenerationParams(
            task_type="text2music", caption=req["caption"],
            lyrics="[Instrumental]" if instrumental else req.get("lyrics", ""),
            instrumental=instrumental, duration=float(req["seconds"]), seed=int(req["seed"]),
            bpm=req.get("bpm"), keyscale=req.get("key") or "",
            timesignature=str(req["time_signature"]) if req.get("time_signature") else "",
            thinking=bool(req.get("plan", True)))
        config = GenerationConfig(batch_size=1, use_random_seed=False, seeds=[int(req["seed"])],
                                  audio_format="wav")
        work = tempfile.mkdtemp(prefix="acestep_take_")
        started = time.monotonic()
        try:
            result = generate_music(state["dit"], state["lm"], params, config, save_dir=work)
            if not result.success or not result.audios:
                raise RuntimeError(result.error or result.status_message or "ACE-Step returned no audio.")
            audio = result.audios[0]
            source = audio.get("path")
            if source and os.path.isfile(source):
                shutil.move(source, req["out_path"])
            else:
                tensor = audio["tensor"].float().cpu().numpy().T
                sf.write(req["out_path"], tensor, int(audio.get("sample_rate", 48000)), subtype="FLOAT")
        finally:
            shutil.rmtree(work, ignore_errors=True)
        info = sf.info(req["out_path"])
        lm_meta = (result.extra_outputs or {}).get("lm_metadata") or {}
        if isinstance(lm_meta, list):
            lm_meta = lm_meta[0] if lm_meta else {}
        chosen = {name: lm_meta.get(name) for name in ("bpm", "keyscale", "timesignature", "duration",
                                                       "vocal_language") if lm_meta.get(name) not in (None, "")}
        memory = {}
        if cuda:
            memory = {"peak_mb": torch.cuda.max_memory_allocated() // 2**20,
                      "reserved_mb": torch.cuda.memory_reserved() // 2**20}
            torch.cuda.empty_cache()
        return {"path": req["out_path"], "sample_rate": int(info.samplerate), "channels": int(info.channels),
                "seconds": round(info.frames / info.samplerate, 3), "elapsed": round(time.monotonic() - started, 2),
                "chosen": {k: (v if isinstance(v, (int, float, str)) else str(v)) for k, v in chosen.items()},
                "memory": memory}

    reply(ok=True, event="ready", cuda=cuda, device=torch.cuda.get_device_name(0) if cuda else "cpu")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            cmd = req.get("cmd")
            if cmd == "load":
                reply(ok=True, **load(req))
            elif cmd == "generate":
                reply(ok=True, **generate(req))
            elif cmd == "ping":
                reply(ok=True)
            elif cmd == "shutdown":
                reply(ok=True)
                break
            else:
                reply(ok=False, error=f"Unknown command: {cmd}")
        except Exception as exc:
            traceback.print_exc()
            reply(ok=False, error=f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # import failures: tell the app instead of dying silently
        traceback.print_exc()
        reply(ok=False, error=f"{type(exc).__name__}: {exc}")
