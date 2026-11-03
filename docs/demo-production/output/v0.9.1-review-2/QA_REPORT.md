# QA report: A World in Sound, v0.9.1 review cut 2 (2026-11-03)

**Status: private review cut. Not for publication** (temporary opener; take D and the new performances await owner approval).

Cut 2 is the same recorded v0.9.1 session as cut 1 (`../v0.9.1-review-1/QA_REPORT.md` has the full application, release and
installer identification: Sonic Rift 0.9.1, tag `v0.9.1` → `9e5ded1`, installer SHA-256 `f5f192c1…8456`, signed by MythologIQ Labs, LLC).
No footage was re-recorded. Only the edit changed, plus one new Guide line generated in Sonic Rift.

## The owner's three notes, and what changed
| Note | Change in cut 2 | Verified |
|---|---|---|
| 1. No narration during music generation | New Guide line at 0:38.8–0:45.9: *"Now give the scene its own music. Describe the mood, generate a few possibilities, and keep the one that feels right."* It plays over the prompt being written, Generate and the composing state. The composing frame (real app state, "Starting ACE-Step…") is held 3.4 s longer so the line fits before the first take plays | Transcriber hears both sentences word for word inside their caption windows. The line ends 0.35 s before the new take plays |
| 2. Disjointed music playback | The new take's audition is cut to 1.5 s. The selection of kept take D in Kept music is held 1.4 s. The new take fades out across D's first phrase (1.8 s overlap). Take D then plays on, uninterrupted, as it arrives on its own Studio track, and fades out (1.95 s) just before the next Guide line | Momentary loudness through the handover stays between −18 and −28 LUFS (cut 1 dropped to −36.5); no silence. Captions name the two takes separately: "[A new take…]", then "[Take D, kept earlier…]" |
| 3. Pause before the tagline | Export result on screen 2.0 s (readable: "Export complete … master, one stem per track and a manifest"). End card at 1:23.2; the tagline starts 0.25 s later; the film ends 1.4 s after the last word. Take D continues softly from where the scene's playback ended and fades out under the tagline | Scene end to tagline: 2.65 s (cut 1: 4.0 s plus a silent pause). The only gap is 0.78 s where the Studio's own playback fades out at the scene's end. Final 5.1 s: end card, tagline, music fade |

## New audio: provenance
- **Guide line**: generated in the installed **Sonic Rift 0.9.1** the way the approved Guide lines were made: the Guide voice saved from the
  owner-picked voice design (`voice-designs/guide.wav`) with Voices › New voice › Clone, then Speech with **Qwen3 voice cloning**
  (Apache-2.0). There were 4 takes (`source-audio/guide-music-takes/`, scores in `score.json`). Take 4 was picked: all words correct; voice similarity to the six
  approved Guide lines **0.956** (Chatterbox voice encoder), the best of the four. For reference, the approved Guide lines score 0.885–0.951
  against each other on the same measure. Its pace is 4.0 words/s, the closest of the four to the approved Guide's 3.8. The file is `source-audio/vo-music-guide-new.wav`.
- **Music under the ending**: take D (`e6ce1041…9b88`, unchanged), from 14.48 s into the file, which is where the scene's playback of D ended.
  It runs under the export result and end card at −29 LUFS, fading out under the tagline. **Editorial**: it is added in the edit after the Studio playback has stopped. It is not app playback.
- **New-take → take D handover**: **editorial crossfade**. In the app the new take was stopped before D was selected. In the edit its audio
  continues under the 1.4 s selection and crosses into D. The two takes stay separately labelled in captions and on screen.

## Results
| Check | Result |
|---|---|
| Both MP4s decode end to end | **Pass**: 88.33 s; H.264 1920×1080 30 fps; main cut AAC 48 kHz stereo |
| Loudness (same standard as cut 1) | **Pass**: −16.2 LUFS integrated, LRA 10.7 LU, true peak −0.8 dBFS; 0 clipped samples (peak 0.891) |
| Picture/sound sync | **Pass**: the build's sync check (every sound within 60 ms of its picture) passed; the scene and its playback re-timing are unchanged from cut 1 |
| No voice under another voice | **Pass** (enforced). Music sits only under the closing tagline and in the take crossfade |
| Captions | **19 of 21** spoken cues heard word for word (the app's transcriber), including both new Guide cues. The other 2 are the same Keeper line heard as "towards" for "toward", as in cut 1 |
| Generated character takes say their script | **Pass**: 3/3, unchanged from cut 1 |
| Beginning-to-end pass | The whole soundtrack, transcribed in one piece, plays every line in story order (Guide, Keeper, Guide, Traveler, Guide, Guide, clone, new Guide line, Guide, Guide, the scene's three lines, tagline). The picture was checked one frame per second over all 88 s. Transitions read: Music page → composing → new take → take D selected → D in Studio → arrange → scene → export → end card |
| Abrupt fades | None: every sound has a raised-cosine fade. The handover is an overlap, not a stop and restart. The ending music fades out over 2.6 s |
| Still picture > 3 s | Only under sound: opener + empty Studio under the first Guide line; Sounds while the waves play; the composing frame under the new Guide line (4.4 s); Kept music while take D plays (5.0 s); the balanced Studio under "A voice… an answer…" (5.3 s); end card |
| Cut 1 untouched | **Pass**: all 54 files in `v0.9.1-review-1/MANIFEST.md` re-verified (0 changed); cut-1 MP4 `7bc58afe…` |
| Approved originals untouched | **Pass**: 35/35 `docs/marketing` files match; `git status` clean |

## Review link
- The MP4s are attached to a **draft** GitHub release, "PRIVATE REVIEW: demo film cut 2 (not a product release)". Drafts are visible only to
  repository collaborators, it is not published, and no tag exists (the draft's tag name is `demo-review-v091-cut2`, which cannot trigger the release workflow).
- Verified: an authenticated API download returns the exact files (SHA-256 below); anonymous requests to the release page and the file get **HTTP 404**.
  The github.com links need a signed-in browser session with access. I could not click-test them myself because my browser is not signed in to GitHub.
- `sonic-rift-world-in-sound-v091-review-2.mp4`: SHA-256 `5e0139d840fe89c54cb41c0939311a5caae0774d9da07cad439256f3b5e91b83`
- `sonic-rift-world-in-sound-v091-review-2-silent-captioned.mp4`: SHA-256 `3b2fe20c700509658c4f1880f61ed1143214a60426b389d4fa7e11185e8e7971`
