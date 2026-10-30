# Marketing media manifest

Media for the MythologIQ Labs site, issue [#118](https://github.com/Knapp-Kevin/sonic-rift/issues/118). **Status: ready for owner review; not approved for public use yet.**

## Provenance

- **Build:** commit `4ea641f` on branch `docs/marketing-media-118` (based on `main` `f7a9cf9`), run from source.
- **Captured:** 2026-10-30, on Windows 11 Pro 10.0.26300, Python 3.11.9, PySide6 6.9.0, PyTorch 2.8.0+cu128, NVIDIA RTX 5070 Ti.
- **How:** a script drove the real main window, rendered off-screen (`QWidget.grab`), in a fresh, empty profile folder. Screenshots: 1600 x 900 logical window at 1.5x scale (2400 x 1350 PNG). Video: 1600 x 900 at 30 fps.
- **Demo fixture:** “Evening Tide”, a fictional wind-down project written for these captures. Narration: Kokoro-82M built-in voice *Heart* (the app's AI watermark option was on). Ocean bed: the app's procedural *Ocean waves* preset (no model). Cloned voice: VoxCPM2 cloning the synthetic Kokoro narration, saved as the fictional “Evening narrator”. No real person's voice, account, credential, private URL or personal file appears.
- **Simulated or condensed:** none of the interface is mocked. In the video, waits for renders are shortened (one frame stands in for the wait), every player in the app was muted during capture, and the soundtrack was assembled from the audio the app produced (takes, the Studio's preview mix) at the times it played. Dialogs (file pickers, names) were answered by the script and are not shown. The Save voice details dialog was answered with the name “Evening narrator”.
- **Not shown:** Live output, Transcribe, Models and Settings; virtual-cable / conferencing routes (unverified); macOS and Linux (experimental, unverified).

## Rights and data

- **Interface and video:** screenshots and recordings of Sonic Rift, owned by the project (Knapp-Kevin).
- **Audio:** generated locally by the app: Kokoro-82M (Apache-2.0) and VoxCPM2 (Apache-2.0) speech, the app's own procedural ocean. Script text written for this demo.
- **Logos:** derived from the approved masters in `assets/branding/` (see logo notes below).
- **Data classification:** public-safe synthetic demo content.

## Files

| Path (under `docs/marketing/`) | Size | File size | SHA-256 |
| --- | --- | --- | --- |
| `screenshots/sonic-rift-studio-dark.png` | 2400x1350 | 0.38 MB | `56415d24c0127b82529d668485ce4121b342c6cc235a82d619650ba38122842a` |
| `screenshots/sonic-rift-speech-dark.png` | 2400x1350 | 0.39 MB | `054a179434f8b9c98de9c9dd7d97f3b8c4f09f2091f0d5f931440197ac5af07a` |
| `screenshots/sonic-rift-sounds-dark.png` | 2400x1350 | 0.39 MB | `7e7476e5dd5b74858c0a570a9b994bc291a0dd1a5d68ecfd47d60a8ddd32d6d2` |
| `screenshots/sonic-rift-voices-clone-dark.png` | 2400x1350 | 0.41 MB | `54690b1a90de4fd2e656462376ab4ef0584807669f71ade287e06b670b903cf9` |
| `screenshots/sonic-rift-studio-light.png` | 2400x1350 | 0.47 MB | `c752ef2a0a7c2d9a29228170e6f930ecd76178e33a6c24b08c14a82c4819f6c9` |
| `logo/sonic-rift-lockup-transparent-on-dark.svg` | vector | 0.00 MB | `d45b1abc69bd151d1406e7f02fc47c5357db463900a0dad1ade6c82be214db40` |
| `logo/sonic-rift-lockup-transparent-on-dark.png` | 2400x680 | 0.18 MB | `3ace48a97668a0a0256325a5030957afc5f2c266242281db38fa8118620ac4b0` |
| `logo/sonic-rift-lockup-transparent-on-light.svg` | vector | 0.00 MB | `9df8c1ee12fbaa80a9a81ed46eb9b349cde407d98f4cf9d1d5174c27b0b8052f` |
| `logo/sonic-rift-lockup-transparent-on-light.png` | 2400x680 | 0.13 MB | `1cf1f0eb765894807a8c73bad85e8035d65991a34c809400b37b32977ed9931e` |
| `logo/sonic-rift-icon-512.png` | 512x512 | 0.11 MB | `1c37a8499bf875b3ac8412d101f2c5a362f7f56b877a2fd61a46453fee5fc5f1` |
| `logo/sonic-rift-icon-1024.png` | 1024x1024 | 0.27 MB | `20fc819b7a104b6476658e1f17fea15ede3c28cd43e6c0d474c53a4a257f4768` |
| `video/sonic-rift-walkthrough.mp4` | 1600x900 | 2.91 MB | `e6c48a82e47aa39fcb6e8685e556e53cb6c68282759e7452dde113dd4228caea` |
| `video/sonic-rift-walkthrough-silent.mp4` | 1600x900 | 2.40 MB | `3f68da3ddc192a600eda3a73f4614d1a4648912953cf96c3c8547ecfb5f0c61e` |
| `video/sonic-rift-walkthrough-poster.png` |  | 0.27 MB | `7efa20784b6525539c4aa5152d51333b1bee7ed0873118823ab687e3da434c93` |
| `video/sonic-rift-walkthrough.en.vtt` |  | 0.00 MB | `6dacfc2adfa869e445a578050b0c442a1f6cd9b057e948176690a3ff1144bd93` |
| `video/transcript.md` |  | 0.00 MB | `147ccda09dbae3c1c3962f966ea7a00a5e06b906903014a91bc78985ac32065e` |

## Screenshots: alt text and captions

**`screenshots/sonic-rift-studio-dark.png`**

- Alt: The Studio: a 60-second ocean bed from Sounds and two narration takes from Speech on one timeline, with the track list below.
- Caption: Arrange speech and sound from every page on one timeline, then play and export the mix.

**`screenshots/sonic-rift-speech-dark.png`**

- Alt: The Speech page: a wind-down script, the built-in Kokoro voice Heart, delivery controls and two generated takes with Add to Studio.
- Caption: Write a script, pick a voice and generate narration on your own PC.

**`screenshots/sonic-rift-sounds-dark.png`**

- Alt: The Sounds page: a procedural ocean-waves preset, three 60-second takes with loudness metrics, and the Sound library.
- Caption: Generate seamless ambience like ocean waves, compare takes and keep the best one.

**`screenshots/sonic-rift-voices-clone-dark.png`**

- Alt: Voices, New voice: three VoxCPM2 clone takes made from a synthetic narration clip, with refine and save controls.
- Caption: Clone, design or remix a voice, then save it so it sounds the same every time.

**`screenshots/sonic-rift-studio-light.png`**

- Alt: The same Studio project in the light theme.
- Caption: Light and dark themes follow your Windows setting.

## Walkthrough

- `video/sonic-rift-walkthrough.mp4`: 67.35 s, 1600x900, H.264 + AAC, soundtrack about -16 LUFS. `-silent.mp4` is the same picture without audio.
- Poster: `video/sonic-rift-walkthrough-poster.png` (the finished Studio project).
- Captions: `video/sonic-rift-walkthrough.en.vtt` (spoken lines timed from the audio, plus sound cues). Transcript and text alternative: `video/transcript.md`.
- Short text alternative: *Sonic Rift turns a short script into narration, generates an ocean bed, arranges both on the Studio timeline, plays and exports the mix, then clones a voice from the narration.*

## Logo notes

- The approved lockup (`assets/branding/sonic-rift-logo-lockup.svg`) sits on a dark panel. The two `sonic-rift-lockup-transparent-*` files are **derived variants pending owner review**: the panel is removed; the on-light version has dark text and no glow. The approved masters are unchanged.
- The PNG wordmarks were rendered on a machine without the Inter font, so the text uses a fallback sans-serif. Use the SVGs where Inter is available, or re-export the PNGs with Inter installed before public use.
- Icon PNGs (512, 1024) are straight renders of the approved `sonic-rift-icon.svg`.
- Usage: keep clear space of about the symbol's radius around the lockup; don't recolour the rift gradient (cyan #22D3EE, blue #4F7BFF, violet #A78BFA), stretch it or put it on busy imagery. Attribution text where needed: “Sonic Rift by Knapp-Kevin”.

## Checks done

- Every PNG opens with the stated size; both MP4s probe as H.264 at the stated size and duration (the main one with AAC audio).
- Captions were generated from the same audio as the soundtrack; their text matches the script and the VoxCPM2 passage word for word.
- README links to these files resolve in the branch.
- The pinned build passes its test suite (463 tests) on Windows.

## Outstanding before public use

1. Owner review and approval of every asset (and of the derived logo variants).
2. Owner listening check of the walkthrough soundtrack.
3. Re-export the PNG wordmarks with Inter installed, if the PNGs are used.
4. This build (the Studio page and sidebar changes) is in a draft PR awaiting review; if review changes the interface, recapture.
5. No public release, website deployment or announcement is part of this work.
