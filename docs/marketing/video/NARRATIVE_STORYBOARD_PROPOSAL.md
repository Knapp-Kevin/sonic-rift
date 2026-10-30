# Sonic Rift | “A World in Sound” cinematic product walkthrough

**Status:** executed 2026-10-30 as [`sonic-rift-beacon.mp4`](sonic-rift-beacon.mp4) (see [transcript](transcript.md) and [MANIFEST](../MANIFEST.md)); the result was **approved by the owner on 2026-10-30** (not yet released). Voices chosen by the owner during production: Qwen3-TTS designs for the Guide, Keeper and Traveler, and a separate resonant baritone brand narrator for the tagline.
**Prepared:** 2026-10-30. Related work: #118 (website media), closed #119 (Studio UI superseded by consolidated draft #120), draft #120 (Studio-first UI + sonic-wave backgrounds), #61 (exact-head Windows acceptance).

## Objective

Replace the existing ~67-second button-by-button capture with a cohesive **approximately 95–105-second, narrator-led micro-story**. The audience should hear a small scene come alive, understand why Sonic Rift exists, and see **real UI evidence** of generating two genuinely distinct voices, creating ocean ambience, optionally cloning a consenting synthetic voice, arranging a scene, auditioning the mix, and exporting.

**Non-negotiable order:** implement and visually qualify the new UI first (Studio-first navigation, page-specific acoustic backgrounds and distinct voice modes); only then recapture screenshots/video in the real Windows app. **The film's visual spine is the growing Studio timeline, NOT a tour of generators: each feature's result must arrive visibly in Studio before the next feature.** This document is **not a Claude production prompt** and authorizes neither recording nor publication.

## Creative concept

**Title:** *A World in Sound*
**Fictional project:** *Evening Tide: The Beacon* (a replacement/extension of the existing synthetic “Evening Tide” fixture).
**One-line story:** A lighthouse keeper leaves a light on for a traveler crossing the water. In a few spoken lines, environmental sound, two different performances, and a final mix, an unseen shoreline becomes a place the audience can imagine.

Choose **genuine emotional simplicity over faux-cinematic complexity**. No film footage, unrealistic animation or faked UI. The actual app is the visual proof. The sound is the payoff.

## Cast and voice evidence

| Identity | Narrative role | Requirements |
| --- | --- | --- |
| **Guide** | Short, polished product narration between actual app sound samples | Distinct voice ID/timbre from both characters. Prefer Sonic Rift-generated narration, no external stock voice. Moderate tempo, intelligent and understated. |
| **Keeper** | Character A, calm and grounded, mid/lower register | Generate in Speech using a clearly identified built-in or owned synthetic voice preset. Original audio is heard in isolation and later in the scene mix. |
| **Traveler** | Character B, noticeably different higher/brighter or differently textured voice | Generate a **separate Speech take with a different actual voice selection/voice ID**. Do not count a clone of the Keeper as proof of a second character. |
| **Keeper clone** | Continuity demonstration: the Keeper can speak a new scripted line | Only clone from the fictional/synthetic Keeper’s own demonstrably eligible audio. The cloned result intentionally resembles the Keeper; it is **not a fourth independent speaker**. |

Keep a small evidence table of the actual engines/preset names, source paths, licenses, durations and output SHA-256 in the revised manifest. Model names in the initial demo (Kokoro Heart and VoxCPM2) are examples, **not preapproval of their audio quality**. Choose a second genuinely distinct voice by listening and checking actual model availability, rather than inventing a label.

## Proposed storyboard (~100–110 seconds; flexible to actual performances)

**Editorial invariant: the narrator speaks while the viewer watches the work taking shape.** Studio is the recurring home base; show the empty project, then visually return to that same project after *every* creation step. A generator is a brief source for an ingredient, never the visual endpoint of a segment. Transition cuts are allowed to shorten genuine generation wait time, but **never** fabricate a clip appearing, create fake waveforms or imply an import the real app cannot perform. If a capability is missing, expose that honestly and adapt the creative plan.

| Time | Narrative beat | Real on-screen action (show genuine state transitions) | Audio and visual payoff |
| --- | --- | --- | --- |
| **00:00–00:09** | **An empty world.** | Open the redesigned Studio on a clearly named, saved **empty** fictional project, atmospheric wave background visibly behind UI. Empty track space is intentional, not an unfinished screenshot. | Guide: “A world can begin with just a few words.” Hold on the real Studio before moving. |
| **00:09–00:25** | **Give it a keeper.** | Cut to Speech: a deliberately chosen Keeper voice, script, Generate, audition. Click **Add to Studio**, then **return immediately to Studio** and let the audience see the first real Narration clip appear on the timeline. | Keeper: “The beacon is still burning. Follow it toward shore.” The guide stays quiet during the actual voice sample. |
| **00:25–00:39** | **Someone answers.** | Cut briefly to Speech and switch to a **visibly different voice preset/ID**. Generate the Traveler take and use **Add to Studio**. Return to Studio; visibly reveal the **second distinct clip** joining the evolving composition. | Guide: “Then someone answers from across the water.” Traveler: “I see it now. Keep the light on.” |
| **00:39–00:54** | **Give the world a shoreline.** | Sounds: choose **Ocean waves**, generate and audition, keep the real take. Click **Add to Studio** and return; show the long ambience waveform under the already-visible two dialogue clips. If mix controls support actual adjustment, balance the bed live. | Guide: “The place comes alive when the sound has somewhere to live.” Allow 3–4 seconds of authentic unobstructed waves. |
| **00:54–01:09** | **Keep a character's voice.** | Voices > New voice > Clone; show real synthetic Keeper source and cloned third line. Audition. If the supported workflow can add it to Studio, **return and show the new clip**. If not, show a truthful library result and do **not** imply the clone participates in the later mix. | Guide: “A character can return without losing their voice.” Keeper clone: “I’ll keep it burning until you’re home.” |
| **01:09–01:35** | **Assemble, save, hear.** | Stay in Studio as clips are **actually positioned, trimmed or balanced where supported**, with visible track/timeline changes in sync with ongoing brief guide narration; save and eliminate all unsaved-state warnings. Show real playhead moving through the genuine mix. Avoid a hard cut to a static “completed” screenshot. | Guide: “A voice. An answer. The sound of the sea. Together, they become a scene.” **Then the guide stops** for an uninterrupted genuine Keeper + Traveler + ocean mixed sequence; add clone only if verifiably included. |
| **01:35–01:45** | **Result and identity.** | Export a real mix from that saved project; show export confirmation briefly, return to the fully built Studio project, end on Sonic Rift branding and tagline. | Guide: “Make worlds you can hear. Sonic Rift.” No false export or staged filesystem path. |

**Runtime is a hypothesis, not a forced cut.** Extend or contract the edit so there is sufficient dwell time to understand each new clip, no speech overlaps, and the resulting scene feels like a miniature creative production. Condense long model waits with disclosed editing, but never cut across a spoken word.

### Capture/edit rules for the Studio-first visual journey

1. Use **one real project instance** across all scenes. Capture the same genuine saved project after every add, not disconnected fixtures or synthetic composited UI layers.
2. At each generator step: show **source choice → render/audition → Add to Studio → newly added real clip**. The return is the story's recurring visual motif.
3. The **Guide** is a voice-over with its own generated voice and identity, not an onscreen speech track presented as one of the characters. Character voices must be **two genuinely different synth/preset identities**, and the Keeper clone is deliberately the Keeper again.
4. Voice-over, generated dialogue and sound preview must be **edited without masking one another**. Give the Studio full-screen priority during the climax. The wavefield is an ambient UI identity, not animated audio visualization.
5. For the website, ship captioned, sound-on product-film version plus a **deliberately legible silent cut** with descriptive text overlays/captions. Those overlays belong in the video edit, never fabricated into screenshots of the app.
6. Film only after the **new page-specific wave backgrounds, revised Studio navigation and take-history UI have been visually qualified** in Windows and source version pinned. The older historical #119 footage and logos are reference material, not final publication assets.

## Editorial and audio-mix constraints

1. **Distinct performances are observable.** The Guide, Keeper, and Traveler must sound unmistakably different and be backed by actual provenance. The Keeper clone is a demonstration of preservation, not the only other voice.
2. **The product speaks for itself.** The Guide bridges story beats and never competes with generated speech. Show two clearly different selected voices on the real Speech UI.
3. **Narrative first, features second.** Each feature advances the same lighthouse story. Don't transition into a random test passage about measuring cups or a new unrelated demo.
4. **Sound contrast matters.** Audition dry voices before the environmental bed, then let listeners hear the fuller mastered arrangement. Manage background level and intelligibility by ear, not only a LUFS metric; avoid clipping, bad overlaps, sudden level jumps and hard cuts.
5. **No third-party impersonation.** Use synthetic demo fixtures, or explicit consent. No real people or private recordings.
6. **No capability inflation.** Do not invent drag gestures, cloned-voice timeline insertion, sound effects, model names or recording routes unless verified in the exact build. Camera framing/zoom should not obscure genuine controls.
7. **Captions and silent playback:** caption all spoken lines with speaker distinctions; include meaningful ambient sound cues. Provide a silent-captioned promotional cut that is actually understandable without sound, and a full transcript. No autoplay with sound on the website.

## UI-first capture gate

Before generating new marketing media, require a real Windows install/source-run on the **final integrated UI SHA** containing the approved Studio-first shell and the wave backgrounds from #120. The generated reference artwork is a visual target; the current procedural Qt variant needs owner-level visual inspection and must not be assumed pixel-identical.

Check navigation and distinct acoustic backgrounds on Studio, Speech, Sounds, Voices > Clone and Voices > Design, dark and light themes, 100/125/150% scaling, legibility, resize performance and contrast. The older random-grain/static effect must be gone. Verify the existing duplicate same-second take labels are fixed and both Studio hero states are saved and stable.

**Then** recapture all affected screenshots, a new poster, the narrative video/audio, a no-audio alternative, captions and the transcript from the verified exact-head runtime. Update checksums, provenance and pinned commit references. Preserve prior media as historical until the new media is accepted. Don't hand this to Claude for media production until the UI implementation is qualified.

## Proposed review checkpoints

- **Creative review (now):** owner accepts or revises the story/characters/voice treatment and target length.
- **UI review:** new backgrounds in the actual product are approved in both themes before filming.
- **Voice audition:** save short raw samples of Guide, Keeper, Traveler and synthetic Keeper clone for owner listening before full video editing.
- **Video rough cut:** owner judges story pacing, voice differentiation, UI veracity and mix quality.
- **Website release gate:** explicit owner sign-off on final videos, screenshots, transparent lockups/font, rights and provenance. No premature publication, merge or announcement.

This is a storyboard proposal. The previous 67-second media is still unapproved. Do not overwrite existing recorded assets or label this plan “production complete.”
