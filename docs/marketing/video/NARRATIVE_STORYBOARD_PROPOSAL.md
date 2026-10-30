# Sonic Rift | “A World in Sound” cinematic product walkthrough

**Status:** proposed editorial direction, **not owner-approved or released**.
**Prepared:** 2026-10-30. Related work: #118 (website media), draft #119 (Studio page), draft #120 (sonic-wave backgrounds), #61 (exact-head Windows acceptance).

## Objective

Replace the existing ~67-second button-by-button capture with a cohesive **approximately 95–105-second, narrator-led micro-story**. The audience should hear a small scene come alive, understand why Sonic Rift exists, and see **real UI evidence** of generating two genuinely distinct voices, creating ocean ambience, optionally cloning a consenting synthetic voice, arranging a scene, auditioning the mix, and exporting.

**Non-negotiable order:** implement and visually qualify the new UI first (Studio-first navigation, page-specific acoustic backgrounds and distinct voice modes); only then recapture screenshots/video in the real Windows app. This document is **not a Claude production prompt** and authorizes neither recording nor publication.

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

## Proposed storyboard (~100 seconds)

| Time | Narrative beat | Real on-screen action | Sound / speech |
| --- | --- | --- | --- |
| **00:00–00:09** | **Hook: an idea waiting to be heard.** | Open the redesigned Studio page with new acoustic background, optionally a clean fictional project title, then move to Speech. Avoid a dashboard montage. | Guide: “A world can begin with just a few words.” No music or unrelated sound effects. |
| **00:09–00:25** | **Give the scene its first voice.** | Speech, Keeper voice clearly selected, type a short line, generate, audition and keep. Show readable take metadata and Add to Studio. | Keeper: “The beacon is still burning. Follow it toward shore.” Let the generated voice finish without guide overlap. |
| **00:25–00:37** | **A second character answers.** | In Speech, deliberately change voice selection to a **different preset/voice ID**, generate a second take and audition; add it to Studio. The change must be unmistakable on screen and by ear. | Guide: “Now someone answers from across the water.” Traveler: “I see it now. Keep the light on.” |
| **00:37–00:51** | **Build the place.** | Sounds > Ocean waves; render several takes only if the actual controls support it, audition, keep the selected ambience, and Add to Studio. Show the Sounds-specific page texture. | Guide: “Give their conversation a shoreline.” Bring up genuine locally generated surf, then allow 3–4 seconds of unmasked waves. |
| **00:51–01:05** | **A voice returns.** | Voices > New voice > Clone; use the **consenting synthetic Keeper** as reference, generate a new line, audition, and save if legitimately supported. Show Clone-specific wave background. | Guide: “And keep a character’s voice consistent as the story grows.” Keeper clone: “I’ll keep it burning until you’re home.” |
| **01:05–01:29** | **The creative payoff.** | Studio: show waveforms for two distinct speakers and the ocean bed. If app supports inserting the newly cloned take using a verified path, include it; otherwise don't imply it is in the mix. Arrange and balance, save the fictional project, then play the **real, synchronized Studio preview**. No unsaved-changes warnings in finished hero footage. | Guide: “Bring the voices and the atmosphere together.” Then **guide stays silent** while the actual mixed scene plays: ocean underneath the Keeper and Traveler, optionally including the cloned line. |
| **01:29–01:40** | **Completion, not a feature dump.** | Export a genuine mastered output from the saved project. Hold briefly on the complete Studio page and Sonic Rift identity, not on an explorer path or modal. | Guide: “From a few lines to a world you can hear. Sonic Rift.” Finish with the official tagline **“Make worlds you can hear.”** |

**Timing is an editorial target, not a requirement to speed up or cut across a spoken word.** Adjust with measured render/playback and breathing room. Condensing long model waits is allowed **only when explicitly disclosed**; never replace generated takes or app screens with fabricated output.

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
