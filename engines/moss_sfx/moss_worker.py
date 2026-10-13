"""MOSS-SoundEffect v2 worker: runs inside engines/moss_sfx/.venv and serves the main app.

The model's VAE ships as a pickled .pth (loading it runs code), which is one more
reason this stays in its own process and environment.

Protocol: one JSON request per line on stdin, one JSON reply per line on the
original stdout. Everything libraries print goes to stderr (the app's Log page).

Requests:
  {"cmd": "load", "model_id": "OpenMOSS-Team/MOSS-SoundEffect-v2.0"}
  {"cmd": "generate", "prompt": "...", "seconds": 30, "seed": 7, "steps": 100,
   "cfg_scale": 4.0, "negative_prompt": "", "out_path": "...wav"}
  {"cmd": "ping"} / {"cmd": "shutdown"}
"""

import json
import os
import sys
import traceback
import warnings

# torch.compile needs Triton, which has no official Windows build; run eagerly instead.
os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")

REPLY = sys.stdout
sys.stdout = sys.stderr
warnings.filterwarnings("ignore")


def reply(**payload):
    REPLY.write(json.dumps(payload) + "\n")
    REPLY.flush()


def main():
    import soundfile as sf
    import torch
    from moss_soundeffect_v2 import MossSoundEffectPipeline

    cuda = torch.cuda.is_available()
    state = {"pipe": None, "model_id": None}

    def load(model_id):
        if state["model_id"] == model_id:
            return
        state.update(pipe=None, model_id=None)
        if cuda:
            torch.cuda.empty_cache()
        pipe = MossSoundEffectPipeline.from_pretrained(
            model_id, torch_dtype=torch.bfloat16 if cuda else torch.float32,
            device="cuda" if cuda else "cpu")
        state.update(pipe=pipe, model_id=model_id)

    def generate(req):
        pipe = state["pipe"]
        if pipe is None:
            raise RuntimeError("No MOSS-SoundEffect model is loaded.")
        seconds = min(30.0, float(req["seconds"]))
        with torch.inference_mode():
            audio = pipe(prompt=req["prompt"], seconds=seconds, seed=int(req.get("seed", 0)),
                         num_inference_steps=int(req.get("steps", 100)),
                         cfg_scale=float(req.get("cfg_scale", 4.0)),
                         negative_prompt=req.get("negative_prompt", ""))
        wav = audio[0].float().cpu().numpy().T          # (frames, channels)
        sample_rate = int(pipe.sample_rate)
        sf.write(req["out_path"], wav, sample_rate, subtype="FLOAT")
        return {"path": req["out_path"], "sample_rate": sample_rate,
                "seconds": round(len(wav) / sample_rate, 3)}

    reply(ok=True, event="ready", cuda=cuda, device=torch.cuda.get_device_name(0) if cuda else "cpu")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            cmd = req.get("cmd")
            if cmd == "load":
                load(req["model_id"])
                reply(ok=True, device="cuda" if cuda else "cpu")
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
