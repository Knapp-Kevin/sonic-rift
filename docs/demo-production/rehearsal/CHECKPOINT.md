# Required starting checkpoint: technical rehearsal, 2026-11-03

**State: rehearsal complete. No final capture was made.** Per CLAUDE_START_HERE.md, the owner must approve the
script changes and the logo before final recording. Nothing was merged, published or pushed, and no CI ran.

Screenshots: `scene-*` are the dark-theme scene rehearsal. `route-*` are the earlier route test in the light theme (the fresh profile followed the light system theme).

## 1. Pinned application
| Item | Value |
|---|---|
| Build | `v0.9.0-alpha`, commit `f093ebdac6161abc28b534bab2add7bc991757b9` (the released tag), run from source in a detached worktree |
| `main` at rehearsal | `8aae2c4` (no app code changes since the tag; only docstrings, tests and docs differ) |
| Installed alpha | **No Sonic Rift installation on this PC** (no uninstall entry and no shortcut). The rehearsal used the tag's source. For the final film, either install the signed v0.9.0-alpha release or record from source and state that, as the approved film did. |
| Runtime | Windows 11 Pro 10.0.26300, Python 3.11.9, PySide6 6.9.0, PyTorch 2.8.0+cu128, RTX 5070 Ti 16 GB |
| Profile | Disposable: the worktree is the app's ROOT. Engine environments and weights are linked read-only from the owner's checkout. The owner's settings, voices, projects and library were not read or written. |
| Capture method | Same as the approved film: the real main window driven by a script, captured with `QWidget.grab` at 1600×900 logical ×1.5 = 2400×1350, dark theme (Qt color scheme set to Dark, which is what Windows dark mode does). Dialogs were answered by the script and logged (`logs/`). |

## 2. Local assets
- All 35 files in `docs/marketing/MANIFEST.md` match their SHA-256 (`sha256sum -c`: 35/35 OK) and are identical to `main`.
  The film, poster, empty-Studio screenshot, end card, voice sources and audio 01–13 are untouched.
- End card `logo/sonic-rift-end-card.png` `f0f39833…f7ed1` ✔. Poster `153437bd…31ae` ✔. Empty Studio `4ea71d27…15c4` ✔.

## 3. Silver MythologIQ logo: **BLOCKER (partial)**
- Fetched exactly from `Knapp-Kevin/MythologIQ@6b655b69c51d6d7e4dde4851e6433be8609305b5`
  `public/assets/studio-20261030-v76/mythologiq-silver-concept.webp`. `StudioHeader.tsx` at that SHA does load this file (line 77)
  and renders the "MythologIQ Labs" wordmark separately as HTML text.
- SHA-256 `c0141a60b03cc6b96750cb17ac3b8ca77b5d650539787cdf8fb83ef7ce9694b2`, 768×512 WebP with alpha (yuva420p), 28,744 bytes.
- Visually: a brushed-silver crescent, a four-point star and a feather. It matches the written description
  (see `screenshots/logo-candidate-mythologiq-silver-concept-on-navy.png`).
- **Not verified against the owner's supplied reference image.** That image was in the project conversation, not in
  either repository, and I don't have it. The start-here rule requires a side-by-side comparison, so brand work stops here.
- Also: 768×512 is low resolution for 1080p. Shown at native size (about 47% of frame height) it stays sharp. Larger than that
  would need upscaling, which is not allowed. A higher-resolution master is wanted, and the wordmark is not in the file.
- **Owner action:** confirm this file is the mark (or supply the master), and say whether the static S00 card is the mark
  alone or the mark plus the "MythologIQ Labs" wordmark set in the site's font.

## 4. Dead air in the approved film
See [DEAD_AIR_REPORT.md](DEAD_AIR_REPORT.md). About 49.6 s of the 102.8 s is true silence. The worst gaps are
4.5–13.7 s (9.2 s, Guide→Keeper) and 51.5–60.5 s (9.0 s, Guide→Keeper clone). There are also five gaps of 3–6 s, and an 8.3 s frozen
frame over the waves. Trimming to the proposed lengths removes about 30 s.

## 5. Music: generation, route into Studio, playback, export: **PASS (with one defect)**
Engine: ACE-Step 1.5 (2B turbo), MIT licence (code and weights), pinned weights `19671f40…` and source `ca1e85fe…`, as the app's catalog states.
The app shows an MIT licence and says commercial use is allowed. The authors' training-data claim is theirs, as the app itself notes.

| Run | What happened in the real app | Result |
|---|---|---|
| Route test (run 3) | Music: 2×30 s instrumental takes; **Keep and add to Studio…** → clip on a new sound track; Save; Play mix; Export mix | Model start 44 s, takes 59 s. Clip appears (30.0 s). Play mix renders in 0.5 s and plays. Export gives `master.wav` + stems + `manifest.json` listing the music asset. Master −16.0 LUFS, −1.1 dBTP |
| Scene rehearsal (`screenshots/scene-*`) | Studio: new project "Evening Tide: The Beacon"; Add › Narration file… ×3 with the **approved** 02 Keeper, 04 Traveler and 08 Keeper-clone WAVs; Sounds: procedural Ocean waves (2 takes, 3 s) → Keep → Add to Studio; Music: 3×30 s takes → Add › Empty track… "Music" → **Keep and add to Studio…**; track gain dialogs (waves −6 dB, music −14 dB); music fades 2 s in / 4 s out; Save; Play mix; Export mix | Model start 46 s, 3 takes 67 s. Export: master −16.2 LUFS, true peak −1.1 dB, 0 clipped samples, ducking on. Stems (post-duck): dialogue −18.7 LUFS, waves −31.7, music −31.8, so the **music sits about 13 dB under the lines** |

Findings:
1. **Defect: music lands on the selected sound track.** If a sound track (the waves) is selected, "Keep and add to
   Studio…" adds the music clip to that same track, overlapping the waves. The labels overlap on screen and the two can't be balanced
   separately (`scene_try1`, kept locally). Workaround in the real UI: Add › Empty track… (sound, "Music"), select it, then
   Keep and add to Studio. Engineering fix suggested: music should get its own track unless a *music-named or empty* track is
   selected. I have not filed an issue (owner's call).
2. **Not reproducible by seed:** the same seed gave different audio in two runs (hashes differ). The owner-picked take
   must be kept as a file. The final film must use the kept asset, not a regeneration.
3. The fades were set through `ProjectSession.update_clip`, the model behind the Clip properties dialog, not the dialog itself,
   because that dialog is a custom QDialog. The approved film's fades were also script-answered dialogs. In the final capture the dialog
   should be answered the same way the approved film did it.
4. Narration-file imports show as "Narration take" on clips (no text). In the final capture the lines come from Speech with
   their text, as in the approved film.
5. Heavy job: about 10 GB VRAM, and the app shows its heavy-job warning (about 4.4 min estimate; real wall time about 2 min).

**Listening package (owner picks the cue):** `listening/music_candidate_{A,B,C}_seed{2026,2027,2028}.wav`
(30 s, 48 kHz stereo, about −16 LUFS each) and `listening/scene-rehearsal-master.wav` (candidate A under the approved Keeper, Traveler and
Keeper-clone lines and procedural waves, exported by Studio). Prompt: *"Understated original instrumental underscore for a quiet seaside
night: soft felt piano, warm low strings, slow and calm, gentle, sparse, no percussion, no vocals"*, Instrumental on,
Plan first on. **Not verified: absence of sung vocals** (no transcriber in this build's environment), so this is an owner listening check.

## 6. Proposed script edits (owner approval needed)
| Scene | Change | Why |
|---|---|---|
| S00 | Static 2.0–2.5 s hold of the exact mark on the navy background, no animation, silence. Only after §3 is cleared | The logo isn't verified, and there are no animation tools for an approved mark |
| S01 | Start on the approved empty-Studio still for ≤1.5 s, then cut to the real saved empty project. Guide line starts ≤0.4 s after the cut | Remove the 2.2 s head silence |
| S02–S05 | Cap each generation wait at 1.0–2.0 s of visible progress (jump cut), and keep about 3–4 s waves-only in S04 with visible take playback | Removes about 30 s of the measured dead air |
| S06 | Add the music beat: Music page → prompt → takes → **Add › Empty track "Music" → Keep and add to Studio** → track gain −14 dB → fades. New Guide line *not* proposed: the existing "Place every line… let the sea sit underneath" stays | Music route verified. The "Music" track step is the honest workaround for finding 1 |
| S07 | Play mix with dialogue + waves + music. Music clip trimmed to the scene with a 4 s fade-out. **No Guide speech** | The rehearsal confirms the balance is about 13 dB under the dialogue |
| S08 | Real Export mix into a new folder; show the "Export complete" note (real) for about 2 s | Fills the 3.8 s pre-tagline gap with real action |
| S09 | Approved end card plus the existing tagline WAV 12. "Windows alpha" only if rechecked at filming (v0.9.0-alpha is a GitHub pre-release) | Unchanged |
| Length | About 100–110 s after trims plus the music beat | Within the 100–125 s target without padding |

## 7. Remaining blockers before final recording
1. Owner confirms the silver mark against their reference, or supplies the master (and decides on the wordmark).
2. Owner approves the script edits in §6 and picks the music cue (A/B/C or regenerate) after listening for vocals.
3. Decide installed build or source build for the "exact recording build" line.
4. Optional: fix the music-track defect first, so the film doesn't need the Empty-track step.

## 8. Final assembly capability (local)
`ffmpeg` 7.1 (Gyan essentials) is available. It can cut, concatenate, mix, side-chain duck, measure loudness (ebur128),
encode H.264/AAC, burn subtitles and verify by decode. No other editor is used. Once the owner approves, I can
deliver the MP4, silent-captioned cut, VTT, transcript, stems, EDL and manifest. No final MP4 was produced in this session.
