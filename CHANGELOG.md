# Changelog

All notable changes to **Sonic Rift** are recorded here. The project began as **This Voice Thing**, a fork of [AcTePuKc/Chatterbox-TTS-UI](https://github.com/AcTePuKc/Chatterbox-TTS-UI). Sonic Rift is licensed under the [Apache License 2.0](LICENSE) from 2026-10-31; earlier versions were MIT. The upstream MIT notice is kept in [LICENSES/MIT-Chatterbox-TTS-UI.txt](LICENSES/MIT-Chatterbox-TTS-UI.txt), with provenance in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Unreleased: source-run development checkpoint (2026-10-30)

No general release, packaged Windows executable or installer has been published. Entries below describe code integrated into `main`, **not** a release artifact or universally verified model/device matrix.

### Integrated

- **License: Apache-2.0.** Sonic Rift is now licensed under the [Apache License 2.0](LICENSE), with a [NOTICE](NOTICE) file. The inherited Chatterbox-TTS-UI MIT notice moved, unchanged, to [LICENSES/MIT-Chatterbox-TTS-UI.txt](LICENSES/MIT-Chatterbox-TTS-UI.txt) and still covers any upstream-derived code. Earlier commits remain available under MIT. Engines and model weights keep their own licenses.
- [#120](https://github.com/Knapp-Kevin/sonic-rift/pull/120): Studio-first navigation, page-specific acoustic-wave backgrounds, improved creation/history UI and the genuine owner-approved multi-voice `A World in Sound` film and screenshots ([handoff](docs/marketing/README.md)). [#122](https://github.com/Knapp-Kevin/sonic-rift/pull/122) tracked the individual audio review assets and [#123](https://github.com/Knapp-Kevin/sonic-rift/pull/123) recorded their approval. Website integration is a separate task.
- [#113](https://github.com/Knapp-Kevin/sonic-rift/pull/113): generate narration directly on an existing Studio script clip using the loaded Speech voice, retaining clip identity and undo/redo, exclusive model ownership, cancellation, safe stale-result handling, project persistence and export.
- [#124](https://github.com/Knapp-Kevin/sonic-rift/pull/124): corrected false between-item Live underrun accounting and avoided leading silence on cached synthetic-speech pads. On the tested Windows audio hardware, Kokoro's mixed-soak underruns went from ten to zero; cached-pad first-word onset improved from approximately 205 ms to 130 ms. The latest [measurement record](docs/live-voice-validation-2026-10-30.md) retains the hardware and testing exclusions.
- [#125](https://github.com/Knapp-Kevin/sonic-rift/pull/125): removed the inherited application-wide `torch.load` modification; fresh-import guard tests and installed Chatterbox, Qwen3, Kokoro and VoxCPM2 CPU/CUDA evidence were recorded. Remaining derived source and model-weight licensing are still under review.
- [#115](https://github.com/Knapp-Kevin/sonic-rift/pull/115): fractional sample-rate waveform bucket alignment. [#117](https://github.com/Knapp-Kevin/sonic-rift/pull/117) adds a *research proposal* for Performance Direction, not an implemented engine.
- [#121](https://github.com/Knapp-Kevin/sonic-rift/pull/121): documented mandatory release-only Azure Artifact Signing for any future distributed Windows binaries. Signing and packaging are not implemented by this document.

### Still open

- [#61](https://github.com/Knapp-Kevin/sonic-rift/issues/61): exact-head combined Windows regression after the independent #124 and #125 merges.
- [#13](https://github.com/Knapp-Kevin/sonic-rift/issues/13): VoxCPM2 cold rebuffering, real device unplug/recovery, virtual routes and owner Live listening.
- [#71](https://github.com/Knapp-Kevin/sonic-rift/issues/71): timeline zoom/navigation/loop transport and long-project streaming export within safe memory bounds.
- [#55](https://github.com/Knapp-Kevin/sonic-rift/issues/55), [#57](https://github.com/Knapp-Kevin/sonic-rift/issues/57), [#60](https://github.com/Knapp-Kevin/sonic-rift/issues/60): further original-source separation, license/notice evidence, installed dependency rights and repository identity.

## Historical unreleased development notes (2026-10-02)

Changes since upstream commit `22460fd` ("Add best-effort macOS/Linux shell launcher flow").

### Added
- **Navigation by task.** The sidebar is grouped by what you're doing: **Create** (was Generate), **Voices** (the library, with the Studio as its **New voice** tab), **Sounds** (was Soundscape), then **Tools** (Transcribe) and **Setup** (**Models**, and **Settings** for pronunciation, the local API and the log). Speed, pitch, MP3 and subtitle format moved from Advanced into **Finishing touches** on Create, next to what they change. Nothing else changed: voices, sounds, settings and outputs stay where they were.
- **One Models page for every engine.** Sound models now have a **Sounds** tab on Models, next to Cloning, Presets, Design and Conversations, with the same tiles: status, license badge, GPU fit and typical speed. Click to install (after the license and size are shown) or to use it on the Sounds page; **All models** on Sounds jumps there.
- **Soundscape page and Asset Library (Audio Studio, #53).**
  - **Engines:** ambience loops and sound effects from two restriction-free engines:
    - **Procedural:** no model; ocean, rain, thunderstorm, wind, drone, UI chimes.
    - **MOSS-SoundEffect v2:** Apache-2.0.
    - Stable Audio 3 Small SFX was built in, evaluated and removed: its ambience was rejected in listening tests, and its license carries conditions.
  - **Install and consent:** each model gets its own environment, and the app shows the license and download size and asks before installing.
  - **Takes:** several at once, with seeds for repeatability. Loops are seamless (folding for MOSS) and come out at the requested length.
  - **Mastering:** LUFS loudness with true-peak headroom and a gentle limiter, a seam check, stereo widening for mono models, **Start soft** (loops begin at their quietest moment and build) and **Even out dynamics** (a slow leveler that roughly halves the swings); calm ambience defaults to -24 to -27 LUFS.
  - **Export:** WAV, OGG or MP3.
  - **Asset Library:** keeps each sound with its provenance (engine, model, license, prompt or preset, seed, settings, checksum).
- **`scripts/restart_app.py`** (Windows) closes the app the way its close button does, so it saves its settings, then starts it again; it forces the app only if it hangs for 30 seconds. `--close` just closes it.
- **Voice Studio.** A new **Studio** page to make voices in one place: **Clone** a recording or file (use it as is, or let a cloning model re-read a passage in that voice), **Design** from a description with several candidates at once (Qwen3, VoxCPM2, OmniVoice), or **Remix** a voice with words (VoxCPM2's styled cloning). Try any take on a test line, trim, clean up, shift pitch and speed, then **Save voice**: it's frozen as a clip and transcript, so it sounds the same in every render and batch.
- **Voice-first Generate.** Pick a voice with **Change** (yours, or a model's built-in voices); the model list shows only the models that can speak it, and picking a clip voice loads a cloning model if needed. The Voice page is now **Voices**, a library; designing moved from Generate to the Studio (which replaces Keep this voice).
- **Get a token.** The Model page's Hugging Face card links straight to Hugging Face's new-token page, with the Read type preselected.
- **Transcription (speech to text).** A new **Transcribe** page turns audio into text locally with OpenAI's Whisper large-v3 turbo (MIT license, a one-time 1.6 GB download the app asks about first). Detects the language or takes one you pick, shows optional timestamps, saves text or SRT/WebVTT subtitles, and **Send to Generate** speaks the result with any voice. **Transcribe clip** in a library voice's menu fills in its transcript for cloning models, and the local API adds an OpenAI-compatible `POST /v1/audio/transcriptions`.
- **Sonic Rift app icon.** The rift ring and waveform now appear in the title bar, taskbar and Alt+Tab, with simplified versions drawn for 16–40 px so they stay legible. `assets/branding/sonic-rift.ico` (16–256 px) is available for shortcuts; existing pinned buttons keep working (unpin and pin again to show the new icon on them).
- **App icon in the Windows taskbar.** The app shows its own icon there instead of Python's.
- **Qwen3-TTS engine (optional).** Three new models alongside Chatterbox:
  - **Preset voices**, with nine speakers and plain-language style instructions.
  - **Voice design**, which creates a voice from a written description.
  - **Voice cloning**, which can use a transcript of the clip for closer likeness.

  Qwen runs in its own environment, which the app offers to install. Its output can carry the same AI watermark as Chatterbox.
- **VibeVoice engine and Conversations (optional, research use).** A new **Conversations** tab. Write a script with up to 4 speakers (`Name: line`), pick a voice for each with **Cast…** (7 sample voices, your recordings or any clip), and VibeVoice performs it as one natural conversation. Long scripts split only between turns, and each speaker keeps their voice throughout. MIT-licensed but limited to research use by its model card, so it's badged amber **Research use**.
- **OmniVoice engine (optional, non-commercial).** Fast voice cloning and voice design in 600+ languages from a 3 GB model (CC BY-NC 4.0 weights, badged red). Cloning needs the clip transcript; voice design uses an **Attributes…** picker (gender, age, pitch, whisper, accent), with unsupported words caught before generating. Sections are batched, about 3 s for four paragraphs on an RTX 5070 Ti, and a designed voice stays the same through a document.
- **License badges look past wrong tags.** Fine-tunes of a non-commercial model inherit its license even when their own tag claims a permissive one.
- **VoxCPM2 engine (optional).** One 5 GB model for voice cloning (with an optional style, and a clip transcript for closer likeness) and voice design, in 30 languages at 48 kHz. The two uses share one download and switch instantly. A designed voice stays the same through a whole document. VoxCPM runs in its own environment, which the app offers to install, and can add the same AI watermark.
- **Kokoro engine (optional).** 49 built-in voices in 7 languages from a 340 MB model, about 20× faster than Chatterbox. Pick a language, then a voice; the choice is remembered per language. Kokoro runs in its own environment, which the app offers to install, and can add the same AI watermark.
- **GPU requirements on every model tile.** Each tile shows the GPU memory the model needs next to your GPU's, in green when it fits, amber when it runs but slower, and red when the GPU is too small.
- **Faster Qwen documents.** Long text is generated in batches (up to 16 sections or about 5,000 characters per call), roughly 5× faster. Oversized batches are split automatically if the GPU runs out of memory.
- **In-app voice recording.** A guided window with countdown, live level meter, too-quiet and clipping warnings, a 30-second limit, and phonetically rich read-aloud passages. Recordings save the passage as a transcript for Qwen cloning.
- **Document narration:**
  - Open `.txt`, `.md` or `.docx` files.
  - **Preview** a sample, and **Keep this take** so the full render matches.
  - A live estimate of the time and number of sections.
  - Progress with time remaining, and **Stop** keeps finished sections as a `_partial` file.
- **Per-model time estimates.** Every model's estimated time for the current text, learned from your own runs. The estimate is a menu: pick a model from it to switch.
- **Model management in the app:**
  - Add, edit, duplicate, hide and remove models.
  - **Check** a Hugging Face repo before downloading.
  - **Find models** searches Hugging Face for repos this app can load.
  - **Model page tabs and tiles.** Tabs for voice cloning, preset voices and voice design. Your models show as tiles with download status, typical speed and a **license badge** (permissive, non-commercial or unclear). Click a tile to load it.
  - **Discover on Hugging Face** lists more loadable models for each tab, searched in the background. Click one to add it.
- **Hugging Face access** section with token **Save** and **Test**. The token is stored locally, never in `models.json`.
- **Finishing touches:** paragraph pauses, even out volume, trim silence, and WAV/FLAC output.
- **Google Docs import** (**Open... → From Google Docs...**). Paste a link to a doc shared with "anyone with the link", or sign in with Google (read-only) to search and open your own docs. Uses your own free Google Cloud OAuth client; setup steps are in the README.
- **Keep this voice.** After previewing with a voice design model (Qwen, VoxCPM, OmniVoice), keep the voice you heard: it's saved to the voice library and locked in for the full render and later renders.
- **Preview length.** Choose about 3, 5 or 10 seconds next to Preview (it was a whole section, often 15–20 s).
- **Local API** (Advanced page, off by default). Other programs on this PC can generate speech over HTTP on `127.0.0.1`: an OpenAI-compatible `POST /v1/audio/speech` (for Open WebUI, SillyTavern and the `openai` package) and a native `POST /v1/speech` with any model, library voice and subtitles. Requests use the full pipeline, take turns with the app, load models on demand, and can require a token.
- **Experimental native live PCM streaming for VoxCPM2.** `POST /v1/audio/speech` can now return 48 kHz mono s16le PCM while VoxCPM2 is still generating (`stream=true`, `stream_format="audio"`, `response_format="pcm"`). The live path reports its raw/unwatermarked policy in response headers, preserves single-GPU serialization, and includes `scripts/benchmark_live_api.py` for TTFA/RTF measurement.
- **Desktop Live Voice (experimental).** A new Live Voice page can send the currently selected voice directly to a chosen Qt/Windows audio output, queue additional lines, Stop current or Stop all, repeat the last line, and report native/segmented/buffered delivery. Playback uses a bounded QAudioSink buffer with sample-rate/channel conversion and fails closed when a previously saved output device disappears.
- **Persistent TTS soundboard.** Save typed/recent phrases as named pads. Static pads build a content-addressed local WAV cache after their first successful generation and then play without loading the model/GPU; voice/model/style/synthesis/pronunciation changes invalidate stale caches, and deleting pads garbage-collects unreferenced cache files.
- **Live Voice route profiles and monitoring.** Local and external/virtual-microphone profiles persist their own Windows audio device IDs. External routes start disarmed on every launch, fail closed if their device disappears, and can fan the same live PCM to an independent headphone monitor without making monitor failure interrupt the primary route. A spoken Test route action verifies the active path.
- **Discord, Zoom, OBS and generic app setup profiles.** Live Voice can now show the likely paired recording/microphone endpoint for conservative known virtual-cable naming patterns, copy that device name, and display app-specific setup/troubleshooting guidance. Pairing hints remain advisory and the app never automates third-party settings.
- **Soundboard boards and focused shortcuts.** Live Voice can create, rename, switch and delete persistent boards. While the Live Voice page has focus, Alt+1…9 triggers pads, Ctrl+Alt+1…9 switches boards, Ctrl+. stops all speech, and Ctrl+Shift+Enter repeats the last phrase. No global OS hotkeys are installed yet.
- **Live Voice safety/privacy hardening.** Speech queues are bounded by item count and estimated duration, session history is clearable and never persisted, soundboard cache can be purged without deleting pads, cached audio preserves its source provenance, monitor feedback-risk hints are surfaced, and both primary/monitor sinks participate in Stop/drain semantics.
- **Live Voice QA telemetry and route probe.** Audio sinks now track negotiated source/target format, configured-to-start timing, bytes written and underruns; Live Voice can copy a text-free diagnostics JSON snapshot, and scripts/live_voice_route_probe.py validates local/virtual/monitor routes with known PCM independently of TTS. A canonical end-to-end QA runbook defines the hardware merge gate.
- **Live Voice extended interaction consolidation.** Soundboards now support owned audio-file pads, multiple named boards, per-board saved voice/route/trigger defaults, persistent pad ordering, favorites/tags/search, per-pad Queue/Interrupt/Ignore behavior, quick voice favorites, focused board/pad shortcuts, and opt-in Windows global hotkeys with a visible master disable switch. All trigger paths retain bounded-queue and fail-closed routing semantics.

- **Mic Effects foundation.** Live Voice can now use a physical microphone as a first-class source and feed bounded, worker-processed PCM through the existing Local/virtual-mic/Discord/Zoom/OBS routing and monitor paths without transcription. The first low-resource DSP slice provides true pass-through, gain, warm/bright tone shaping, optional compression/limiting, microphone diagnostics, feedback warnings, and a lower-latency output buffer policy. Realtime pitch/formant shifting is intentionally deferred until a suitable low-latency implementation is selected.
- **Discord, Zoom, OBS and Other App route profiles.** External routing now includes guided app-specific setup, enumerates Windows recording endpoints, offers conservative virtual-cable pairing hints such as CABLE Input → CABLE Output, and lets the user copy the suggested microphone name. Ambiguous pairings are left unresolved rather than guessed.
- **Shared live-speech core.** Desktop playback now consumes a UI-independent LiveSpeechSession rather than calling the app's own HTTP API; model/API/file-generation paths are serialized so an active model cannot be unloaded underneath a live utterance.
- **Pronunciation dictionary.** Respell names, acronyms and jargon (`Nguyen → Win`, `SQL → sequel`) for every model, with whole-word and match-case options. **Hear it** and **Try** let you test respellings, and word lists can be imported or exported. Subtitles keep the original spelling; the Generate page shows how many words were respelled.
- **Subtitles.** Tick **Save subtitles** to get an `.srt` or `.vtt` file next to the audio. Captions are timed from the generated sections and snapped to the pauses in the speech, with no speech recognition needed. Speed changes and trimmed silence are accounted for, and conversation captions name their speaker.
- **Advanced page:** speed and pitch changes (formant-preserving) and MP3 export, with a note that they can weaken the AI watermark.
- **Voice library** (the Voice page). Save clip voices, preset voices (Kokoro, Qwen speakers) and designed voices (Qwen, VoxCPM, OmniVoice) by name, with tags and notes, and use any of them with a click. A preset or designed voice can **make a clip**: 15 s reading a phonetic passage with its exact transcript, so cloning models can reuse it. Existing recordings join the library without being moved, and VibeVoice's **Cast…** lists library voices by name.

### Changed
- **VoxCPM2 Live Voice quality setting.** Low latency · 6 steps (default), Balanced · 8, or Full quality · 10, for Live Voice only; Generate and the local API keep 10 steps. On the target machine 6 steps streamed with 0 underruns, RTF ~0.79 and first audio ~0.22 s, where 10 steps gapped on every utterance (RTF ~1.13). A listening check found the voice about the same. Mode labels and diagnostics show the step count, and the status warns when generation falls behind playback.
- **Fewer Live Voice gaps at the start of an utterance.** Once the output had played one item, it stayed started, so every later item began playing its first chunk with no start buffer and one late chunk was an audible gap. A quiet output now refills its start buffer before playing (back-to-back queue items stay seamless), and VoxCPM2 native streams start with 0.35 s buffered. In a 10-minute mixed-load run, utterances with gaps fell from 26 of 88 to 6 of 88; speech starts after about 0.45 s (median). Remaining gaps happen only while VoxCPM2 generates slower than real time, which no buffer can hide.
- **The window code is split up.** `ui/main_window.py` went from about 5,900 lines to about 400. Each page now lives in `ui/pages/` (generate, generation, documents, estimates, finishing, engine controls, player, voice, voice library, using voices, recording, transcribe, models, discover, model loading, model settings, advanced, local API, pronunciations; the Generate, Voice, Model and Advanced pages are built card by card), the dialogs in `ui/dialogs/`, and the threads, API bridge, shared setup and small widgets in their own modules. The code moved without changes, and a test checks that no two pages define the same method.
- **Organised code.** The 20-odd modules that sat in the project folder now live in a `this_voice_thing` package (`ui/`, `engines/`, `core/`, `integrations/`), with `install_torch.py` in `scripts/` and automated tests in `tests/`. `python main.py`, `run.bat` and `run.sh` work as before, and app data (settings, model list, outputs, recordings, voice library, engine environments) stays where it was.
- **New look for This Voice Thing.** A cyan / electric-blue / purple / pink identity on deep navy (dark) or light neutral surfaces (light), built on semantic theme tokens. Cyan marks actions, selection and focus; the brand gradient appears only on progress bars, the recording waveform and a thin sidebar stroke. Amber is now reserved for warnings and caution (uncertain licenses, tight hardware, setup needed), red for errors, green for success. Keyboard focus is visible everywhere, and text meets WCAG AA contrast in both themes.
- **Renamed to This Voice Thing.** The app had outgrown "Chatterbox UI"; Chatterbox remains one of its engines. Runtime names are unchanged for compatibility: outputs still go to `chatterbox_outputs/` as `chatterbox_….wav` (renaming those is a planned migration).
- **The shipped model list only holds models you can actually download.** The placeholder "Example custom…" entries and the "Legacy English compatibility" entry are gone; add an original-layout model with **+ Add repo…** if you need one. Each shipped model's download size is shown on its tile before you load it.
- **New interface:**
  - Sidebar pages (Generate, Voice, Model, Advanced, Log).
  - A light/dark theme that follows Windows, with depth and texture.
  - Plain-language controls: Expressiveness, Pacing, Variation, Take number.
- **Models are grouped by what they do:** cloning, presets, design and conversations, as tabs on the Model page.
- **Text is split where a reader would pause:**
  - Never across paragraphs or headings.
  - Overlong sentences split at clause breaks, not mid-phrase.
  - Qwen sections can hold whole paragraphs.
  - Pauses depend on the type of join.
- **The window sizes itself to its content,** so nothing needs scrolling.
- **Generated audio is saved as standard 16-bit WAV** (previously 32-bit float), with optional volume levelling and silence trimming.
- **Model settings** (repetition, min-p, top-p) are now remembered between sessions.

### Fixed
- **Kokoro works with Windows Smart App Control on.** Kokoro's text front end pulled in an unused spaCy transformer plugin whose unsigned tokenizer binary Smart App Control blocks, so English Kokoro failed to load. Installs now remove the plugin (`spacy-curated-transformers`, `curated-tokenizers`); English G2P and speech were verified without it.
- **A missing Chatterbox library no longer blocks every engine.** If `chatterbox-tts` fails to import, only the Chatterbox engine is unavailable; Qwen, Kokoro, VoxCPM2, OmniVoice and VibeVoice still load. The load log no longer says "Chatterbox model" for every engine.
- **VoxCPM2 installs without `funasr` and `kaldiio`.** `voxcpm` declares `funasr`, which pulls in `kaldiio`, licensed by NTT for evaluation only (no redistribution); every kaldiio release carries that license. VoxCPM's inference uses neither, so they're removed after install; VoxCPM2 was verified to load and speak without them. Existing installs drop them on the next reinstall.
- **Outputs always go to the app's own `chatterbox_outputs` folder**, even when the app is started from another directory.
- **Engine installs on Windows:**
  - They work around a uv bug that broke Python 3.12 environments.
  - They refuse up front, with a fix, when the app's folder path is too long for Windows' 260-character limit, instead of failing halfway.
- **The window no longer widens with several finishing touches on.** The Finishing touches summary (e.g. speed, pitch, pauses, MP3) now shortens to fit, with the full text in its tooltip.
- **Qwen cloned voices no longer "reset" at section seams.** A cloned or saved designed voice drifted from its reference over long sections and snapped back at the next one. Qwen cloning now uses 300-character sections (was 600) and, while Variation is on its default, a steadier 0.5; measured on a designed voice, the drift is gone and the seams match more closely.
- **Long renders can't be cut short by a stray key.** Generate turns into Stop while rendering and kept keyboard focus, so Space or Enter could stop a render and drop its last sections. It no longer takes focus, a stop is logged again (a console redirect used to hide it), and the status says which sections weren't generated.
- **Settings are saved when a generation starts**, not only when the app closes, so a crash or forced close doesn't lose them.
- **Taskbar icon, for real this time.** Windows sometimes showed a generic icon because it asked the window for its icon while start-up work kept the window busy, then kept the generic one. The window now hands Windows its ID, icon file and relaunch command up front, so the brand icon always shows, and pinning the app pins This Voice Thing.
- **Designed voices stay frozen.** **Keep this voice** now also appears after a full render, saves the description that made the voice even if you edited the box afterwards, and **Save voice** on the Voice page saves the exact voice you heard instead of only its description (which designs a new voice each time). Saving a kept voice again edits it instead of adding a duplicate.
- **Qwen voice design no longer changes voice between sections.** The first section is designed and the rest are cloned from it with Qwen3's cloning model (voice similarity between sections 0.76 → 0.91).
- **Long voice names no longer widen the window**; the voice chip shortens them.
- **Kokoro's voice picker no longer widens the window** (its long voice names set the minimum width).
- **Windows installer:**
  - Batch files are now checked out with Windows line endings. Before, steps could run out of order and report success after a failure.
  - Newer NVIDIA drivers no longer cause a CPU-only PyTorch install.
  - A dependency URL conflict that newer `uv` versions reject is resolved.
- **Qwen works offline** once its models are downloaded.
- **A slider rounding error:** Expressiveness could go below its minimum (0.20 instead of 0.25).
- **Windows-1252 text files** now open correctly.
- **Cancelling the file browser** no longer clears the selected voice.
