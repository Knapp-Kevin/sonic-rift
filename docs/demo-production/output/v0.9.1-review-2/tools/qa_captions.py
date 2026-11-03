"""QA with Sonic Rift's own transcriber (Whisper large-v3-turbo, as installed in v0.9.1):
1. every spoken caption is heard in the finished soundtrack, inside its own time window;
2. each newly generated character take says its scripted line;
3. the music files (take D and the new on-camera take) contain no recognisable words.

    <install>\.venv\Scripts\python.exe qa_captions.py <install dir> <out dir> <capture dir>
"""
import json
import os
import re
import sys

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

APP, OUT, CAPTURE = sys.argv[1:4]
sys.path.insert(0, APP)
from this_voice_thing.core import transcription  # noqa: E402

NAME = os.environ.get("CUT_NAME", "sonic-rift-world-in-sound-v091-review")
T = transcription.Transcriber()


def words(text):
    return [w for w in re.sub(r"[^a-z' ]", " ", text.lower().replace("’", "'")).split() if w]


def mono16(audio, rate):
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    return resample_poly(audio, 16000, rate).astype(np.float32)


def heard(samples):
    return T.transcribe(samples, language="en").text


def parse_vtt(path):
    cues, lines = [], open(path, encoding="utf-8").read().split("\n\n")[1:]
    for block in lines:
        rows = [r for r in block.strip().split("\n") if r]
        if len(rows) < 3:
            continue
        a, b = [sum(float(x) * m for x, m in zip(t.split(":"), (3600, 60, 1))) for t in rows[1].split(" --> ")]
        cues.append((a, b, " ".join(rows[2:])))
    return cues


report = {"captions": [], "takes": [], "music": []}
track, rate = sf.read(f"{OUT}/soundtrack.wav", dtype="float32")
for a, b, text in parse_vtt(f"{OUT}/{NAME}.en.vtt"):
    m = re.match(r"<v ([^>]+)>(.*)", text)
    if not m:
        continue
    speaker, line = m.group(1), m.group(2)
    piece = track[max(0, int((a - 0.25) * rate)): int((b + 0.35) * rate)]
    got = heard(mono16(piece, rate))
    want = words(line)
    missing = [w for w in want if w not in words(got)]
    report["captions"].append({"at": round(a, 2), "speaker": speaker, "caption": line, "heard": got,
                               "missing_words": missing, "pass": not missing})
log = json.load(open(f"{CAPTURE}/log_dark.json", encoding="utf-8"))["film"]
for e in log["events"]:
    if e["role"] in ("Keeper", "Traveler", "Keeper (clone)"):
        audio, r = sf.read(e["path"], dtype="float32")
        got = heard(mono16(audio, r))
        missing = [w for w in words(e["text"]) if w not in words(got)]
        report["takes"].append({"role": e["role"], "script": e["text"], "heard": got, "missing_words": missing,
                                "pass": not missing})
for label, path in (("take D (kept, used in the scene)", next(e["source"] for e in log["events"] if e["role"] == "Music (kept)")),
                    ("new on-camera take", next(e["path"] for e in log["events"] if e["role"] == "Music (new take)"))):
    audio, r = sf.read(path, dtype="float32")
    got = heard(mono16(audio, r))
    report["music"].append({"file": label, "heard": got, "words": len(words(got))})
report["summary"] = {
    "captions_pass": sum(c["pass"] for c in report["captions"]), "captions_total": len(report["captions"]),
    "takes_pass": sum(t["pass"] for t in report["takes"]), "takes_total": len(report["takes"]),
    "music_words": {m["file"]: m["words"] for m in report["music"]}}
json.dump(report, open(f"{OUT}/qa_transcription.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(report["summary"], ensure_ascii=False))
for c in report["captions"]:
    if not c["pass"]:
        print("CAPTION MISS", c["at"], c["speaker"], c["caption"], "| heard:", c["heard"])
for t in report["takes"]:
    print("TAKE", t["role"], "| heard:", t["heard"], "| missing:", t["missing_words"])
for m in report["music"]:
    print("MUSIC", m["file"], "| heard:", repr(m["heard"]))
