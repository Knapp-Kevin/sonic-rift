# Audio Studio: Phase 0 research and proposed ADR (#53)

> **Historical research snapshot, 2026-10-13.** Counts, source comparisons, package inventories, model licensing, and recommendations describe the audited revision, **not the current Sonic Rift `main`**. Subsequent implementation includes independent provider #77, core refactors #75/#78/#85/#86, and adopted MOSS soundscape implementation. Review current `docs/upstream-provenance-audit.md`, `THIRD_PARTY_NOTICES.md`, and release issue #61 before treating any result as a live production assertion. No new tests or downloads were performed during this archival integration. **Stable Audio 3 was evaluated but not retained as the selected shipping sound model; MOSS and procedural generation were adopted later.**

**Status:** research complete. **ADR accepted 2026-10-13: full GO** (see §6). This document records the research; implementation is tracked in the child issues.
**Date:** 2026-10-13. **Machine:** Windows 11, RTX 5070 Ti 16 GB, Ryzen 7 7800X3D, 1.7 TB free disk.

| File | What it holds |
| --- | --- |
| This document | Reuse map, baseline results, options, ADR |
| [model-matrix.md](model_matrix.md) | Every candidate model with cited license, length, sample rate, VRAM, Windows risk |
| [model-shortlist.md](model_shortlist.md) | Ranked benchmark shortlist, exclusions, unverified points |
| [procedural_baseline.py](procedural_baseline.py) + [metrics](procedural_baseline_metrics.json) | Zero-model baseline generator and its measurements |

## Recommendation in one paragraph

**LIMITED GO.** Build a **Soundscape page** on the existing app core (option A below) and ship the **procedural engine first**. It needs no model or download, has no license risk and loops seamlessly by construction, and it already produces measured, seamless 60 s loops in 1–4 s on the CPU. In parallel, and only with the owner's approval to download and accept Stability's gated terms, **benchmark `stabilityai/stable-audio-3-small-sfx`** in its own worker environment against that baseline. Defer the multi-track arrangement timeline (option B) until the Soundscape page and asset library exist. Pilot: **Gentle Ocean Waves**, 60 s seamless loop.

## 1. What the current app already provides

| Need for Audio Studio | Existing piece | Reuse |
| --- | --- | --- |
| Run a heavy model without breaking the app's torch/deps | `engines/worker.py` `WorkerProcess`: one long-lived process per engine in its own venv, JSON-lines protocol, `install_env()` | **Direct.** A sound-generation model becomes another worker (SA3 pins torch 2.7.1; MOSS needs torch 2.9, so separate venvs are required anyway). |
| Model catalogue, licenses, hardware fit, download state | `core/model_registry.py`: `Engine`, `CAPABILITIES`, `capability_for`, `resolve_license`/`license_badge`, `HardwareNeeds`, `cached_repo_sizes`, `check_repo` | **Extend.** Add a `sound` capability (and later `music`); license badges and hardware estimates carry over. Capabilities today are voice-only (`clone`, `preset`, `design`, `conversation`). |
| Find / add / download models with consent | Models + Discover pages, `dialogs/models.py`, HF token setting | **Direct**, with a non-voice filter. |
| Post-processing and export | `core/audio_effects.py`: `even_volume`, `trim_silence`, `save_audio` (WAV/MP3), finishing settings | **Extend.** Add loudness (LUFS) normalization, true-peak limiting, OGG, loop seam check. Note the OGG finding below. |
| Reusable clips with metadata and cache | `core/soundboard.py` (PR #24): boards, pads, imported audio, content-addressed cache | **Pattern for the Asset Library**: provenance fields (engine, model revision, license, seed, prompt, hash) are an addition. |
| Long-running jobs with progress and Stop | `ui/threads.py` generation threads, estimates, Stop handling | **Direct.** |
| Navigation | Sidebar of page mixins in `ui/pages/` | **Direct.** A new page is a new mixin; nothing is replaced. |
| Voice Studio, Live Voice, voice library | `ui/pages/studio.py`, Live Voice (PR #24), `core/voice_library.py` | **Untouched** by options A and B; narration for arrangements comes from Generate. |

No part of the voice workflow has to change to add sound generation. The coupling to clean up first is in the rebrand audit ([../rebrand/README.md](../rebrand/README.md)), e.g. a missing Chatterbox library currently blocks *every* engine from loading.

## 2. Zero-model procedural baseline (measured)

Plain NumPy/SciPy DSP, CPU only, stereo 48 kHz, 60 s. The loops are **periodic by construction**:
- noise is shaped with circular (FFT) filters;
- every modulator completes whole cycles per loop;
- discrete events (drops, thunder) wrap around the loop boundary.

Loudness target in LUFS, true peak kept ≤ −1 dBTP.

| Sound | Generate | Integrated | True peak | Wrap jump ÷ p99 step | Level step at wrap vs interior p95 | Spectral change at wrap vs interior p95 |
| --- | --- | --- | --- | --- | --- | --- |
| Ocean waves | 3.8 s | −20.0 LUFS | −2.1 dBTP | 0.007 | 0.12 vs 3.85 dB | 1.30 vs 1.46 |
| Forest rain | 1.1 s | −22.0 LUFS | −9.9 dBTP | 0.40 | 0.45 vs 1.31 dB | 0.53 vs 0.65 |
| Thunderstorm | 1.6 s | −20.0 LUFS | −9.0 dBTP | 0.32 | 0.60 vs 0.96 dB | 0.37 vs 0.61 |
| Ambient drone | 1.5 s | −24.0 LUFS | −14.6 dBTP | 0.86 | 0.00 vs 3.58 dB | 0.00 vs 0.21 |
| UI chime (one-shot, 1.6 s) | 0.01 s | −13.2 LUFS | −3.0 dBTP | n/a | n/a | n/a |

**On every seam measure, the loop point is no larger a change than an ordinary point inside the loop**, so the loops are seamless by these measures. No clipping, no DC offset. Delivery sizes for 60 s stereo: WAV 24-bit 16.9 MB, OGG ~0.7–0.9 MB, MP3 ~0.8–1.1 MB.

**Not yet known: whether they sound real.** No listening test has been done. Rain, surf and drones are where procedural audio is traditionally strong. Thunder, birds and anything with recognisable sources are where models should win, and that's what the benchmark has to show.

**Engineering finding for the export feature:** libsndfile's Vorbis encoder (via `soundfile`) **crashes the process with a Windows stack overflow** when handed a whole 60 s buffer in one `write()`. Writing in 4,096-frame blocks avoids it. Any OGG export in the app must stream in blocks.

## 3. Model candidates (summary)

Full table with citations: [model-matrix.md](model_matrix.md). Ranked shortlist: [model-shortlist.md](model_shortlist.md).

- **Most well-known open models can't be used commercially:** AudioGen/MusicGen, AudioLDM 1/2, Tango/Tango 2, TangoFlux, MMAudio and AudioX all have non-commercial or research-only weights. They're excluded for a project that will publish assets on a website.
- **Best fit: `stabilityai/stable-audio-3-small-sfx`** (released 2026-05-17).
  - **What it does:** SFX and ambience; up to 120 s of 44.1 kHz stereo per call; supports inpainting and continuation (one way to heal a loop seam); runs on CPU.
  - **Size and data:** about 2.4 GB VRAM (reported); a 3.5 GB download from a gated repo; trained on licensed and Creative Commons data.
  - **License:** the Stability AI Community License. Commercial use is free only below **US$1M total annual revenue** and requires **registration** and **"Powered by Stability AI"** attribution.
- **Permissive alternative: `OpenMOSS-Team/MOSS-SoundEffect-v2.0`** (Apache-2.0, 48 kHz, 30 s per call). Its training data is undisclosed, it's an 11.2 GB download, and its VAE is a pickled `.pth` file, so it must only be loaded in an isolated process.
- **Verified on the Hub (2026-10-13):** the SA3 repos exist, are gated, and are tagged `license:other`; MOSS is Apache-2.0 and not gated. **Not verified:** the SA3 license text itself (gated), whether attribution applies to published outputs alone, and Windows/RTX speed and VRAM.

## 4. Hardware, disk and running cost

| Option | Download | Extra env (est.) | VRAM | No-GPU fallback | Cost |
| --- | --- | --- | --- | --- | --- |
| Procedural | 0 | 0 (NumPy/SciPy already installed) | 0 | Is the CPU path | None |
| SA3 Small SFX | ~3.5 GB | ~5–8 GB (torch cu128 venv; the Kokoro env is 7.5 GB today) | ~2.4 GB reported | Yes (CPU designed) | Free < $1M revenue; registration + attribution |
| SA3 Medium | ~10.4 GB | ~5–8 GB + flash-attn | ~5–6.5 GB reported | No | Same license; Windows flash-attn risk |
| MOSS-SoundEffect v2 | ~11.2 GB | ~5–8 GB (torch 2.9, Py 3.12) | unknown | unknown | Apache-2.0 |

The Hugging Face cache already holds 31 GB of voice models, and there is 1.7 TB free. All runs are local: no cloud or API spend, and no GitHub Actions involved.

## 5. Three UI architectures

| | **A. Soundscape page on the shared core** | **B. Unified multi-track Audio Studio** (Voice Studio becomes a mode) | **C. Sound generator inside the current Voice Studio** |
| --- | --- | --- | --- |
| Migration risk | Low: new page, nothing moved | High: reorganises Studio, Generate and the library | Medium: overloads a voice-focused page |
| Preserves today's workflows | Fully | Only after a large refactor | Mostly, but muddles them |
| Discoverability | Clear sidebar entry | Best long-term, steep at first | Poor: sound hidden under "voice" |
| Complexity | Small vertical slice | Timeline, clips, project schema up front | Moderate, with tangled concepts |
| Path to arrangement | Add an Arrange page later on the same assets | Built in | Awkward |
| Verdict | **Recommended now** | **Later**, once A and the asset library exist | **Rejected** |

Wireflow for A, phase 1:

```
Sidebar: Generate | Studio | Voices | Soundscape (new) | Transcribe | Models | Advanced
                                       |
  Soundscape ────────────────────────────────────────────────────────────────────
  Engine [Procedural ▾]   Preset [Ocean waves ▾]   Seed [53]   Length [60 s]  [x] Loop
  Character:  Intensity ──●──   Brightness ──●──   Width ──●──      (preset-specific)
  [ Generate 3 candidates ]                                   est. 4 s on CPU
  ┌ Candidate A ▶ ─ waveform ─ seam ✓ ─ -20 LUFS ┐ ┌ B ▶ … ┐ ┌ C ▶ … ┐
  [Play looped]  [Keep → Asset Library]  [Export WAV / OGG / MP3]
  Provenance: procedural v1 · seed 53 · preset ocean · CC0-able (own work)
```

With a model engine selected, Preset becomes a prompt box, and a license badge plus a download-consent step appear: the same consent the Models page already shows.

## 6. ADR (proposed)

**ADR-0001: Audio Studio direction**
- **Status:** **Accepted** (2026-10-13), as a **full GO**, amended from the proposal below. Decision owner: Kevin Knapp.
- **Owner's decision:** build for **every available backend**, not one. The app is a front end: whoever downloads and runs a model accepts that model's license, so the Stability Community License is acceptable as a user-accepted license, and the permissive MOSS-SoundEffect v2 ships alongside it, not only as a fallback. The procedural engine remains the zero-download default. Implementation: Soundscape page (option A), Asset Library, procedural engine, Stable Audio 3 Small SFX and MOSS-SoundEffect v2 workers, each in its own environment, each behind a license/consent step before download.
- **Original proposal (kept for the record):**
- **Context:** The owner wants first-party ambience and effects (e.g. 12 missing assets for MythologIQ Studio). The app is voice-only today. Most open sound-generation weights are non-commercial. Provenance of training data varies.
- **Proposed: LIMITED GO.**
  1. Build option **A**: a Soundscape page on the shared core, with a `sound` capability in the registry and a provenance-carrying Asset Library generalized from the soundboard store.
  2. Ship **procedural** generation first (presets: ocean, rain, storm, wind, drone, UI chimes). Seeded and deterministic, with seam check, LUFS/true-peak normalization, and WAV/OGG/MP3 export streamed in blocks.
  3. **Benchmark SA3 Small SFX** locally only after the owner (a) approves a ~3.5 GB download plus a ~5–8 GB environment and (b) accepts Stability's gated terms. Compare it blind against the procedural baseline on the pilot prompts. MOSS-SoundEffect v2 is the backup if the Stability license is unacceptable.
  4. **Defer** option B (arrangement timeline) to its own decision after 1–3.
- **Resource budget:** procedural adds 0 GB. The model benchmark adds ≤ 12 GB disk and ≤ 4 GB VRAM. All local.
- **Consequences:** voice workflows are unaffected. Models arrive through the existing worker and consent patterns. Every asset records engine, model revision, license, seed and prompt.
- **Not claimed:** no therapeutic or clinical efficacy for any generated sound. Content involving veterans or trauma needs separate content review.
- **Alternatives considered:** options B and C (see §5); third-party stock assets (rejected by #53 for maintainability); non-commercial models (excluded by license).

## 7. Child slices to file after GO (not created yet)

1. **Registry:** `sound` capability, license and consent for non-voice models (no download).
2. **Procedural engine:** presets, seeded generation, seam check, normalization, block-streamed export, with tests.
3. **Soundscape page:** candidates, looped preview, keep and export.
4. **Asset Library:** provenance fields, search and preview, generalized from the soundboard store.
5. **Pilot:** Gentle Ocean Waves 60 s loop, delivered for MythologIQ, including a browser playback check.
6. **Benchmark (needs download approval):** SA3 Small SFX worker in its own venv, timing, VRAM, blind A/B against procedural.
7. **Later (separate decision):** Arrange page / option B.

## 8. Questions for the owner

1. GO / LIMITED GO / NO-GO on the ADR above?
2. Approve downloading SA3 Small SFX (~3.5 GB, gated terms) for a benchmark only?
3. Is the Stability Community License acceptable for MythologIQ assets: revenue under US$1M, registration, "Powered by Stability AI"? If unsure, MOSS (Apache-2.0) is the hedge.
4. Will you do a short blind listening pass on the baseline loops (1–5 rating; the `*_x3_listen.wav` files repeat each loop three times to judge the seam)?
