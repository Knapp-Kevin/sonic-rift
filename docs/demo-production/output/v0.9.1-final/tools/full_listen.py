import sys, json
import numpy as np, soundfile as sf
from scipy.signal import resample_poly
sys.path.insert(0, sys.argv[1])
from this_voice_thing.core import transcription
a, r = sf.read(sys.argv[2], dtype="float32"); a = a.mean(1)
t = transcription.Transcriber().transcribe(resample_poly(a, 16000, r).astype(np.float32), language="en")
for s in t.segments: print(f"{s.start:6.2f}-{s.end:6.2f}  {s.text}")
