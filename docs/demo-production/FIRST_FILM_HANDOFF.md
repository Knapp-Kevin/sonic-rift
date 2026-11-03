> **2026-11-03 production correction:** This handoff contains early concepts that required newly generated illustrations. The owner rejected those visuals. **Authoritative replacement:** [CLAUDE_START_HERE.md](./CLAUDE_START_HERE.md) + [SCRIPT_LOCK.md](./SCRIPT_LOCK.md). Only use approved existing media and exact silver logo sourced from website revamp. No image generation is assigned to Claude. The lighthouse illustration requirement below is **cancelled** for first production; use approved empty-Studio imagery instead. The final recording is pending technical rehearsal and owner review.

# First production pilot — Sonic Rift: A World in Sound
**State:** creative preproduction / final recording **HOLD** until approved brand graphics, human opener, exact-build rehearsal, model licenses and soundtrack are qualified.
**Production owner:** local Claude session operating the real Windows alpha and Sonic Rift, with owner approval.
**Story:** A lighthouse keeper leaves a light burning for a traveler crossing the water. Sonic Rift gives them different voices, an ocean, an original musical bed, and a mix that becomes a scene.

## Shared MythologIQ Labs ident (3 seconds, reusable)
**Owner-selected visual reference (2026-11-03): the MythologIQ Labs logo image supplied in the project conversation. The opener must look like THAT reference.** Do not use the older generic generated storyboard or an unrelated legacy website logo. In the active website revamp branch `Knapp-Kevin/MythologIQ:feature/sites-sonic-rift-reconciled-20261102-no-ci` (inspected SHA `6b655b69c51d6d7e4dde4851e6433be8609305b5`), `src/studio/StudioHeader.tsx` loads `public/assets/studio-20261030-v76/mythologiq-silver-concept.webp` as its header brand mark and displays the `MythologIQ Labs` wordmark separately. Compare that current revamp asset and the supplied owner reference side by side, including mark proportions, silhouette, tonal treatment, typography, wordmark spacing and composition. **If they differ, the owner's supplied image controls the visual goal.** Do not claim the supplied image has been committed to GitHub until its actual bytes are copied into a versioned asset pack and SHA-256 checked. Keep the approved mark undistorted; animation should reveal the exact image, not have generative AI redraw it. If there is no authoritative transparent master matching the owner image, request or extract a clean master from the provided artwork, verify it visually, and retain the source with provenance.

| Time | Motion | Audio |
|---|---|---|
| 0.00–0.65 | Deep navy celestial field, a few muted luminous specks moving slowly | Quiet breath of original synthesized ambience |
| 0.65–1.55 | Subtle points gather *toward* a central focal field, no three concentric rings | Low rising tone |
| 1.55–2.45 | Actual transparent/appropriately matted logo fades into full clarity with slight scale easing; light particles fade | Short clean brand chord |
| 2.45–3.00 | Static logo hold and dissolve to story still | Tail resolves, do not overlap first narrator word |

**Technical:** 1920×1080, 30 fps, sRGB Rec.709 H.264 MP4 with AAC audio, optional alpha master when needed. Keep an uncompressed/transparent logo master and an editable composition source. No hard-coded product names so the same ident can serve all projects. Do not create a second brand identity. Avoid strobe, heavy motion blur and intrusive loudness. Provide reduced-motion static fallback.

## Sonic Rift opener illustration
Use one **clean 1920×1080 still WITHOUT words or logos**: solitary lighthouse on a rocky shoreline at blue-hour sunset; distant small beam over calm dark water; warm window against deep navy sky; emotionally understated, photographic/cinematic not fantasy concept art. Keep a large safe zone on the right for overlay title and captions; no visible people. The story begins with a humanly comprehensible situation, not an app menu. An opening image must be explicitly **illustrative**, never implied to show the app itself.

**Opening title overlay added in edit, not burned into generated art:** `A World in Sound`.
**Opening narrator:** “A world can begin with just a few words.”
**Sound:** near-silent surf fades in, no music yet.
**Transition:** slow 2% push-in, then a modest 8-frame crossfade to the *real* empty Studio project.

## The existing story is the authority
Read `docs/marketing/video/NARRATIVE_STORYBOARD_PROPOSAL.md`, `docs/marketing/audio/README.md`, and `docs/marketing/video/transcript.md` before changing the film. Respect the owner's approved guide/keeper/traveler voice identities and original story. Keep the existing approved cut as an immutable reference.

### Revision goals
1. Cut unintentional gaps between lines and inert application footage; keep intentional listening space at the ocean and completed mix.
2. Rehearse whether the **currently installed Sonic Rift Windows alpha** can generate *and place* new music into this one saved project. If no end-to-end path exists, show a truthful export/import workflow or omit the scene; do not invent timeline actions.
3. Use Sonic Rift to generate the original *instrumental* bed, with verified commercially usable model and output rights. The bed must sit well below dialog and stop during full product samples where clarity matters.
4. Make the finished lighthouse exchange with voice + ocean (+ musical bed if real) the emotional climax; the narrator should STOP for the authentic passage.
5. Retain captioned sound-on cut, deliberate silent-captioned alternative, full transcript, stems and SHA-256 media manifest. No autoplay sound.

## Required pre-supplied assets
- [ ] Approved MythologIQ Labs logo master, checksum + license/permission
- [ ] Approved brand ident animation MP4 and associated source composition
- [ ] Approved clean lighthouse opener still, checksum and generation provenance
- [ ] Existing approved Sonic Rift lockup from `docs/marketing/logo/`
- [ ] End-card template (product name, `Windows alpha`, `mythologiq.studio`)
- [ ] Human-approved full narration + scene script; the existing storyboard is a starting point, not an automatic approval for revised footage

## Claude actions once the assets above exist
1. Pull this exact branch and the approved creative pack; lock local source SHA and installed app version.
2. Verify existing clips, voice model choices, ocean-wave stems, sound licenses and current composition.
3. **Rehearse without final recording:** test music generation, timeline insertion, mix playback, export, and the existing known dead-air points. Report missing features and give precise proposed script revisions; do not continue through an unverified scripted claim.
4. Generate and audition short soundtrack candidates in Sonic Rift. Owner picks the final cue.
5. Upon explicit approval of revised script, music and graphics, perform real capture against the verified build and edit it to exact scene IDs.
6. Produce downloadable H.264 MP4, silent-captioned alternate, VTT, transcript, music/narration/SFX WAV stems, poster, manifest and QA receipt. No publishing/merging until owner signs off.

## Evidence standard
The creative still is illustration; the app footage is genuine UI. Claims about signatures, music quality, model rights, voice cloning permissions, and released functionality require evidence from the exact app and license. Failed captures become engineering issues, not scenes to fabricate.
