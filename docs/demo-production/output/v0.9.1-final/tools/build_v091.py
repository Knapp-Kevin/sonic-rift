"""Assemble the v0.9.1 review cut of 'A World in Sound: Evening Tide, The Beacon' from a
film_v091.py session (same assembly as the approved film's build_film.py, plus a temporary opener).

    python build_v091.py <capture dir> <out dir> <end card png> <fonts dir> <opener mark png>

Writes: sonic-rift-world-in-sound-v091-review.mp4 (sound on), ...-silent.mp4 (burned-in beat titles
and speaker-labelled lines), ...en.vtt, stems/*.wav, soundtrack.wav, timeline.json, poster.jpg.
"""
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.signal import resample_poly

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import captions  # noqa: E402

FILM, OUT, END_CARD, FONTS, MARK = sys.argv[1:6]
NAME = "sonic-rift-world-in-sound-v091-review"
os.makedirs(OUT, exist_ok=True)
RATE = 48000
OPEN = 2.6                                   # temporary opener (static exact mark, labelled TEMPORARY)
log = json.load(open(os.path.join(FILM, "log_dark.json"), encoding="utf-8"))["film"]
events = log["events"]
end_at, end_len = log["end_card"]
lines = open(os.path.join(FILM, "frames.txt"), encoding="utf-8").read().rstrip("\n").split("\n")[:-1]
frame_list = [[lines[i][6:-1], float(lines[i + 1].split()[1])] for i in range(0, len(lines), 2)]
# ---- real-time playback: a played section (an audition or the scene) was grabbed frame by frame
# against the wall clock, but each 2400x1350 grab takes longer than 1/12 s, so fewer frames exist
# than the time it played. Stretch each such run of frames back to the time it really played (the
# audio's length), so the picture (the playhead) stays in step with the sound; later sounds move too.
NOM = 1 / 12
retimed = []
for e in sorted(events, key=lambda x: x["at"]):
    role = e["role"]
    if role in ("Keeper", "Traveler", "Keeper (clone)"):
        played = e["file_seconds"] + 0.6
    elif role in ("Ocean", "Music (new take)", "Music (kept)", "Studio mix"):
        played = e["length"]
    else:
        continue
    t, i = 0.0, 0
    while i < len(frame_list) and t + frame_list[i][1] / 2 < e["at"]:
        t += frame_list[i][1]
        i += 1
    n = 0
    while i + n < len(frame_list) and abs(frame_list[i + n][1] - NOM) < 1e-3:
        n += 1
    shown = n * NOM
    if n == 0 or played <= shown + 0.02:
        continue
    for f in frame_list[i:i + n]:
        f[1] *= played / shown
    delta = played - shown
    for other in events:
        if other["at"] > e["at"] + 0.005:
            other["at"] = round(other["at"] + delta, 3)
    log["chapters"] = [(round(at + delta, 3) if at > e["at"] + 0.005 else at, name) for at, name in log["chapters"]]
    end_at += delta
    retimed.append({"role": role, "frames": n, "shown_seconds": round(shown, 2), "played_seconds": round(played, 2)})
original_durations = [d for _p, d in frame_list]
session_chapters = list(log["chapters"])
for e in events:
    e["session_at"] = e["at"]

# ---- dead air: inside any stretch with no sound longer than MAX_QUIET, shorten the held frames
# (single frames shown for 0.3 s or more); typing, drags and playback (1/12 s frames) are untouched.
# Every later sound moves with the picture, so sync is kept. Ambience runs on to the next sound,
# so it counts as sound.
MAX_QUIET, MIN_HOLD = 1.2, 0.3


def sounding_spans():
    spans = []
    for i, e in enumerate(events):
        end = e["at"] + e["length"]
        if e["role"] in ("Ocean", "Studio mix"):
            nxt = events[i + 1]["at"] if i + 1 < len(events) else end_at
            end = max(end, min(nxt - 0.1, e["at"] + e["file_seconds"]))
        spans.append((e["at"], end))
    return sorted(spans)


squeezed = []
quiet, cursor = [], 0.0
for a, b in sounding_spans() + [(end_at, end_at)]:
    if a - cursor > MAX_QUIET:
        quiet.append((cursor, a))
    cursor = max(cursor, b)
k = 0
total_cut = 0.0
while k < len(quiet):
    q0, q1 = quiet[k]
    k += 1
    export_at = next((at for at, name in session_chapters if name == "Export the mix"), None)
    export_at = None if export_at is None else export_at - total_cut   # in the trimmed timeline so far
    if export_at is not None and q1 > export_at - 0.5:
        continue                                   # the export result stays on screen as recorded
    t, holds = 0.0, []
    for f in frame_list:
        if f[1] >= MIN_HOLD and t >= q0 - 1e-6 and t + f[1] <= q1 + 1e-6:
            holds.append(f)
        t += f[1]
    limit_here = 0.6 if q0 < 1e-6 else MAX_QUIET        # the first line follows the opener quickly
    excess = (q1 - q0) - limit_here
    if excess <= 0:
        continue
    cut = 0.0
    spare = sum(f[1] - MIN_HOLD for f in holds)
    if spare > 0:
        scale = min(1.0, excess / spare)
        for f in holds:
            d = (f[1] - MIN_HOLD) * scale
            f[1] -= d
            cut += d
    # still too long: typing in the quiet stretch may run up to 1.5x faster (never playback,
    # which always has sound)
    if excess - cut > 0.05:
        t, quick = 0.0, []
        for f in frame_list:
            if f[1] < MIN_HOLD and t >= q0 + cut * 0 - 1e-6 and t + f[1] <= q1 - cut + 1e-6:
                quick.append(f)
            t += f[1]
        room = sum(f[1] / 3 for f in quick)               # 1.5x faster = each frame 2/3 as long
        if room > 0:
            share = min(1.0, (excess - cut) / room)
            for f in quick:
                d = f[1] / 3 * share
                f[1] -= d
                cut += d
    for e in events:
        if e["at"] >= q1 - 0.005:
            e["at"] = round(e["at"] - cut, 3)
    end_at -= cut
    total_cut += cut
    squeezed.append({"quiet": [round(q0, 2), round(q1, 2)], "removed_seconds": round(cut, 2)})
    quiet[k:] = [(x0 - cut, x1 - cut) for x0, x1 in quiet[k:]]   # later quiet windows move too



def mapped(t_orig):
    """Where a moment of the session lands after the dead-air pass (through the frame durations)."""
    acc_old = acc_new = 0.0
    for old, (_p, new) in zip(original_durations, frame_list):
        if acc_old + old > t_orig + 1e-6:
            return acc_new + min(new, max(0.0, t_orig - acc_old) * (new / old if old else 1))
        acc_old += old
        acc_new += new
    return acc_new + (t_orig - acc_old)


log["chapters"] = [(round(mapped(at), 3), name) for at, name in session_chapters]   # chapters follow the picture
for e in events:   # sync check: every sound sits on its own moment of the picture
    drift = abs(mapped(e["session_at"]) - e["at"])
    if drift > 0.06:
        raise SystemExit(f"sync drift {drift:.3f} s: {e['role']} at {e['session_at']}")

for e in events:
    e["at"] = round(e["at"] + OPEN, 3)
end_at += OPEN
total = round(end_at + end_len, 3)
TARGET = {"Guide": -20.0, "Keeper": -20.0, "Traveler": -20.0, "Keeper (clone)": -20.0, "Ocean": -27.0,
          "Music (new take)": -27.0, "Music (kept)": -27.0, "Studio mix": -19.0, "Brand narrator": -19.0}
STEM = {"Guide": "narration", "Brand narrator": "narration", "Keeper": "dialogue", "Traveler": "dialogue",
        "Keeper (clone)": "dialogue", "Ocean": "effects", "Music (new take)": "music", "Music (kept)": "music",
        "Studio mix": "scene-mix"}
meter = pyln.Meter(RATE)

# Ambience and the scene mix run on toward the next sound and fade out smoothly (never cut off);
# music auditions stop where they stopped on screen, with a fade.
for i, e in enumerate(events):
    e["fade_out"] = e["fade"]
    if e["role"] in ("Ocean", "Studio mix"):
        nxt = events[i + 1]["at"] if i + 1 < len(events) else total
        room = min(nxt - 0.1 - e["at"], e["file_seconds"])
        if room > e["length"]:
            e["length"] = round(room, 3)
        e["fade_out"] = min(3.0, e["length"] / 3)
    elif e["role"].startswith("Music"):
        e["fade_out"] = min(0.8, e["length"] / 3)

spans = [(e["at"], e["at"] + e["length"], e["role"]) for e in events]
for a in spans:
    for b in spans:
        if a is not b and a[0] < b[1] and b[0] < a[1]:
            raise SystemExit(f"overlap: {a} / {b}")


def curve(n):
    return (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n, dtype=np.float32)))[:, None]


length = int((total + 1) * RATE)
mix = np.zeros((length, 2), dtype=np.float32)
stems = {name: np.zeros((length, 2), dtype=np.float32) for name in set(STEM.values())}
levels = []
for e in events:
    audio, rate = sf.read(e["path"], dtype="float32", always_2d=True)
    if audio.shape[1] == 1:
        audio = np.repeat(audio, 2, axis=1)
    if rate != RATE:
        audio = resample_poly(audio, RATE, rate, axis=0).astype(np.float32)
    piece = audio[: int(e["length"] * RATE)].copy()
    loud = meter.integrated_loudness(piece) if len(piece) > RATE * 0.5 else -20.0
    piece *= 10 ** ((TARGET[e["role"]] - loud) / 20)
    fade_in, fade_out = int(e["fade"] * RATE), int(e["fade_out"] * RATE)
    if fade_in + fade_out < len(piece):
        if fade_in:
            piece[:fade_in] *= curve(fade_in)
        if fade_out:
            piece[-fade_out:] *= curve(fade_out)[::-1]
    at = int(e["at"] * RATE)
    end = min(length, at + len(piece))
    mix[at:end] += piece[: end - at]
    stems[STEM[e["role"]]][at:end] += piece[: end - at]
    levels.append(dict(role=e["role"], at=e["at"], seconds=round(len(piece) / RATE, 2), source_lufs=round(loud, 1),
                       target_lufs=TARGET[e["role"]], source=e.get("source", "")))
mix = mix[: int(total * RATE)]
whole = meter.integrated_loudness(mix)
gain = 10 ** ((-16.0 - whole) / 20)
mix *= gain


def limit(audio, ceiling=0.891, lookahead=0.005, release=0.08):
    from scipy.ndimage import maximum_filter1d
    from scipy.signal import lfilter
    peak = maximum_filter1d(np.max(np.abs(audio), axis=1), size=int(lookahead * RATE) * 2 + 1)
    want = np.minimum(1.0, ceiling / np.maximum(peak, 1e-9))
    a = np.exp(-1.0 / (release * RATE))
    smooth = lfilter([1 - a], [1, -a], 1 - want)
    g = 1 - np.maximum(smooth, 1 - want)
    return (audio * g[:, None]).astype(np.float32), float(1 - g.min())


mix, reduction = limit(mix)
peak = float(np.max(np.abs(mix)))
soundtrack = os.path.join(OUT, "soundtrack.wav")
sf.write(soundtrack, mix, RATE, subtype="PCM_24")
os.makedirs(os.path.join(OUT, "stems"), exist_ok=True)
for name, data in stems.items():   # the same gain as the soundtrack, before the limiter
    sf.write(os.path.join(OUT, "stems", f"{name}.wav"), (data[: int(total * RATE)] * gain).astype(np.float32),
             RATE, subtype="PCM_24")

# ---- picture: temporary opener, the session's frames, the approved end card ----
overlay = os.path.join(OUT, "overlay")
os.makedirs(overlay, exist_ok=True)
for f in ("Inter-SemiBold.ttf", "Inter-Medium.ttf"):
    shutil.copyfile(os.path.join(FONTS, f), os.path.join(overlay, f))
open(os.path.join(overlay, "opener.txt"), "w", encoding="utf-8").write(
    "TEMPORARY OPENER  ·  MythologIQ Labs mark pending owner verification  ·  not for publication")
opener = os.path.abspath(os.path.join(OUT, "opener_temporary.jpg"))
subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=0x0b1020:s=2400x1350",
                "-i", os.path.abspath(MARK), "-filter_complex",
                "[1]format=rgba[m];[0][m]overlay=(W-w)/2:(H-h)/2-40,"
                "drawtext=fontfile=Inter-SemiBold.ttf:textfile=opener.txt:fontsize=40:fontcolor=0xffb020:"
                "box=1:boxcolor=0x000000@0.6:boxborderw=18:x=(w-text_w)/2:y=h-160",
                "-frames:v", "1", "-q:v", "2", opener], check=True, cwd=overlay)
card = os.path.abspath(os.path.join(OUT, "end_card.jpg"))
subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", END_CARD, "-vf", "scale=2400:1350",
                "-q:v", "2", card], check=True)
shown = sum(d for _p, d in frame_list)
frames = os.path.join(OUT, "frames.txt")
with open(frames, "w", encoding="utf-8") as handle:
    handle.write(f"file '{opener.replace(os.sep, '/')}'\nduration {OPEN:.4f}\n")
    for path, duration in frame_list:
        handle.write(f"file '{path}'\nduration {duration:.4f}\n")
    gap = round(end_at - OPEN - shown, 4)
    if gap > 0.01:
        handle.write(f"file '{frame_list[-1][0]}'\nduration {gap}\n")
    handle.write(f"file '{card.replace(os.sep, '/')}'\nduration {end_len:.4f}\nfile '{card.replace(os.sep, '/')}'\n")

# ---- captions (speaker-tagged) ----
cues = []
for e in events:
    if e["role"] == "Ocean":
        cues.append((e["at"], e["at"] + e["length"], "[Ocean waves]"))
    elif e["role"] == "Music (new take)":
        cues.append((e["at"], e["at"] + e["length"], "[A new music take: cello and strings]"))
    elif e["role"] == "Music (kept)":
        cues.append((e["at"], e["at"] + e["length"], "[The kept theme: cello and strings]"))
    elif e["role"] == "Studio mix":
        cues.append((e["at"], e["at"] + 1.9, "[Ocean waves and music under the scene]"))
    else:
        for start, end, text in captions.spoken_cues(e["path"], e["text"], e["at"], 0.0, e["length"]):
            cues.append((start, end, f"<v {e['role']}>{text}"))
mix_event = next(e for e in events if e["role"] == "Studio mix")
dialogue = next(t for t in log["clips"] if t[0] == "Dialogue")[1]
speakers = ["Keeper", "Traveler", "Keeper (clone)"]
take_events = {e["role"]: e for e in events if e["role"] in speakers}
for speaker, clip in zip(speakers, dialogue):
    start_s, length_s = clip[1], clip[2]
    e = take_events[speaker]
    for a, b, line in captions.spoken_cues(e["path"], e["text"], mix_event["at"] + start_s, 0.0, length_s):
        cues.append((a, b, f"<v {speaker}>{line}"))
vtt = os.path.join(OUT, f"{NAME}.en.vtt")
cues = captions.build(cues, vtt)

# ---- encode ----
common = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", frames]
scale = "scale=1920:1080:flags=lanczos,fps=30,format=yuv420p"
main_mp4 = os.path.join(OUT, f"{NAME}.mp4")
subprocess.run(common + ["-i", soundtrack, "-vf", scale, "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{total:.3f}", main_mp4],
               check=True)
TITLES = {
    "An empty world": "A new, empty project in the Studio",
    "Give it a keeper": "Speech  ·  the Keeper speaks",
    "Someone answers": "Speech  ·  the Traveler answers",
    "Give it a shoreline": "Sounds  ·  generated ocean waves",
    "Keep a character's voice": "Voices › Clone  ·  the Keeper's voice, kept for a new line",
    "Give it music": "Music  ·  a new take, then the kept cello theme on its own track",
    "Arrange, balance and save": "Studio  ·  place the lines, set each lane's level, Check balance, save",
    "Hear the scene": "The scene plays: voices, the sea and the music",
    "Export the mix": "Export  ·  a mastered mix and one stem per track",
}
filters, n = [scale], 0
chapters = [(round(at + OPEN, 2), name) for at, name in log["chapters"]]
for i, (at, name) in enumerate(chapters):
    if name not in TITLES:
        continue
    end = chapters[i + 1][0] if i + 1 < len(chapters) else end_at
    path = f"t{n:02d}.txt"
    open(os.path.join(overlay, path), "w", encoding="utf-8").write(TITLES[name])
    filters.append(f"drawtext=fontfile=Inter-SemiBold.ttf:textfile={path}:fontsize=34:fontcolor=0x9fe9f7:"
                   f"box=1:boxcolor=0x0b1020@0.82:boxborderw=16:x=(w-text_w)/2:y=h-232:"
                   f"enable='between(t,{at:.2f},{end:.2f})'")
    n += 1
for start, end, text in cues:
    plain = text.replace("<v ", "").replace(">", ": ", 1) if text.startswith("<v ") else text
    path = f"c{n:02d}.txt"
    open(os.path.join(overlay, path), "w", encoding="utf-8").write(plain)
    filters.append(f"drawtext=fontfile=Inter-Medium.ttf:textfile={path}:fontsize=38:fontcolor=white:"
                   f"box=1:boxcolor=0x000000@0.70:boxborderw=16:x=(w-text_w)/2:y=h-150:"
                   f"enable='between(t,{start:.2f},{end:.2f})'")
    n += 1
silent = os.path.abspath(os.path.join(OUT, f"{NAME}-silent-captioned.mp4"))
subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
                "-i", os.path.abspath(frames), "-vf", ",".join(filters), "-c:v", "libx264", "-preset", "slow",
                "-crf", "18", "-an", "-movflags", "+faststart", "-t", f"{total:.3f}", silent], check=True, cwd=overlay)
poster_src = os.path.join(FILM, "45_studio_balanced.png")
subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", poster_src, "-vf",
                "scale=1920:1080:flags=lanczos", "-q:v", "2", os.path.join(OUT, f"{NAME}-poster.jpg")], check=True)
json.dump(dict(total=total, opener_seconds=OPEN, end_card=[end_at, end_len], levels=levels, dead_air_removed=squeezed, playback_retimed=retimed,
               mix_lufs_before=round(whole, 2), limiter_max_reduction_db=round(-20 * np.log10(1 - reduction + 1e-9), 2),
               final_peak=round(peak, 4), cues=cues, chapters=chapters, events=events),
          open(os.path.join(OUT, "timeline.json"), "w", encoding="utf-8"), indent=1)
print(json.dumps(dict(total=total, cues=len(cues), files=sorted(os.listdir(OUT)))))
