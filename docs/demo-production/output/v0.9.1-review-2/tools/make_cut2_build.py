"""Derive build_v091_cut2.py from build_v091.py (cut 1's build stays as it is)."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE / "build_v091.py").read_text(encoding="utf-8")


def R(a, b):
    global s
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


R('''"""Assemble the v0.9.1 review cut of 'A World in Sound: Evening Tide, The Beacon' from a
film_v091.py session (same assembly as the approved film's build_film.py, plus a temporary opener).

    python build_v091.py <capture dir> <out dir> <end card png> <fonts dir> <opener mark png>
''', '''"""Assemble review cut 2 of 'A World in Sound: Evening Tide, The Beacon' from the same film_v091.py
session as cut 1 (build_v091.py), with the owner's cut-1 notes applied:
  1. a Guide line explains the music step (generated in Sonic Rift 0.9.1, Guide voice, Qwen3 cloning);
  2. the new take's audition is short and crossfades into the kept take D, which plays on as it
     reaches its own Studio track (no fade-out-then-restart);
  3. the ending: the export result stays readable, the tagline follows the end card promptly, take D
     continues softly under the ending and fades out shortly after the last word.

    python build_v091_cut2.py <capture dir> <out dir> <end card png> <fonts dir> <opener mark png> <guide music wav>
''')
R('FILM, OUT, END_CARD, FONTS, MARK = sys.argv[1:6]\nNAME = "sonic-rift-world-in-sound-v091-review"',
  'FILM, OUT, END_CARD, FONTS, MARK, GUIDE_MUSIC = sys.argv[1:7]\nNAME = "sonic-rift-world-in-sound-v091-review-2"')

STORY = (HERE / "cut2_story.py").read_text(encoding="utf-8")
R('original_durations = [d for _p, d in frame_list]\nsession_chapters',
  STORY + '\noriginal_durations = [d for _p, d in frame_list]\nsession_chapters')
R('''total = round(end_at + end_len, 3)
TARGET = {''', '''total = round(end_at + end_len, 3)
TARGET = {"Music (ending)": -29.0, ''')
R('''"Studio mix": "scene-mix"}''', '''"Studio mix": "scene-mix", "Music (ending)": "music"}''')
R('''    if e["role"] in ("Ocean", "Studio mix"):
        nxt = events[i + 1]["at"] if i + 1 < len(events) else total
        room = min(nxt - 0.1 - e["at"], e["file_seconds"])
        if room > e["length"]:
            e["length"] = round(room, 3)
        e["fade_out"] = min(3.0, e["length"] / 3)
    elif e["role"].startswith("Music"):
        e["fade_out"] = min(0.8, e["length"] / 3)''', '''    if e["role"] in ("Ocean", "Studio mix", "Music (kept)"):
        nxt = next((o["at"] for o in events[i + 1:] if o["role"] != "Music (ending)"), total)
        room = min(nxt - 0.1 - e["at"], e["file_seconds"])
        if room > e["length"]:
            e["length"] = round(room, 3)
        e["fade_out"] = min(2.5 if e["role"] == "Music (kept)" else 3.0, e["length"] / 3)
    elif e["role"] == "Music (new take)":
        e["fade_out"] = e["crossfade_out"]                    # fades under the selection, into take D
    elif e["role"] == "Music (ending)":
        e["fade_out"] = min(2.6, e["length"] / 2)''')
R('''spans = [(e["at"], e["at"] + e["length"], e["role"]) for e in events]
for a in spans:
    for b in spans:
        if a is not b and a[0] < b[1] and b[0] < a[1]:
            raise SystemExit(f"overlap: {a} / {b}")''', '''# No voice may overlap another voice (the Studio mix holds the scene's dialogue). Music may crossfade
# between takes and sit under the closing tagline; it never sits under a Guide or character line.
VOICES = {"Guide", "Keeper", "Traveler", "Keeper (clone)", "Brand narrator", "Studio mix"}
spans = [(e["at"], e["at"] + e["length"], e["role"]) for e in events]
for a in spans:
    for b in spans:
        if a is b or not (a[0] < b[1] - 1e-6 and b[0] < a[1] - 1e-6):
            continue
        if (a[2].startswith("Music") and b[2].startswith("Music")) or {a[2], b[2]} == {"Music (ending)", "Brand narrator"}:
            continue
        if a[2] in VOICES or b[2] in VOICES:
            raise SystemExit(f"overlap: {a} / {b}")''')
R('''    piece = audio[: int(e["length"] * RATE)].copy()''', '''    start = int(e.get("offset", 0.0) * RATE)
    piece = audio[start: start + int(e["length"] * RATE)].copy()''')
(HERE / "build_v091_cut2.py").write_text(s, encoding="utf-8")
print("build_v091_cut2.py written")
