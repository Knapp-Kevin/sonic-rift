"""Pick the new Guide take closest to the approved Guide narration: voice similarity (Chatterbox voice
encoder, as installed with Sonic Rift), exact wording (Sonic Rift's transcriber) and speaking pace."""
import glob
import json
import re
import sys

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

APP, TAKES, APPROVED, OUT = sys.argv[1:5]
sys.path.insert(0, APP)
from chatterbox.models.voice_encoder import VoiceEncoder  # noqa: E402
from this_voice_thing.core import transcription  # noqa: E402

LINE = "Now give the scene its own music. Describe the mood, generate a few possibilities, and keep the one that feels right."
APPROVED_LINES = {"01": "A world can begin with just a few words.", "03": "Then someone answers from across the water.",
                  "05": "Give their conversation a shoreline.", "07": "A character can return without losing their voice.",
                  "09": "Place every line where it belongs, and let the sea sit underneath.",
                  "10": "A voice... an answer... the sound of the sea. Together, they become a scene."}
from safetensors.torch import load_file  # noqa: E402
VE = glob.glob(r"C:\Users\krkna\.cache\huggingface\hub\models--ResembleAI--chatterbox\snapshots\*\ve.safetensors")[0]
enc = VoiceEncoder()
enc.load_state_dict(load_file(VE))
enc.eval()
T = transcription.Transcriber()


def load16(path):
    a, r = sf.read(path, dtype="float32")
    a = a.mean(axis=1) if a.ndim == 2 else a
    return resample_poly(a, 16000, r).astype(np.float32)


def speech_seconds(a, rate=16000):
    hop = 320
    rms = np.array([np.sqrt(np.mean(a[i:i + hop] ** 2) + 1e-12) for i in range(0, len(a), hop)])
    return float((20 * np.log10(rms) > -40).sum() * hop / rate)


def words(t):
    return re.sub(r"[^a-z' ]", " ", t.lower()).split()


approved = sorted(glob.glob(f"{APPROVED}/*-guide-*.wav"))
ref = VoiceEncoder.utt_to_spk_embed(enc.embeds_from_wavs([load16(p) for p in approved], sample_rate=16000))
rates = [len(words(APPROVED_LINES[p.split("\\")[-1].split("/")[-1][:2]])) / speech_seconds(load16(p)) for p in approved]
results = []
for path in sorted(glob.glob(f"{TAKES}/guide-music-take*.wav")):
    a = load16(path)
    emb = enc.embeds_from_wavs([a], sample_rate=16000)[0]
    sim = float(np.dot(ref, emb) / (np.linalg.norm(ref) * np.linalg.norm(emb)))
    heard = T.transcribe(a, language="en").text
    missing = [w for w in words(LINE) if w not in words(heard)]
    rate = len(words(LINE)) / speech_seconds(a)
    results.append({"take": path.replace("\\", "/").split("/")[-1], "seconds": round(len(a) / 16000, 2),
                    "similarity_to_approved_guide": round(sim, 4), "words_per_second": round(rate, 2),
                    "heard": heard, "missing_words": missing})
others = {"approved_guide_words_per_second": round(float(np.mean(rates)), 2)}
# Rank: wording must be complete; then voice similarity, then pace closest to the approved lines
ranked = sorted(results, key=lambda r: (len(r["missing_words"]) > 0, -r["similarity_to_approved_guide"],
                                        abs(r["words_per_second"] - others["approved_guide_words_per_second"])))
json.dump({"line": LINE, "approved_reference": approved, **others, "takes": results, "picked": ranked[0]["take"]},
          open(OUT, "w", encoding="utf-8"), indent=1)
print(json.dumps(others))
for r in results:
    print(r["take"], r["seconds"], "sim", r["similarity_to_approved_guide"], "wps", r["words_per_second"], "missing", r["missing_words"], "|", r["heard"])
print("picked", ranked[0]["take"])
