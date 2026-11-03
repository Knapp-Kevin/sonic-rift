# Dead air in the approved film (measured 2026-11-03)

Source: `docs/marketing/video/sonic-rift-beacon.mp4` (SHA-256 `4100df5b…6a09`, 102.8 s), unchanged.
Method: `ffmpeg silencedetect=noise=-45dB:d=1.0` on the soundtrack; `freezedetect` on the silent cut
(`n=0.003`, then `n=0.0003` for S06–S08 so a moving playhead counts as motion); cue times from
`sonic-rift-beacon.en.vtt`.

Total true silence: **~49.6 s of 102.8 s**. Intended listening (waves 38.5–48.7 s, scene 79.9–91.1 s)
is not silent and is not counted.

| # | Silence (s) | Length | Between | Picture during the gap | Proposed trim |
|---|---|---|---|---|---|
| 1 | 0.00–2.15 | 2.2 s | film start → Guide S01 | Static empty Studio (frozen 0–6.2 s) | Replace with S00 logo hold (2–3 s), then ≤0.4 s before the line |
| 2 | **4.54–13.72** | **9.2 s** | Guide S01 → Keeper S02 | Speech page, static 6.2–14.5 s (8.3 s frozen) | Cut to ~1.5 s: show prompt + Generate, jump-cut the wait, audition starts on the line |
| 3 | 16.74–22.20 | 5.5 s | Keeper → Guide S03 | Add to Studio / clip appears (frozen 14.5–18.4, 18.4–22.0) | ~1.5 s: keep the clip-appears beat only |
| 4 | 24.43–28.15 | 3.7 s | Guide S03 → Traveler | Traveler generation | ~1.0 s |
| 5 | 30.18–35.83 | 5.7 s | Traveler → Guide S04 | Studio with two clips, then Sounds (frozen 32.0–35.6) | ~1.5 s |
| — | 35.6–43.9 | — | (waves playing) | Sounds page frozen 8.3 s while waves play | Keep ≥3 s waves-only (script), trim to ~4 s; picture needs motion (take list / playback) |
| 6 | **51.49–60.52** | **9.0 s** | Guide S05 → Keeper clone | Voices clone + Speech (frozen 53.6–55.6, 55.6–64.0) | ~2.0 s: Clone → Save voice → Generate, compressed |
| 7 | 62.42–67.66 | 5.2 s | Keeper clone → Guide S06 | Return to Studio, arrange | ~1.5 s (or cover with music bed if approved) |
| 8 | 71.38–74.44 | 3.1 s | Guide S06 line 1 → line 2 | Arranging/fades | ~1.0 s |
| 9 | 93.60–97.38 | 3.8 s | end of scene tail → Brand tagline | Static Studio after playback (frozen 93.5–96.8 at n=0.0003) and end card | Export (S08) belongs here: ~2.5 s with the real export result, then end card |
| 10 | 100.65–102.80 | 2.2 s | tagline → end | End card | ~1.0 s |

Not dead air: S07 playback 79.9–91.1 s (the playhead moves; keep it uninterrupted) and the waves at 38.5–48.7 s.

Trimming gaps 2–8 to the proposed lengths removes about 30 s. That brings the
current story to about 73–78 s, before adding the S00 logo hold and the S08 export beat (+~5 s).
The SCRIPT_LOCK target of 100–125 s therefore needs either the music scene (if it passes the rehearsal) or
longer listening moments. Silence should not be used as padding.
