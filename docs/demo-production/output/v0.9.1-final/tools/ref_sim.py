import glob, sys
import numpy as np, soundfile as sf
from scipy.signal import resample_poly
sys.path.insert(0, sys.argv[1])
from chatterbox.models.voice_encoder import VoiceEncoder
from safetensors.torch import load_file
enc = VoiceEncoder(); enc.load_state_dict(load_file(glob.glob(r"C:\Users\krkna\.cache\huggingface\hub\models--ResembleAI--chatterbox\snapshots\*\ve.safetensors")[0])); enc.eval()
def l(p):
    a, r = sf.read(p, dtype="float32"); a = a.mean(1) if a.ndim == 2 else a
    return resample_poly(a, 16000, r).astype(np.float32)
ps = sorted(glob.glob(sys.argv[2] + "/*-guide-*.wav")); E = enc.embeds_from_wavs([l(p) for p in ps], sample_rate=16000)
for i, p in enumerate(ps):
    rest = VoiceEncoder.utt_to_spk_embed(np.delete(E, i, axis=0)); s = float(E[i] @ rest / np.linalg.norm(E[i]) / np.linalg.norm(rest))
    print(p.replace("\\", "/").split("/")[-1], round(s, 4))
