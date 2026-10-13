"""Stable Audio 3 worker: runs inside engines/sa3/.venv and serves the main app.

Protocol: one JSON request per line on stdin, one JSON reply per line on the
original stdout. Everything libraries print goes to stderr (the app's Log page).

Requests:
  {"cmd": "load", "model": "small-sfx", "device": "cuda" | "cpu" | null}
  {"cmd": "generate", "prompt": "...", "seconds": 30, "seed": 7, "steps": 8,
   "negative_prompt": "", "out_path": "...wav",
   "inpaint_path": "...wav", "inpaint_start": 28.5, "inpaint_end": 31.5}   (inpaint optional)
  {"cmd": "ping"} / {"cmd": "shutdown"}
"""

import json
import sys
import traceback
import warnings

REPLY = sys.stdout
sys.stdout = sys.stderr
warnings.filterwarnings("ignore")


def reply(**payload):
    REPLY.write(json.dumps(payload) + "\n")
    REPLY.flush()


def main():
    import numpy as np
    import soundfile as sf
    import torch
    from stable_audio_3 import StableAudioModel

    cuda = torch.cuda.is_available()
    state = {"model": None, "name": None, "device": None}

    def load(name, device):
        device = device or ("cuda" if cuda else "cpu")
        if state["name"] == name and state["device"] == device:
            return
        state.update(model=None, name=None)
        if cuda:
            torch.cuda.empty_cache()
        # Gated on Hugging Face: uses HF_TOKEN from the app, after the user accepted the terms.
        model = StableAudioModel.from_pretrained(name, device=device)
        state.update(model=model, name=name, device=device)

    def generate(req):
        model = state["model"]
        if model is None:
            raise RuntimeError("No Stable Audio model is loaded.")
        kwargs = dict(prompt=req["prompt"], duration=float(req["seconds"]), seed=int(req.get("seed", -1)),
                      steps=int(req.get("steps", 8)), batch_size=1)
        if req.get("negative_prompt"):
            kwargs["negative_prompt"] = req["negative_prompt"]
        if req.get("inpaint_path"):
            wav, sr = sf.read(req["inpaint_path"], dtype="float32", always_2d=True)
            kwargs.update(inpaint_audio=(sr, torch.from_numpy(np.ascontiguousarray(wav.T))),
                          inpaint_mask_start_seconds=float(req["inpaint_start"]),
                          inpaint_mask_end_seconds=float(req["inpaint_end"]))
        with torch.inference_mode():
            audio = model.generate(**kwargs)
        sample_rate = int(model.model.sample_rate)
        wav = audio[0].float().cpu().numpy().T          # (frames, channels)
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
                load(req.get("model", "small-sfx"), req.get("device"))
                reply(ok=True, device=state["device"])
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
