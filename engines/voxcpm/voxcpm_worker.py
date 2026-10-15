"""VoxCPM worker: runs inside engines/voxcpm/.venv and serves the main app.

Protocol: one JSON request per line on stdin, one JSON reply per line on the
original stdout. Everything libraries print goes to stderr (the app's Log page).

Requests:
  {"cmd": "load", "model_id": "openbmb/VoxCPM2"}
  {"cmd": "generate", "text": ..., "out_path": path, "style": "...",
   "reference_wav": path | null, "prompt_wav": path | null, "prompt_text": str | null,
   "seed": int, "cfg_value": 2.0, "timesteps": 10}
  {"cmd": "ping"} / {"cmd": "shutdown"}

A style or voice description goes in parentheses before the text, which is how
VoxCPM2 takes voice design and style control.
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


def numba_free_load(path, sr=22050, mono=True, **_ignored):
    """librosa.load for one file: soundfile + soxr (librosa's own default resampler)."""
    import numpy as np
    import soundfile as sf
    import soxr
    audio, rate = sf.read(path, dtype="float32", always_2d=True)
    audio = audio.mean(axis=1) if mono else audio
    if sr is not None and rate != sr:
        length = int(np.ceil(len(audio) * sr / rate))   # librosa's output length
        audio = soxr.resample(audio, rate, sr, quality="HQ")
        if len(audio) < length:
            audio = np.pad(audio, [(0, length - len(audio))] + [(0, 0)] * (audio.ndim - 1))
        audio = audio[:length]
        rate = sr
    audio = audio if mono else audio.T
    return np.ascontiguousarray(audio, dtype=np.float32), rate


def numba_free_trim(y, top_db=60, ref=None, frame_length=2048, hop_length=512, **_ignored):
    """librosa.effects.trim: drop leading/trailing frames quieter than top_db below ref
    (centred, zero-padded RMS frames, as librosa computes them)."""
    import numpy as np
    y = np.asarray(y, dtype=np.float32)
    mono = y if y.ndim == 1 else y.mean(axis=0)
    padded = np.pad(mono, frame_length // 2)
    count = 1 + max(0, len(padded) - frame_length) // hop_length
    frames = np.lib.stride_tricks.sliding_window_view(padded, frame_length)[::hop_length][:count]
    power = np.mean(frames.astype(np.float64) ** 2, axis=1)
    reference = (ref or np.max)(power) if len(power) else 0.0
    amin = 1e-10
    db = 10.0 * np.log10(np.maximum(amin, power)) - 10.0 * np.log10(max(amin, reference))
    loud = np.flatnonzero(db > -top_db)   # never empty: the loudest frame is at 0 dB
    start = int(loud[0] * hop_length)
    end = int(min(mono.shape[-1], (loud[-1] + 1) * hop_length))
    return y[..., start:end], (start, end)


def use_numba_free_audio():
    """VoxCPM2 reads reference clips with librosa.load (and trims with librosa.effects.trim),
    which import Numba. Windows Smart App Control and other Application Control policies can
    block Numba's compiled modules, and then every cloning request fails with "Numba could
    not be imported". Give VoxCPM the same two calls without Numba."""
    import types
    from voxcpm.model import voxcpm2
    voxcpm2.librosa = types.SimpleNamespace(load=numba_free_load,
                                            effects=types.SimpleNamespace(trim=numba_free_trim))


def main():
    import numpy as np
    import soundfile as sf
    import torch
    from huggingface_hub import snapshot_download
    from voxcpm import VoxCPM

    use_numba_free_audio()

    cuda = torch.cuda.is_available()
    state = {"model": None, "model_id": None}

    def load(model_id):
        if state["model_id"] == model_id:
            return
        state.update(model=None, model_id=None)
        if cuda:
            torch.cuda.empty_cache()
        # Use the local copy when it's there so loading works offline.
        try:
            source = snapshot_download(model_id, local_files_only=True)
        except Exception:
            source = snapshot_download(model_id)
        # The optional denoiser downloads a separate ModelScope model; it isn't needed
        # for clean reference clips. optimize (torch.compile) needs Triton, which Windows
        # lacks: it gave no speed-up on an RTX 5070 Ti and added ~9 s to loading.
        model = VoxCPM.from_pretrained(source, load_denoiser=False, optimize=False)
        state.update(model=model, model_id=model_id,
                     v2=type(model.tts_model).__name__ == "VoxCPM2Model")
        # The first generation pays a one-time GPU warm-up (~15 s); do it while loading.
        model.tts_model.generate(target_text="Hello, this is a warm-up sentence.", max_len=10)

    def generate(req):
        model = state["model"]
        if model is None:
            raise RuntimeError("No VoxCPM model is loaded.")
        if req.get("seed"):
            torch.manual_seed(int(req["seed"]))
            if cuda:
                torch.cuda.manual_seed_all(int(req["seed"]))
        text = req["text"].strip()
        style = (req.get("style") or "").strip().strip("()")
        if style:
            text = f"({style}){text}"
        kwargs = dict(text=text, cfg_value=float(req.get("cfg_value", 2.0)),
                      inference_timesteps=int(req.get("timesteps", 10)))
        if req.get("prompt_wav") and req.get("prompt_text"):
            kwargs.update(prompt_wav_path=req["prompt_wav"], prompt_text=req["prompt_text"])
        if req.get("reference_wav"):
            if state["v2"]:
                kwargs["reference_wav_path"] = req["reference_wav"]
            elif "prompt_wav_path" not in kwargs:
                raise ValueError("This older VoxCPM model clones only with a transcript of the clip. "
                                 "Fill in Clip transcript, or use VoxCPM2.")
        if style and not state["v2"]:
            raise ValueError("Styles and voice design need VoxCPM2; this is an older VoxCPM model.")
        wav = model.generate(**kwargs)
        wav = np.asarray(wav, dtype=np.float32).reshape(-1)
        sr = int(model.tts_model.sample_rate)
        sf.write(req["out_path"], wav, sr, subtype="FLOAT")
        return {"path": req["out_path"], "sr": sr, "seconds": round(len(wav) / sr, 2)}

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
                reply(ok=True, sample_rate=int(state["model"].tts_model.sample_rate), v2=state["v2"])
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
    except Exception as exc:
        traceback.print_exc()
        reply(ok=False, event="fatal", error=f"{type(exc).__name__}: {exc}")
