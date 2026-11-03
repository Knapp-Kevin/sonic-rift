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
| S06 / ~75–92 s | Return to Studio, the same saved project. Music page → prompt → takes → the **owner-approved take** → **Keep and add to Studio…** with the **Shoreline waves track still selected**; the music arrives on **its own track** (no manual Empty-track step). Then balance in the **Levels panel**: drag the music slider to about **−14 dB** and the waves to about −6 dB, leave **Duck under voices** at −10 dB, click **Check balance** and hold on the readout ("… dB under the voices"). Clip fades from Clip properties (2 s in / 4 s out). Save | **Guide:** “Place every line where it belongs, and let the sea sit underneath.” **Guide:** “A voice... an answer... the sound of the sea. Together, they become a scene.” | Owner-picked cue: **round 2 take D** (cello and strings, 70 BPM, A major), `rehearsal/listening/round2/music_candidate_D_seed3101.wav`. Don't regenerate it (takes aren't reproducible from the seed). Rehearsal readout: music 22.7 dB and waves 21.3 dB under the voices |
| S07 / ~92–110 s | Hit real **Play mix**; show playhead and actual clips as genuine master audio plays uninterrupted | **Keeper:** “The beacon is still burning. Follow it toward shore.” **Traveler:** “I see it now. Keep the light on.” **Keeper clone:** “I'll keep it burning until you're home.” | **NO GUIDE SPEECH** during result. Full real voice + waves mix; optional low bed if actual source was verified. Never represent stitched overlay as native Studio playback if not true. |
| S08 / ~110–118 s | Actual Studio **Export mix** to fresh directory; show genuine success or supported export output; return to saved composition | *(None)* | Sound resolves gently; no fake confirmation or staged export panel. |
| S09 / final ~4–6 s | Existing **approved Sonic Rift** logo end card; include Windows alpha status only if independently rechecked at filming | **Brand narrator:** “Sonic Rift. Make worlds you can hear.” | End cleanly after voice. |

## Recording baseline (proposed, owner approval required)
- **Build to record:** Sonic Rift **development build** `59d132263eb2cdeba241b05d35c851510225b4e1` (branch
  `feat/studio-balance-controls`, draft PR #145, stacked on the music-track fix in draft PR #144), run from source. That is the v0.9.0-alpha
  code plus two Studio changes: kept music gets its own track, and the Levels panel (gain sliders, Duck under voices, Check balance). **This is a post-v0.9.0-alpha development build, not the published release.**
  The published v0.9.0-alpha (`f093ebd`) puts kept music on the selected waves track. A film recorded on it would need the manual
  Empty-track step, which this script no longer shows.
- **Qualification:** full test suite **676/676** at `59d1322` on the Windows Qt platform (the fix branch head `1c67a10`: 669/669;
  `bc84a4a` alone fails `test_version` because of a CHANGELOG heading, corrected in `1c67a10`) (one status-bar test fails only under off-screen Qt, the same
  on the untouched release, because off-screen Qt has no fonts). Real-app rehearsal: with the waves selected, kept music got its
  own track, and Save, Play mix and Export mix worked (`rehearsal/CHECKPOINT.md`).
- **Provenance line for the film/manifest:** "Recorded on a Sonic Rift development build (`59d1322`, after 0.9.0-alpha)." If the fixes are
  merged and released before filming, record on that release and update this line. Never call the build "the released alpha".
- **Availability text (S09):** "Windows alpha" refers to the published v0.9.0-alpha pre-release. Recheck it at filming.

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
