from pathlib import Path
p = Path("build_v091_cut2.py"); s = p.read_text(encoding="utf-8")
def R(a, b):
    global s
    assert s.count(a) == 1, a[:60]
    s = s.replace(a, b)
R('''    elif e["role"] == "Music (new take)":
        cues.append((e["at"], e["at"] + e["length"], "[A new music take: cello and strings]"))
    elif e["role"] == "Music (kept)":
        cues.append((e["at"], e["at"] + e["length"], "[The kept theme: cello and strings]"))''',
'''    elif e["role"] == "Music (new take)":
        cues.append((e["at"], e["at"] + e["length"] - e["crossfade_out"] + 0.3, "[A new take: cello and strings]"))
    elif e["role"] == "Music (kept)":
        cues.append((e["at"] - 1.4, e["at"] + e["length"], "[Take D, kept earlier: cello and strings]"))
    elif e["role"] == "Music (ending)":
        cues.append((e["at"], e["at"] + 1.6, "[Music continues under the ending]"))''')
R('''    "Give it music": "Music  ·  a new take, then the kept cello theme on its own track",''',
  '''    "Give it music": "Music  ·  describe the mood, try a take, keep the one that feels right",''')
R("dead_air_removed=squeezed, playback_retimed=retimed,", "dead_air_removed=squeezed, playback_retimed=retimed, story_edits=story,")
p.write_text(s, encoding="utf-8"); print("patched")
