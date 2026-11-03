"""Derive build_v091_final.py from build_v091_cut2.py: the same edit, with the temporary logo card replaced
by the MythologIQ Labs opener frames (make_opener.py). The opener keeps cut 2's 2.6 s, so nothing after it moves."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE / "build_v091_cut2.py").read_text(encoding="utf-8")


def R(a, b):
    global s
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


R('"""Assemble review cut 2 of', '"""Assemble the final cut (review cut 2 with the MythologIQ Labs opener) of')
R("    python build_v091_cut2.py <capture dir> <out dir> <end card png> <fonts dir> <opener mark png> <guide music wav>",
  "    python build_v091_final.py <capture dir> <out dir> <end card png> <fonts dir> <opener.json> <guide music wav>")
R('NAME = "sonic-rift-world-in-sound-v091-review-2"', 'NAME = "sonic-rift-world-in-sound-v091-final"')
R("OPEN = 2.6                                   # temporary opener (static exact mark, labelled TEMPORARY)",
  "OPEN = 2.6                                   # MythologIQ Labs opener (make_opener.py), dissolving into the film")
R('''# ---- picture: temporary opener, the session's frames, the approved end card ----''',
  '''# ---- picture: the MythologIQ Labs opener, the session's frames, the approved end card ----''')
R('''open(os.path.join(overlay, "opener.txt"), "w", encoding="utf-8").write(
    "TEMPORARY OPENER  ·  MythologIQ Labs mark pending owner verification  ·  not for publication")
opener = os.path.abspath(os.path.join(OUT, "opener_temporary.jpg"))
subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=0x0b1020:s=2400x1350",
                "-i", os.path.abspath(MARK), "-filter_complex",
                "[1]format=rgba[m];[0][m]overlay=(W-w)/2:(H-h)/2-40,"
                "drawtext=fontfile=Inter-SemiBold.ttf:textfile=opener.txt:fontsize=40:fontcolor=0xffb020:"
                "box=1:boxcolor=0x000000@0.6:boxborderw=18:x=(w-text_w)/2:y=h-160",
                "-frames:v", "1", "-q:v", "2", opener], check=True, cwd=overlay)''',
  '''opener_spec = json.load(open(MARK, encoding="utf-8"))     # MARK is the opener.json from make_opener.py
opener_frames = opener_spec["frames"]
assert abs(len(opener_frames) / opener_spec["fps"] - OPEN) < 1e-6, "the opener must keep cut 2's length"''')
R('''    handle.write(f"file '{opener.replace(os.sep, '/')}'\\nduration {OPEN:.4f}\\n")''',
  '''    for path in opener_frames:
        handle.write(f"file '{path}'\\nduration {1 / opener_spec['fps']:.6f}\\n")''')
(HERE / "build_v091_final.py").write_text(s, encoding="utf-8")
print("build_v091_final.py written")
