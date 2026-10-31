# Sonic Rift Music Generation: Phase 0 model and product research

**Status:** RESEARCH PROPOSAL, NOT AN APPROVED MODEL INSTALL OR RELEASE  
**Prepared:** 2026-10-30 · **Source base:** `main` `f3b276b54defef40ef37b8994eb95d93bc382756`  
**Tracking:** [#128](https://github.com/Knapp-Kevin/sonic-rift/issues/128), [#53](https://github.com/Knapp-Kevin/sonic-rift/issues/53), [#71](https://github.com/Knapp-Kevin/sonic-rift/issues/71), [#55](https://github.com/Knapp-Kevin/sonic-rift/issues/55), [#60](https://github.com/Knapp-Kevin/sonic-rift/issues/60), [#61](https://github.com/Knapp-Kevin/sonic-rift/issues/61).

## Decision to test, not yet a product release decision

**Proposed first phase:** new **Music** creation workspace with a strong *instrumental score/underscore* use case, followed by optional original-lyrics/song vocals and then music editing. Generated tracks become sound-library-backed clips in the existing Studio timeline. Sonic Rift should not become a full DAW by accident, nor should music be collapsed into the Sound Effects/ambience workflow.

**Primary engineering candidate:** ACE-Step 1.5, *regular 2B turbo/SFT*, for songs and instrumentals on the existing RTX 5070 Ti 16 GB Windows workstation. **Best independent instrumental comparator:** Stable Audio 3 Small-Music/Medium. **Future vocal comparator:** HeartMuLa OSS. These are **candidates only**; no local generation benchmark, model installation, owner audition, weight hash check or legal clearance has yet occurred.

### Where Music belongs

1. **Music workspace:** prompt + purpose (scene score, theme, rhythmic bed, transition, original song), instrumental vs vocal intent, optional user-owned lyrics, desired duration, style/instrumentation, candidate count, optional tempo/key controls *only when supported*. Review A/B previews and keep selected take.
2. **Library:** save a verified music WAV master with engine, exact model and weight revision, prompt, seed, parameters, generated duration, peak/loudness, rights provenance and a stable content hash. A prompt/seed is an *intent record*, not proof of bit-identical regenerated audio.
3. **Studio:** Add to Studio as a `sound` clip initially, with non-destructive trim/fades/volume/ducking under narration, playback and export. `AudioProject` schema v1 currently allows only `voice`, `sound`, `effect` kinds; do **not** insert an unrecognized `music` kind or rewrite saved projects. If a dedicated `music` track kind becomes valuable, use a versioned schema migration with rollback and compatibility tests.
4. **Engine:** separate pinned subprocess/venv via the established `this_voice_thing/engines/sound_models.py` pattern. Isolate PyTorch/CUDA dependencies, provide explicit install-consent and disk/VRAM estimates, and honor GPU exclusivity across voice, sound and music jobs. Inputs are text or explicitly permitted user references. Outputs stay local and are atomically saved.
5. **Long audio:** existing mixer has a conservative 512 MiB unmastered PCM budget. Long musical tracks plus layered narration will encounter it. Implement chunked/bounded-memory export under #71 rather than silently increasing the cap.

### Verified architectural anchors

- `this_voice_thing/core/soundscape/assets.py`: `AssetLibrary` uses a verified SHA-256 master, 24-bit WAV files, atomic index writes, and optional engine/model/license/seed/prompt/metrics provenance. It does not yet have a music-specific contract.
- `this_voice_thing/core/audio_project.py`: project version 1, integer sample frames, three track kinds, trim/fades, no special music metadata.
- `this_voice_thing/ui/pages/project_editor.py`: currently supports mixing, placing kept sounds, voice clips, in-place narration, undo/redo and export.
- `this_voice_thing/engines/sound_models.py`: standalone sound-model worker environment and pinned source revision (MOSS) show the isolation pattern, but music runtime compatibility is untested.

## Candidate model and rights matrix (official pages, accessed October 2026)

| Family | Capability claim from official source | License / business boundary | RTX 5070 Ti 16 GB hypothesis |
| --- | --- | --- | --- |
| **ACE-Step 1.5** | Text/music, optional lyrics, BPM/key/time metadata, song-length outputs and editing. 2B standard and 4B XL variants. [Source](https://github.com/ace-step/ACE-Step-1.5) · [model card](https://huggingface.co/ACE-Step/Ace-Step1.5) | Official code/model card list MIT; authors describe licensed, royalty-free and synthetic training data. Do not equate that self-description with an independent non-infringement guarantee. Reference audio and uploaded lyrics need their own rights. | **Top candidate.** Official GPU tiers permit regular 2B with 0.6B/1.7B LM around 16GB; XL 4B requires offload below 20GB. Benchmark latency, peak VRAM and actual musical coherence on this GPU. |
| **Stable Audio 3 Small-Music / Medium** | Small-Music 433M, up to 120 seconds, CPU; Medium 1.4B, up to 380 seconds, 44.1 kHz stereo. [Source](https://github.com/Stability-AI/stable-audio-3) · [model overview](https://github.com/Stability-AI/stable-audio-3/blob/main/docs/guides/model-overview.md) | Source MIT; **self-hosted weights subject to the Stability AI Community/Enterprise license**, not MIT. Commercial users have registration/eligibility conditions; revenue-threshold and organization-wide rights must be checked before product use. [Official license](https://stability.ai/license) | **Instrumental baseline and alternative.** Official H200 table shows Medium ~5–7GB GPU allocation, not a measured 5070 Ti result. Small can serve CPU-capable testing. Not a speech/vocal TTS replacement. |
| **HeartMuLa OSS 3B** | Vocal song and lyric/tag control; source says inference ~RTF 1, Python 3.10 recommended. [Source](https://github.com/HeartMuLa/heartlib) · [weights](https://huggingface.co/HeartMuLa/HeartMuLaGen) | Apache-2.0 claimed for source and related OSS model weights as of Jan 2026. Check each selected checkpoint and codec license/notice, not just repository root. | Later vocal candidate. Multi-component codec and dependency versions imply an isolated Python environment, not installation in the main app. |
| **DiffRhythm** | Full-song generation and edit/continuation family. [Source](https://github.com/ASLP-lab/DiffRhythm) | GitHub source marks Apache-2.0. Check actual v1.2 and newer specific model checkpoint rights/consent. | Secondary quality/stability benchmark pending memory and Windows fit. |
| **Meta AudioCraft MusicGen** | Short/melodic music generation and conditioning. [Source](https://github.com/facebookresearch/audiocraft) | Code MIT; official pretrained **weights CC BY-NC 4.0**. **Exclude as default commercial integration** absent separate permission. | Research comparison only; a known code license is not a weight-distribution right. |
| **YuE2** | Explicit symbolic score planning, melody/chord edit. [Source](https://github.com/tidesea/yue) | New YuE2 model weights CC BY-NC 4.0; official Linux / >=24GB VRAM recommendation. | **Not a fit** for initial Windows 16GB deliverable; investigate symbolic planning ideas only. |
| **SongGeneration 2 / LeVo2** | Sung song research family. [Official license](https://github.com/AMAImedia/SongGeneration2-LeVo2/blob/main/LICENSE) | License limits to **academic, research and education**, excluding commercial/production. | **NO-GO** for production integration without a new rights agreement. |

**Copyright/rights caution:** A model being MIT, Apache-2.0 or commercially marketed does **not** establish that any particular generated song is free of similarity claims, that a cover/reference is licensed, or that the user owns protected composition rights. The shipped UX must not claim it does. Do not silently use living-artist names, upload third-party reference songs, or infer performer-voice consent.

## Proposed Phase 0 benchmark contract

After explicit approval of which **exact** local checkpoints may be fetched, measure each candidate under an isolated offline-after-setup profile:

| Test | Input intent | Required checks |
| --- | --- | --- |
| M-01 | 30s delicate piano/cello scene underscore | Dynamics, musical phrase shape, clean start/end, intelligibility of existing narration over a ducked mix |
| M-02 | 60s rhythmic instrumental travel cue | Rhythm stability, observed tempo vs requested BPM, unwanted loops/repetitions, export integrity |
| M-03 | 120s cinematic fantasy exploration bed | Long-range coherence, memory/latency, transitions, melody continuity and file integrity |
| M-04 | 30s original ambient-to-musical crescendo | Distinction from Sound/SFX, controllable tension, no unintended vocals |
| M-05 (stage 2) | 60s user-owned original lyrics | Lyric word accuracy, vocal quality, reproducibility and rights/provenance |

- Record each test's model SHA, weights SHA, input and seed, output SHA, prompt, Python/CUDA/driver/OS versions, cold and warm model load, elapsed generation, real RTF, peak GPU VRAM/RAM, output duration/rate/channels, LUFS/true peak and observed BPM/key. Publish neutral test data, not user-owned or copyrighted audio.
- The *same seed* does not guarantee identical audio across kernels/devices; document deterministic and nondeterministic behavior separately.
- Compare at matched output duration and loudness with at least two independent consenting listeners. Separate music quality, prompt adherence, production sound, structure, editability and instrumental/vocal performance. Don't use engine-authored score claims as independent listening evidence.
- Use sound/voice provider busy gates, stop/cancel, failed-load recovery, stale result disposal, disk-full and user-data isolation. No unattended multi-GB downloads, training, cloud API usage or GitHub Actions.

## Decision gates

1. **Research only: GO.** This document and issue #128 are permission to review public models, architecture and licensing.
2. **Local installation: HOLD.** Approve precise pinned model/weight versions, storage location, environment isolation and rights first.
3. **Technical alpha: HOLD.** Requires measured local generation, honest commercial-rights status, actual Windows source-run tests, working Add to Studio/undo/export, cancellation, and owner audition.
4. **Public release: NOT PROPOSED.** No public use or licensing claims until #55/#58/#60/#61 and exact installed engine notices are satisfied.

**Preferred delivery sequence:** (A) independent music model bench and audition; (B) instrumental generation as library assets and Studio clips; (C) original lyrics/vocal songs and optional music edits; (D) later true stems, MIDI, score editing or advanced DAW controls only on user-validated need. Keep existing Speech, Sounds and Live behavior intact.
