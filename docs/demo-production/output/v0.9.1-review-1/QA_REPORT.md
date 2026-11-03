# QA report: A World in Sound, v0.9.1 review cut 1 (2026-11-03)

**Status: private review cut. Not for publication** (temporary opener; music cue and character takes await owner approval).

## Application and release identification
| Item | Value |
|---|---|
| Release | Sonic Rift **0.9.1**, GitHub pre-release <https://github.com/Knapp-Kevin/sonic-rift/releases/tag/v0.9.1> (published 2026-11-03 21:24 UTC) |
| Source | tag `v0.9.1` → commit `9e5ded1fba5d0f9f19b5c1ed32253a74ac087696` |
| Installer | `SonicRift-Setup-0.9.1.exe`, SHA-256 `f5f192c1da11b24e0b3d093efeecb0aaf2c15b30bc2ee395b2f4cecc2d968456`, downloaded anonymously from the release; Authenticode **Valid**, signer `CN="MythologIQ Labs, LLC"` (thumbprint `5CE2719479095575EA8D258879F81BE324402BBA`), timestamped by Microsoft Public RSA Time Stamping Authority |
| Installed copy | Windows "Sonic Rift 0.9.1", publisher MythologIQ Labs, LLC, per-user install in a disposable folder (`/DIR=`); signed uninstaller (Valid) |
| Executable identity | `launch-sonic-rift.cmd` SHA-256 `41d100a9…d13d`; `main.py` SHA-256 `c25f2c63…a850`; app `this_voice_thing.__version__` = `0.9.1`; the installed `.venv` (Python 3.11.9, PySide6 6.9.0, PyTorch 2.8.0+cu128) built by the installer's first launch |
| Engines | Qwen3-TTS (Apache-2.0), VoxCPM2 (Apache-2.0), ACE-Step 1.5 2B turbo (MIT; weights `19671f40…`, source `ca1e85fe…`), procedural ocean (no model). Their environments and weights were linked from the owner's existing engine installs; the app code is the installed release |
| Machine | Windows 11 Pro 10.0.26300, NVIDIA RTX 5070 Ti 16 GB |
| Profile | Disposable demo profile with fictional data only (no owner settings, voices, projects or libraries). Seeded with the three owner-picked voice designs and kept music take D |

## Method
Same as the approved film: a script drives the real window off-screen (`QWidget.grab`, 2400×1350, 12 fps). Dialogs are answered by the script (listed in `timeline.json`/capture log). Waits for renders and model loads are condensed to a single frame. The real waits were: Keeper take 35.7 s (Qwen3 load), Traveler 5.0 s, ocean 3.1 s, VoxCPM2 load and clone 73.0 s, clone line 3.1 s, ACE-Step start and composition 69.2 s. App players are muted during capture, and the soundtrack is assembled from the files the app produced, at the times they played. Edit: dead air trimmed only from held frames and typing in silent stretches (21.8 s removed). Played sections re-timed to real time, so the picture stays in step with the audio. A sync check fails the build if any sound drifts more than 60 ms from its picture.

## Results
| Check | Result |
|---|---|
| Both MP4s decode end to end (`ffmpeg -f null`) | **Pass**: no errors; 84.70 s; H.264 1920×1080 30 fps; main cut AAC 48 kHz stereo |
| Loudness | **Pass**: −16.2 LUFS integrated, LRA 11.8 LU, true peak −0.9 dBFS; 0 clipped samples in the soundtrack (peak 0.891) |
| Abrupt truncation | **Pass**: every sound has a raised-cosine fade; ambience and the scene run on and fade (up to 3 s); the tagline ends 1.75 s before the end |
| No voice overlaps another | **Pass** (enforced by the build) |
| Picture/sound sync | **Pass**: sync check passed for all 14 sounds; the scene's playhead sits on each clip as its line plays (verified at the Keeper and clone lines; about 0.25 s player start-up latency) |
| Captions heard in the soundtrack (Sonic Rift's own transcriber, Whisper large-v3-turbo) | **17 of 19** spoken cues heard word-for-word in their windows; the other 2 are the same Keeper line, heard as "towards" for "toward" (the take alone transcribes as "toward") |
| Generated takes say their script | **Pass**: Keeper, Traveler and Keeper (clone), all word-for-word |
| Music has no words | Transcriber output on take D: "Thank you."; on the new take: "Thank you for listening." These are Whisper's known phantom phrases on instrumental audio, not lyrics. **Owner to confirm by ear** |
| Silent stretches (−45 dB, > 1.5 s) | Opener plus first line 3.3 s (the opener is silent by design); typing passages 2.0–3.8 s (visible action); export result 4.2 s (protected so "Export complete" can be read; includes the scene's tail) |
| Still picture > 3 s | Only under narration or sound: the empty project under the first Guide line (3.8 s), the Sounds page while the waves play (4.0 s), the balanced Studio under "A voice… an answer…" (6.0 s); end card |
| Approved originals untouched | **Pass**: all 35 files in `docs/marketing/MANIFEST.md` still match their SHA-256; `git status` clean |
| Guide and tagline audio | **Pass**: byte-identical to the approved `docs/marketing/audio` WAVs 01, 03, 05, 07, 09, 10, 12 |
| Ocean | **Pass**: the waves rendered on camera (procedural, seed 53) are byte-identical to the approved `06-shoreline-waves.wav` |
| Music in the scene | **Pass**: take D (`e6ce1041…9b88`), unchanged |

## Product claims shown, and the evidence
| Claim on screen | Evidence |
|---|---|
| Characters speak in their own voices (Speech) | Real Qwen3 cloning takes generated on camera (`source-audio/01-keeper.wav`, `03-traveler.wav`) |
| A character's voice can return (Voices › Clone) | Real VoxCPM2 clone saved as "Keeper (cloned)"; its take is `07-keeper-clone.wav` |
| Generated ocean waves (Sounds) | Real procedural render; byte-identical to the approved waves |
| Music is composed on the PC (Music) | Real ACE-Step take on camera (`08-music-new-take.wav`: seed 3201, 70 BPM, A major, made in 14 s) |
| Kept music gets its own Studio track even with the waves selected | Capture log: the waves lane was selected; the new track "Harbor light theme" was added; the waves lane still has one clip |
| Inline gain and Check balance | Lane sliders committed −6.0 / −15.0 dB as single undoable edits; Check balance badges 21.0 / 22.6 dB under the voices |
| Save, uninterrupted Play mix, Export | Heading "Studio · Saved · evening-tide-the-beacon.sonicrift.json"; the 14.48 s Play mix file is in `source-audio/`; Export output in `app-export/` (master −16.08 LUFS, −1.1 dBTP, 0 clipped, ducking on at −10 dB, 3 stems) |

## Known limitations of this cut
- **Temporary opener**: the website's silver mark (`mythologiq-silver-concept.webp`, SHA-256 `c0141a60…94b2`, shown at native 768×512, no resizing) has not been verified against the owner's reference image. It is labelled TEMPORARY on screen.
- The music beat shows a **new** take being composed, then uses the **kept** take D (picked earlier from round 2). Both are real and labelled in the captions; see OWNER_DECISIONS.md.
- The character lines are **new performances** generated live by v0.9.1 from the same owner-picked voice designs; the original film's takes are not reused (see OWNER_DECISIONS.md).
- Runtime 84.7 s, below the 100–120 s guide, after removing dead air without padding.
