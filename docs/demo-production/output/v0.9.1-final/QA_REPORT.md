# QA report: A World in Sound, v0.9.1 final cut (2026-11-03)

The final cut is **review cut 2 with the temporary logo card replaced by the MythologIQ Labs opener**. Nothing else changed. After the opener,
the frame list is identical to cut 2's (the only other difference is the end card's file path, same image). The soundtrack and captions are
byte-identical to cut 2. Application, release and installer identification are in `../v0.9.1-review-1/QA_REPORT.md` (Sonic Rift 0.9.1, tag
`v0.9.1` → `9e5ded1`, signed installer `f5f192c1…8456`). Cut 2's QA (`../v0.9.1-review-2/QA_REPORT.md`) applies unchanged to everything after 0:02.6.

## The opener (0:00–0:02.6)
| Item | Value |
|---|---|
| Mark | The website revamp's own file `public/assets/studio-20261030-v76/mythologiq-silver-concept.webp` (Knapp-Kevin/MythologIQ @ `6b655b69`), SHA-256 `c0141a60b03cc6b96750cb17ac3b8ca77b5d650539787cdf8fb83ef7ce9694b2`, approved by the owner for the opener. Cropped to its visible area and scaled **down** (481 → 360 px on the 1350-px canvas); not redrawn |
| Lockup | As in the revamp header (`src/studio/studio.css`): "MythologIQ" DM Sans 700 #ffffff + " Labs" DM Sans 500 #d4d5da, letter-spacing −0.025em; "INDEPENDENT SOFTWARE STUDIO" DM Sans 700 #aaaeb9, letter-spacing 0.16em. Sizes, gap and margin keep the header's proportions (mark : wordmark : subtitle = 46 : 21 : 8). Optical sizes match the header (21 and 9). The mark has the header's drop shadow and soft silver glow, scaled. Canvas #090a10 (the studio palette) |
| Font | DM Sans variable `DMSans[opsz,wght].ttf` from github.com/google/fonts (ofl/dmsans), SHA-256 `8cd08d97e89c24d0aa92edd2f0f4c8ee6195eee9b7c9f154865a58b02f0c1c0d`, SIL Open Font License 1.1 (`licenses/DMSans-OFL.txt`); downloaded with the owner's approval |
| Motion | Mark fades in 0.2–0.8 s; wordmark 0.5–1.0 s (0.3 s after the mark begins); subtitle 0.6–1.1 s; hold; dissolve into the film's first frame 2.2–2.6 s. Smoothstep easing, no scale, particles or other effects. 2.6 s total, so every later timing, caption and sound is unchanged. Silent |
| Temporary markers | None: no "TEMPORARY" text in the picture, overlays or captions (scanned) |

## Results
| Check | Result |
|---|---|
| Both MP4s decode end to end | **Pass**: 88.33 s; H.264 1920×1080 30 fps; main cut AAC 48 kHz stereo |
| Loudness | **Pass**: −16.2 LUFS integrated, true peak −0.7 dBFS (the soundtrack is identical to cut 2; the 0.1 dB difference is from AAC encoding); 0 clipped samples |
| Captions, transcript | Captions identical to cut 2 (19 of 21 spoken cues heard word for word; the other 2 are the "toward/towards" recognition variant). Transcript updated for the opener row only |
| Sync | Unchanged from cut 2 (the build's sync check passed) |
| Opener frames | Checked at 0.1, 0.5, 1.0, 1.8, 2.4 and 3.0 s: dark canvas, mark in, lockup complete, dissolve, film |
| Previous cuts and approved media | Cuts 1 and 2 and all approved `docs/marketing` media untouched |

## Editorial notes that carry over from cut 2
- The handover from the new music take into take D is an editorial crossfade (in the app the new take was stopped before D was selected).
- The music under the export and end card is take D continuing after the app's playback has ended (editorial).
- The character lines are live v0.9.1 takes. The Guide narration, tagline and waves are the approved files, plus one new Guide line made in Sonic Rift 0.9.1.

## Download
Private draft GitHub release (not published, no tag; repository collaborators only):
- `sonic-rift-world-in-sound-v091-final.mp4`: SHA-256 `76a3bd69ae2bcea3e96d48d5a1535383660e0db8f7c2d986834b36a6da57dd33`
- `sonic-rift-world-in-sound-v091-final-silent-captioned.mp4`: SHA-256 `6b9077f097c33b62f38cf1be574b7a79ae5025603a297c05db7ccc7715a4e1c4`
