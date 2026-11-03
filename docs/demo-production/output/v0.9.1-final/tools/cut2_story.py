
# ---- cut 2 story edits (session time, after the playback re-timing, before the dead-air pass) ----
GUIDE_MUSIC_TEXT = ("Now give the scene its own music. Describe the mood, generate a few possibilities, "
                    "and keep the one that feels right.")
story = []


def frame_starts():
    out, t = [], 0.0
    for f in frame_list:
        out.append(t)
        t += f[1]
    return out


def index_at(t):
    starts = frame_starts()
    return min(range(len(starts)), key=lambda i: abs(starts[i] - t))


def shift_after(t, delta):
    global end_at
    for other in events:
        if other["at"] > t + 0.005:
            other["at"] = round(other["at"] + delta, 3)
    log["chapters"] = [(round(at + delta, 3) if at > t + 0.005 else at, name) for at, name in log["chapters"]]
    end_at += delta


chap = dict((name, at) for at, name in log["chapters"])
new_take = next(e for e in events if e["role"] == "Music (new take)")
kept = next(e for e in events if e["role"] == "Music (kept)")

# 1. The Guide explains the music step: from the Music page (the frame after the lane-select hold)
#    until just before the new take plays. The condensed composing frame is held longer if needed.
i_lane = index_at(chap["Give it music"])
music_page_at = frame_starts()[i_lane + 1]
narr_seconds = sf.info(GUIDE_MUSIC).duration
narr_at = music_page_at + 0.2
pad = narr_at + narr_seconds + 0.35 - new_take["at"]
if pad > 0:
    i_compose = index_at(new_take["at"]) - 1
    frame_list[i_compose][1] += pad
    shift_after(frame_starts()[i_compose] + 0.05, pad)
    story.append({"edit": "composing frame held longer for the Guide line", "seconds": round(pad, 2)})
events.append(dict(at=round(narr_at, 3), path=GUIDE_MUSIC, source=GUIDE_MUSIC, role="Guide", length=narr_seconds,
                   gain_db=0.0, fade=0.02, text=GUIDE_MUSIC_TEXT, file_seconds=round(narr_seconds, 3)))
story.append({"edit": "Guide line for the music step", "at": round(narr_at, 2), "seconds": round(narr_seconds, 2)})

# 2. The new take's audition: 1.6 s of its frames, then the selection of take D in Kept music held
#    1.4 s. The new take fades out under the selection and crossfades into D.
KEEP = 1.6
i0 = index_at(new_take["at"])
step = frame_list[i0][1]
t, i = 0.0, i0
while i < len(frame_list) and abs(frame_list[i][1] - step) < 1e-6 and t + frame_list[i][1] <= KEEP + 1e-6:
    t += frame_list[i][1]
    i += 1
j = i
while j < len(frame_list) and abs(frame_list[j][1] - step) < 1e-6:
    j += 1
removed = sum(f[1] for f in frame_list[i:j])
del frame_list[i:j]
shift_after(new_take["at"] + t - 0.01, -removed)
story.append({"edit": "new take audition shortened", "kept_seconds": round(t, 2), "removed_seconds": round(removed, 2)})
i_select = i
extra = max(0.0, 1.4 - frame_list[i_select][1])
frame_list[i_select][1] += extra
shift_after(frame_starts()[i_select] + 0.05, extra)
XF = 0.6
new_take["length"] = round(kept["at"] - new_take["at"] + 2 * XF, 3)   # fades across D's first phrase
new_take["crossfade_out"] = round(3 * XF, 3)     # full level through the selection, then crosses into D
kept["fade"] = XF
story.append({"edit": "take D selection held", "seconds": round(frame_list[i_select][1], 2), "crossfade_seconds": XF})

# 3. The ending: the export result for 2.0 s; the tagline 0.25 s after the end card; take D continues
#    softly from where the scene ended and fades out under the ending; the film ends 1.4 s after the
#    last word.
i_export = index_at(dict((name, at) for at, name in log["chapters"])["Export the mix"])   # after the edits above
cut_export = frame_list[i_export][1] - 2.0
if cut_export > 0:
    frame_list[i_export][1] = 2.0
    shift_after(frame_starts()[i_export] + 0.05, -cut_export)
scene = next(e for e in events if e["role"] == "Studio mix")
brand = next(e for e in events if e["role"] == "Brand narrator")
brand["at"] = round(end_at + 0.25, 3)
end_len = round(0.25 + brand["file_seconds"] + 1.4, 3)
bed_at = round(scene["at"] + scene["length"], 3)
events.append(dict(at=bed_at, path=kept["source"], source=kept["source"], role="Music (ending)",
                   length=round(end_at + end_len - bed_at, 3), offset=round(scene["length"], 3), gain_db=0.0,
                   fade=0.5, text="[Music continues under the ending]", file_seconds=30.0))
story.append({"edit": "ending", "export_result_seconds": 2.0, "tagline_after_card_seconds": 0.25,
              "tail_after_tagline_seconds": 1.4,
              "music_bed": f"take D from {scene['length']} s into the file, from the end of the Studio playback, 0.5 s fade in, faded out under the ending"})
events.sort(key=lambda e: e["at"])
