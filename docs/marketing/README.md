# Sonic Rift: website media handoff

Everything the web developer needs for the Sonic Rift page, from issue [#118](https://github.com/Knapp-Kevin/sonic-rift/issues/118). Checksums, provenance, voices and rights are in [MANIFEST.md](MANIFEST.md). **These are review candidates: owner approval is required before public use.**

## Product description (suggested, 44 words)

> Sonic Rift is a local-first audio studio for Windows. Give characters their own voices, keep a voice so it returns sounding the same, generate ambience like ocean waves, and arrange it all on one timeline into a mastered mix. Your text, recordings and audio stay on your PC.

Shorter (12 words): *Make worlds you can hear: voices, sound and a studio, on your PC.*

## Assets and suggested placement

| Asset | Use it for |
| --- | --- |
| [`video/sonic-rift-beacon.mp4`](video/sonic-rift-beacon.mp4) | The product film, “A World in Sound” (about 1:43, with sound). “See it work” section, with the poster, captions and transcript; no autoplay with sound. |
| [`video/sonic-rift-beacon-silent.mp4`](video/sonic-rift-beacon-silent.mp4) | Muted autoplay or hero loop. Titles and speaker-labelled lines are burned in, so it reads without sound. |
| [`video/sonic-rift-beacon-poster.jpg`](video/sonic-rift-beacon-poster.jpg) | Poster frame for the film (the finished, saved Studio scene). |
| [`video/sonic-rift-beacon.en.vtt`](video/sonic-rift-beacon.en.vtt) | Captions track for the film (speakers tagged: Guide, Keeper, Traveler, Brand narrator). |
| [`video/transcript.md`](video/transcript.md) | Transcript and text alternative; link it next to the player. |
| [`screenshots/sonic-rift-studio-dark.png`](screenshots/sonic-rift-studio-dark.png) | Home page hero: the saved Studio scene, two voices and the sea. |
| [`screenshots/sonic-rift-studio-light.png`](screenshots/sonic-rift-studio-light.png) | Light-theme alternative to the hero. |
| [`screenshots/sonic-rift-studio-empty-dark.png`](screenshots/sonic-rift-studio-empty-dark.png) | Optional “start from nothing” image (a new, empty project). |
| [`screenshots/sonic-rift-speech-dark.png`](screenshots/sonic-rift-speech-dark.png) | Feature row: voices and narration (Speech). |
| [`screenshots/sonic-rift-sounds-dark.png`](screenshots/sonic-rift-sounds-dark.png) | Feature row: ambience and sound generation (Sounds). |
| [`screenshots/sonic-rift-voices-clone-dark.png`](screenshots/sonic-rift-voices-clone-dark.png) | Feature row: keep a character's voice (Voices, Clone). |
| [`screenshots/sonic-rift-voices-design-dark.png`](screenshots/sonic-rift-voices-design-dark.png) | Feature row: design a voice from a description (Voices, Design). |
| [`logo/sonic-rift-lockup-transparent-on-dark.svg`](logo/sonic-rift-lockup-transparent-on-dark.svg) | Site header or footer on dark backgrounds (PNG alongside). |
| [`logo/sonic-rift-lockup-transparent-on-light.svg`](logo/sonic-rift-lockup-transparent-on-light.svg) | Site header or footer on light backgrounds (PNG alongside). |
| [`logo/sonic-rift-lockup-panel.png`](logo/sonic-rift-lockup-panel.png) | The approved lockup on its dark panel, for social cards. |
| [`logo/sonic-rift-icon-512.png`](logo/sonic-rift-icon-512.png), [`-1024`](logo/sonic-rift-icon-1024.png) | Product card, app icon tile. |
| [`logo/sonic-rift-end-card.png`](logo/sonic-rift-end-card.png) | The film's closing card (banner art), 1920x1080. |
| [`audio/`](audio/README.md) | Listening-review package: every voice and sound in the film. Not for the site. |

All logo and title text is rendered with Inter 4.1 (SIL OFL).

## Screenshots: alt text and captions

- **Studio (dark):** Alt: “The Sonic Rift Studio: a saved scene, ‘Evening Tide: The Beacon’, with three dialogue lines over a Shoreline waves track that fades in and out.” Caption: “Bring every voice and sound into one scene, then play and export the mix.”
- **Studio (light):** Alt: “The same Studio scene in the light theme.” Caption: “Light and dark themes.”
- **Studio (empty):** Alt: “A new, empty Studio project with one Dialogue track.” Caption: “Every world starts empty.”
- **Speech:** Alt: “The Speech page with the saved voice Traveler, the line ‘I see it now. Keep the light on.’ and its takes.” Caption: “Give each character a voice and generate their lines on your PC.”
- **Sounds:** Alt: “The Sounds page: a procedural Ocean waves preset, two takes with loudness figures, and the Sound library.” Caption: “Generate seamless ambience and keep the take you like.”
- **Voices, Clone:** Alt: “Voices, New voice, Clone: two VoxCPM2 takes made from the Keeper's line, with a test line and Save voice.” Caption: “Keep a character's voice so it returns sounding the same.”
- **Voices, Design:** Alt: “Voices, New voice, Design: a written description of a voice and the Qwen3 voice design model.” Caption: “Describe a voice and hear it.” (The take list is shared between Clone and Design, so the clone takes from the previous step are still listed.)

## Video embed notes

- About 1:43 (102.8 s), 1920x1080 H.264, AAC stereo at about -16 LUFS. Show the poster and controls; attach the captions (`kind="captions"`, `srclang="en"`) and link the transcript.
- For a muted loop use the silent cut, with the captioned version one click away.

## Wording guardrails

- Say **Windows** (maintained). macOS and Linux are experimental and unverified.
- Say voices are **synthetic** and made on the user's PC; don't imply any real person's voice.
- Don't claim virtual-cable, Discord, Zoom or OBS support (not verified), an installer or a store listing.
- No accessibility, security, performance or compliance guarantees.

## Preview

![The Studio: a saved scene with three dialogue lines over Shoreline waves](screenshots/sonic-rift-studio-dark.png)
