# Marketing media manifest

Media for the MythologIQ Labs site, issue [#118](https://github.com/Knapp-Kevin/sonic-rift/issues/118).
**Status: approved by the owner (Kevin Knapp) on 2026-10-30 for use on the website.**

The first media pass (build `4ea641f`) is archived, unchanged, in [archive/2026-10-30-v1](archive/2026-10-30-v1/README.md).

## Provenance

- **Build:** commit `d9e8179` on PR [#120](https://github.com/Knapp-Kevin/sonic-rift/pull/120) (Studio-first UI and page-specific sonic-wave backgrounds), run from source.
- **Captured:** 2026-10-30 on Windows 11 Pro 10.0.26300, Python 3.11.9, PySide6 6.9.0 (Qt 6.9.0), PyTorch 2.8.0+cu128, NVIDIA RTX 5070 Ti.
- **How:** a script drove the real main window, rendered off-screen (`QWidget.grab`), in a fresh disposable profile (no owner settings, voices, recordings, projects or Sound Library were read or written). Window 1600x900 logical at 1.5x scale: screenshots are 2400x1350 PNG; the film is captured at the same size and encoded at 1920x1080, 30 fps.
- **Demo fixture:** “Evening Tide: The Beacon”, a fictional scene written for these captures.
- **Done before filming (not shown):** the owner-picked voice designs were saved in the profile's voice library as “Guide”, “Keeper” and “Traveler” (Voices, New voice, Clone, use the clip as it is), and an empty project with one “Dialogue” track was created and saved. The Guide's narration lines were spoken beforehand with the same voice (Qwen3-TTS voice cloning) and laid over the picture.
- **Shown in the film, all real:** Speech generating the Keeper and Traveler lines with Qwen3-TTS voice cloning and adding them to the Studio; Sounds generating procedural Ocean waves and keeping them as “Shoreline waves”; Voices cloning the Keeper's take with VoxCPM2 and saving “Keeper (cloned)”, which then speaks a new line on Speech; the Studio arrangement (clip drags), track gain (-6 dB), clip fades on the waves (1.5 s in, 3 s out, via Clip properties), Save, an uninterrupted Play mix and a real Export mix (master WAV, stems, manifest).
- **Simulated or condensed:** none of the interface is mocked. Waits for renders and model loads are shortened; the app's players were muted during capture and the soundtrack was assembled from the audio the app produced, placed at the times it played. Dialogs (names, file pickers, track gain, clip properties, export format) were answered by the script and are not shown. The end card is the approved banner art (`assets/branding/sonic-rift-banner.svg`) rendered with Inter.
- **Soundtrack:** each voice levelled to about -20 LUFS, the waves to -27 LUFS (they fade out over 3 s on a smooth curve), the Studio's own mix to -19 LUFS; the whole film -20.39 LUFS before a look-ahead limiter to -16 LUFS integrated, -1 dBFS peak (at most 3.78 dB of gain reduction). No voice overlaps another.
- **Not shown:** Live output, Transcribe, Models and Settings pages in the film; virtual-cable and conferencing routes (NOT VERIFIED); macOS and Linux (experimental, NOT VERIFIED).

## Voices

| Role | Engine (licence) | How it was made |
| --- | --- | --- |
| Guide (narrator) | Qwen3-TTS 1.7B VoiceDesign + Base cloning (Apache-2.0) | Designed from a written description, picked by the owner, then cloned for each line |
| Keeper | Qwen3-TTS 1.7B VoiceDesign + Base cloning (Apache-2.0) | Same; a weathered, low lighthouse keeper |
| Traveler | Qwen3-TTS 1.7B VoiceDesign + Base cloning (Apache-2.0) | Same; a younger voice across the water |
| Keeper (cloned) | VoxCPM2 (Apache-2.0) | Cloned in the film from the Keeper's take |
| Brand narrator (tagline) | Qwen3-TTS 1.7B VoiceDesign (Apache-2.0) | Owner-chosen resonant baritone, seed 23 |

No real person's voice, likeness, account, credential, private URL or personal file appears. All voices are synthetic; the app's AI watermark option was on for Speech takes.

## Rights and data

- **Interface, video and screenshots:** recordings of Sonic Rift, owned by the project (Knapp-Kevin).
- **Audio:** generated locally by the app (Qwen3-TTS and VoxCPM2, both Apache-2.0; the app's own procedural ocean, no model). Script text written for this demo.
- **Font:** Inter 4.1 (SIL Open Font License 1.1), used for the logos, end card and silent-cut titles. Source archive `Inter-4.1.zip`, SHA-256 `9883fdd4a49d4fb66bd8177ba6625ef9a64aa45899767dde3d36aa425756b11e`.
- **Logos:** derived from the approved masters in `assets/branding/`, which are unchanged.
- **Data classification:** public-safe synthetic demo content.

## Files

| Path (under `docs/marketing/`) | Format | File size | SHA-256 |
| --- | --- | --- | --- |
| `screenshots/sonic-rift-studio-dark.png` | 2400x1350 PNG | 0.16 MB | `100ac0fd805fefa0018c01fe6e1342e1513c71e502b409661d884f990e6d9f3a` |
| `screenshots/sonic-rift-studio-light.png` | 2400x1350 PNG | 0.16 MB | `dfbfc0435e721679a81cfd96aa182be4de5f504be8c732bb94c46e41cac687f2` |
| `screenshots/sonic-rift-studio-empty-dark.png` | 2400x1350 PNG | 0.09 MB | `4ea71d278f1d223c7f5acf5589edbc3943b2d9211bbc26513211d8f8fa9015c4` |
| `screenshots/sonic-rift-speech-dark.png` | 2400x1350 PNG | 0.20 MB | `a7afb636ace412e49d92f354a0337e65fff57f4c96e41fd6ad5e4ae413757ad3` |
| `screenshots/sonic-rift-sounds-dark.png` | 2400x1350 PNG | 0.20 MB | `6552d689dc477b43a06c36121c01a204ea8d0ad14560b3010cff825d8e4a62ae` |
| `screenshots/sonic-rift-voices-clone-dark.png` | 2400x1350 PNG | 0.18 MB | `8cbf84757c4442ceaac40dbd288789b0e1c4074c357c40cac4c55ffaf83608af` |
| `screenshots/sonic-rift-voices-design-dark.png` | 2400x1350 PNG | 0.18 MB | `7faa0779555a0ec2f8b90f175d5ba37f866403e3097d909324e66a69b8dc0929` |
| `video/sonic-rift-beacon.mp4` | 1920x1080, 102.8 s, H.264 + AAC | 4.37 MB | `4100df5b0de50a1988d6166f6120116705bf204d52a2f4e5cc33cfdb739f6a09` |
| `video/sonic-rift-beacon-silent.mp4` | 1920x1080, 102.8 s, H.264 | 3.29 MB | `a7ee5ca6dc97b5238239f8b130f1771efaea59e369b075c8aefb815e3b8d080c` |
| `video/sonic-rift-beacon.en.vtt` | WebVTT, 21 cues | 0.00 MB | `2be0087cc686e843982138f5a7654560b4403e066225f2b2df235fa0b89aacc9` |
| `logo/sonic-rift-lockup-transparent-on-dark.svg` | SVG, vector | 0.00 MB | `d45b1abc69bd151d1406e7f02fc47c5357db463900a0dad1ade6c82be214db40` |
| `logo/sonic-rift-lockup-transparent-on-dark.png` | 2400x680 PNG | 0.19 MB | `14888615b1ee34ef41734f4266a16f9f9fbe4e717d750a40b929658691655087` |
| `logo/sonic-rift-lockup-transparent-on-light.svg` | SVG, vector | 0.00 MB | `9df8c1ee12fbaa80a9a81ed46eb9b349cde407d98f4cf9d1d5174c27b0b8052f` |
| `logo/sonic-rift-lockup-transparent-on-light.png` | 2400x680 PNG | 0.14 MB | `b04dc4dc5e30ea195622d35040f41861d9f48c2c10427e2089efdc1c011f076f` |
| `logo/sonic-rift-lockup-panel.png` | 2400x680 PNG | 0.26 MB | `0cf82bfd7c0723ea99589451f97b9928d89bcaf4d77e3880ef085f323630166f` |
| `logo/sonic-rift-icon-512.png` | 512x512 PNG | 0.11 MB | `1c37a8499bf875b3ac8412d101f2c5a362f7f56b877a2fd61a46453fee5fc5f1` |
| `logo/sonic-rift-icon-1024.png` | 1024x1024 PNG | 0.28 MB | `20fc819b7a104b6476658e1f17fea15ede3c28cd43e6c0d474c53a4a257f4768` |
| `logo/sonic-rift-end-card.png` | 1920x1080 PNG | 0.25 MB | `f0f39833bdda2a3ae9b7e1c93c0feca7adb8a4856973531f8410ae90612f7ed1` |
| `audio/01-guide-a-world-can-begin.wav` | 2.49 s, WAV 24 kHz, 1 ch | 0.12 MB | `e4962e88eeab9ab7b33338b07df1601c6e86530e98e125b0ffaa77b1f4dc0ad4` |
| `audio/02-keeper-the-beacon.wav` | 3.17 s, WAV 24 kHz, 1 ch | 0.15 MB | `137adaf2414d9cbeda99ec946fe82d7f1332b1f1d3db10d181b7c629bbc12db3` |
| `audio/03-guide-someone-answers.wav` | 2.32 s, WAV 24 kHz, 1 ch | 0.11 MB | `47560e89d8025f50e862441410df31cc12e05725a47c451272a812bfee6f8690` |
| `audio/04-traveler-i-see-it-now.wav` | 2.19 s, WAV 24 kHz, 1 ch | 0.11 MB | `42de5f39a2d9a016f5beb6ccdf95ad5d5828a386d7ebc666e40a8ed8ac5429e9` |
| `audio/05-guide-a-shoreline.wav` | 1.93 s, WAV 24 kHz, 1 ch | 0.09 MB | `3fa523c47d05daa3cff3d5f64043d49d6f882fa07aa0bbb2220139eab607cbae` |
| `audio/06-shoreline-waves.wav` | 20.0 s, WAV 48 kHz, 2 ch | 5.76 MB | `15ef246de73c057cb58c8b8604be0dc3c853b70504e0c6e0692df067218d45d2` |
| `audio/07-guide-a-character-can-return.wav` | 2.72 s, WAV 24 kHz, 1 ch | 0.13 MB | `4d3bf34c0b0e0329c85539554939d7139536a656d2cc38f284372b07dbdd9439` |
| `audio/08-keeper-clone-ill-keep-it-burning.wav` | 2.04 s, WAV 48 kHz, 1 ch | 0.20 MB | `b4a47815c1df5daa7c9f3c35e84f352941dea10eb21e3d9a413c9882255379e8` |
| `audio/09-guide-place-every-line.wav` | 3.86 s, WAV 24 kHz, 1 ch | 0.19 MB | `90642812f9810506d194cef3db482724d6a8109e17791c3f638a519fa1ea2a63` |
| `audio/10-guide-together.wav` | 4.96 s, WAV 24 kHz, 1 ch | 0.24 MB | `4c8cafe39b2166b059307d48b534ae1aa5ac8c66668cdfd68d94c658a5496eeb` |
| `audio/11-studio-preview-mix.wav` | 14.5 s, WAV 48 kHz, 2 ch | 2.78 MB | `2339bcd637dbc037c04b74239a13de1ba6d503636772fc8d9160828d7f64586f` |
| `audio/12-brand-narrator-tagline.wav` | 3.44 s, WAV 24 kHz, 1 ch | 0.17 MB | `844a05a1cadd59d8a9772bc2bc701c849433da351234a98aee22572aa6d1cb87` |
| `audio/13-exported-master.wav` | 14.5 s, WAV 48 kHz, 2 ch | 4.18 MB | `8c31e2e3c18acd87d3695ea3e2b25a0e404ef6d7735c787db71811021ecaa228` |
| `audio/voice-designs/guide.wav` | 2.56 s, WAV 48 kHz, 1 ch | 0.25 MB | `91e8e930abddadc0ae3280e4f56f1fdebb2bdee045b4682b50a8aa6fd4922b11` |
| `audio/voice-designs/keeper.wav` | 3.52 s, WAV 48 kHz, 1 ch | 0.34 MB | `72c086dbee87c1c8c5b32c19c69a4bd360b841001a4d852cb2308523a118747f` |
| `audio/voice-designs/traveler.wav` | 2.56 s, WAV 48 kHz, 1 ch | 0.25 MB | `3dc0e2b937157d01f1aa794a2ed338e0f458af46ef8afd1c2fb08ae3d5040d5c` |
| `video/sonic-rift-beacon-poster.jpg` | 1920x1080 JPEG | 0.31 MB | `153437bdaf248eb3d2b0d718081d035bb0abcc216d992344dccc1d80d8c631ae` |

## Checks done

- Every PNG/JPEG opens at the stated size; both MP4s decode without errors (`ffmpeg -f null`) and probe as H.264 1920x1080, 102.8 s, the main one with AAC 48 kHz stereo.
- Whisper (the app's transcriber) heard every word of all 19 spoken captions inside each caption's time window in the finished soundtrack; it also heard every word of each voice clip (see [audio/README.md](audio/README.md)).
- Speaker check (Chatterbox voice encoder): every line is closest to its own designed voice.
- The exported master and the Studio preview mix fade in from silence and out to silence.
- The build passes its full test suite on Windows (see PR #120 for the exact count and SHA).

## Approval

- 2026-10-30: the owner watched the film and reviewed the set, and approved it (“approved 1,000 times approved”, in chat with Claude), recorded on [#118](https://github.com/Knapp-Kevin/sonic-rift/issues/118).
- Website deployment and any announcement are separate steps for the web developer and the owner.
