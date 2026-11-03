# Sonic Rift | A World in Sound — SCRIPT LOCK v0.3 (proposed), OWNER REVIEW REQUIRED
**Fictional scene:** Evening Tide: The Beacon. **Intent:** Show a complete, genuine creative journey: distinct characters + ambience + optional original music → arranged, saved, auditioned and exported in Sonic Rift. **Target:** 100–125 seconds; trim dead air based on measured durations rather than forcing timestamps. **No new fictional storyline.**
**Important:** The exact narration lines and voice identities below reflect the existing owner-approved film. New music and revised intro alter the cut and therefore require owner review before publication.

## Production boundaries
- Use only current real application UI, existing approved repository visuals, and exact website-revamp silver MythologIQ logo. Generated lighthouse illustrations and image-generated storyboard sheets are REJECTED.
- Intro may use existing `sonic-rift-studio-empty-dark.png` to convey the starting point; do not wait for new artwork. Avoid logo animation if the correct logo/animation is not available, use static exact mark.
- All generated audio must come from the real Sonic Rift app; keep Qwen3 designed Guide, Keeper, Traveler roles and distinguish Keeper clone. Model output rights and exact recording build must be verified.
- Preserve the original final WAV, approved MP4 and voice sources. New take names and renders must not overwrite them.
- Claimed music capability is alpha and must pass a real end-to-end build-specific rehearsal. If it cannot be placed in the Studio project, use a separately mastered bed only if the product story makes that edit distinction honest; otherwise omit music.

## Production script: exact intended words
| ID / target duration | Real on-screen action and proof | Spoken narration / exact dialogue | Original audio and edit direction |
| --- | --- | --- | --- |
| S00 / 0–3 s | Use the **actual** owner-matched silver MythologIQ logo, static hold or approved lightweight animation; no imitation | *(None)* | A brief original brand tone if Sonic Rift can generate one and license permits; otherwise silence. |
| S01 / 3–10 s | Existing approved **empty Studio screenshot** then transition into a real saved empty project `Evening Tide: The Beacon` | **Guide:** “A world can begin with just a few words.” | No soundtrack bed. Avoid gratuitous silent lead-in. |
| S02 / ~10–27 s | Actual Speech UI shows selection of Keeper, prompt, generation, audition and **Add to Studio**; return to same real Studio project and show clip appear | **Keeper:** “The beacon is still burning. Follow it toward shore.” | One voice, clear and dry. Narrator quiet while character speaks. Shorten model-loading wait visibly. |
| S03 / ~27–42 s | Actual Speech UI shows *different* Traveler voice/preset, generation, audition, Add to Studio and same timeline with two distinct clips | **Guide:** “Then someone answers from across the water.” **Traveler:** “I see it now. Keep the light on.” | No overlap between Guide and Traveler. |
| S04 / ~42–59 s | Actual Sounds UI generates procedural Ocean waves; audition; add kept wave to the same project's own track | **Guide:** “Give their conversation a shoreline.” | Play genuine waves visibly/audibly for ~3 seconds. If using music, do not bury the waves. |
| S05 / ~59–75 s | Actual Voices > New voice > Clone using Keeper's **synthetic** sample, then Speech uses cloned Keeper to add last line | **Guide:** “A character can return without losing their voice.” **Keeper clone:** “I'll keep it burning until you're home.” | Clone is the same character returning, not a fourth independent speaker. |
| S06 / ~75–92 s | Return to Studio, the same saved project. Music page → prompt → takes → the **owner-approved take** → **Keep and add to Studio…** with the **Shoreline waves track still selected**; the music arrives on **its own track** (no manual Empty-track step). Then balance **on the timeline**: drag the slider in the music lane's header to about **−14 dB** (waves stay about −6 dB; Duck under voices stays at its −10 dB default), click **Check balance** beside Play mix and hold on the lane badges ("… dB under the voices") and the summary line. Clip fades from Clip properties (2 s in / 4 s out). Save | **Guide:** “Place every line where it belongs, and let the sea sit underneath.” **Guide:** “A voice... an answer... the sound of the sea. Together, they become a scene.” | Owner-picked cue: **round 2 take D** (cello and strings, 70 BPM, A major), `rehearsal/listening/round2/music_candidate_D_seed3101.wav`. Don't regenerate it (takes aren't reproducible from the seed). Rehearsal readout: music 22.7 dB and waves 21.3 dB under the voices |
| S07 / ~92–110 s | Hit real **Play mix**; show playhead and actual clips as genuine master audio plays uninterrupted | **Keeper:** “The beacon is still burning. Follow it toward shore.” **Traveler:** “I see it now. Keep the light on.” **Keeper clone:** “I'll keep it burning until you're home.” | **NO GUIDE SPEECH** during result. Full real voice + waves mix; optional low bed if actual source was verified. Never represent stitched overlay as native Studio playback if not true. |
| S08 / ~110–118 s | Actual Studio **Export mix** to fresh directory; show genuine success or supported export output; return to saved composition | *(None)* | Sound resolves gently; no fake confirmation or staged export panel. |
| S09 / final ~4–6 s | Existing **approved Sonic Rift** logo end card; include Windows alpha status only if independently rechecked at filming | **Brand narrator:** “Sonic Rift. Make worlds you can hear.” | End cleanly after voice. |

## Recording baseline (released build)
- **Build to record:** the published **Sonic Rift 0.9.1** GitHub pre-release, installed from the signed
  `SonicRift-Setup-0.9.1.exe` (SHA-256 `f5f192c1da11b24e0b3d093efeecb0aaf2c15b30bc2ee395b2f4cecc2d968456`, signer MythologIQ Labs, LLC),
  tag `v0.9.1` at commit `9e5ded1fba5d0f9f19b5c1ed32253a74ac087696`. It contains the music-track fix (#144), the Studio balancing controls
  (#145), the upgrade fix that keeps `models.json`, and the single Add to Studio button style (#146).
  Release: <https://github.com/Knapp-Kevin/sonic-rift/releases/tag/v0.9.1>.
- **Install for capture:** a fresh install in a disposable folder (`/DIR=`), with no personal profile. Verify the installer's SHA-256 and signature before installing.
- **Qualification:** 679/679 tests and 10/10 real-app acceptance checks at the release commit content; the signed installer passed a clean install, a first
  launch and a signed uninstall; an upgrade from the signed 0.9.0-alpha kept every user file (17/17).
- **Provenance line for the film/manifest:** "Recorded on Sonic Rift 0.9.1 (Windows pre-release, signed installer)."
  The earlier development SHAs (`bc84a4a`, `06ff4c0`) are rehearsal history only.
- **Availability text (S09):** the current download is the 0.9.1 Windows **pre-release**. Say "Windows pre-release" (or the owner's chosen wording); recheck at filming.

## Original approved audio map
| Role | Source |
| --- | --- |
| Guide S01 | `docs/marketing/audio/01-guide-a-world-can-begin.wav` |
| Keeper S02 | `docs/marketing/audio/02-keeper-the-beacon.wav` |
| Guide/Traveler S03 | `docs/marketing/audio/03-guide-someone-answers.wav`, `04-traveler-i-see-it-now.wav` |
| Guide and waves S04 | `docs/marketing/audio/05-guide-a-shoreline.wav`, `06-shoreline-waves.wav` |
| Guide and Keeper clone S05 | `docs/marketing/audio/07-guide-a-character-can-return.wav`, `08-keeper-clone-ill-keep-it-burning.wav` |
| Guides S06 | `docs/marketing/audio/09-guide-place-every-line.wav`, `10-guide-together.wav` |
| Scene S07 | `docs/marketing/audio/11-studio-preview-mix.wav` or `13-exported-master.wav`; exact selected clip must match captured playback |
| Closing S09 | `docs/marketing/audio/12-brand-narrator-tagline.wav` |

## Audio cut quality
- Diagnose **actual silence**: measured source timecodes and intent; trim unintended inactivity but preserve ~3s waves-only and one complete final scene.
- Narration mixed near consistent perceived level; use side-chain ducking or gain automation. Avoid abrupt cuts and clipping; publish measured integrated loudness and true peak.
- Add 1–2 seconds of opening or closing space only where rhythm demands it, not random empty timeline.
- Include voice-separated caption labels, meaningful audio-cue descriptions, full transcript and silent-captioned version.

## Capture and truth checklist
- [ ] Same real saved project from first clip to export.
- [ ] Guide, Keeper, Traveler and Keeper-clone identities grounded in actual saved preset/engine evidence.
- [ ] Every Add to Studio has a visible corresponding clip.
- [ ] Any instrumental score generated in Sonic Rift and rights/provenance confirmed; real playback and export tested.
- [ ] Recording is a real app instance with exact commit/version, Windows build and disposable synthetic profile.
- [ ] Owner logo visually matched; no generated substitute.
- [ ] Updated score, cut, title and script receive owner approval before public use.

If any recorded action fails, preserve an exact report and propose a script revision. Do NOT quietly replace verified application footage with generated UI.
