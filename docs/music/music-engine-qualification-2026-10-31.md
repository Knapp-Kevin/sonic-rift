# Music generation: engine qualification and first vertical slice

**Date:** 2026-10-31 · **Branch:** `feat/music-generation-20261031` from `main` `6fa8d0e` · **Issue:** [#128](https://github.com/Knapp-Kevin/sonic-rift/issues/128)
**Hardware:** Windows 11 Pro, NVIDIA RTX 5070 Ti 16 GB (driver 617.14), source run.

This builds on the [Phase 0 research](phase0-model-landscape-2026-10-30.md). It records what was installed (with owner approval), what was measured on this PC, and what Sonic Rift's Music slice does. Published model claims are not repeated as measurements.

## Engines: installed, deferred and rejected

| Candidate | Status | Exact source / weights | License (code / weights) | Notes |
| --- | --- | --- | --- | --- |
| **ACE-Step 1.5, 2B turbo + 1.7B planner** | **Installed (owner-approved 2026-10-31) and integrated** | Code `ace-step/ACE-Step-1.5` @ `ca1e85fe9430179831e6bc6be790c332190a3866`; weights `ACE-Step/Ace-Step1.5` @ `19671f406d603126926c1b7e2adc169acbcade22` | MIT / MIT (not gated) | Environment built from upstream `uv.lock` (`uv sync --frozen`), Python 3.12.15, torch 2.7.1+cu128 (includes `sm_120` for Blackwell). Weights 9.4 GB: DiT turbo 4,787,825,604 B; LM 1.7B 3,708,521,528 B; Qwen3-Embedding-0.6B 1,191,586,416 B; VAE 337,431,388 B (sizes match the Hub listing for the pinned revision). Environment 6.2 GB. |
| Stable Audio 3 Small-Music / Medium | **Deferred (owner decision 2026-10-31)** | Not downloaded | MIT / Stability AI Community License | Weights aren't MIT: free below a revenue threshold, with registration for commercial use. The owner rejected SA3 for sound effects by ear and prefers restriction-free models. Revisit only if ACE-Step instrumentals disappoint. |
| HeartMuLa OSS 3B | Later (vocal comparator) | Not downloaded | Apache-2.0 claimed | Evaluate after the instrumental workflow is in use. |
| DiffRhythm | Later | Not downloaded | Apache-2.0 (source listing) | Secondary comparator. |
| MusicGen, YuE2 | Rejected for product use | — | Weights CC BY-NC 4.0 | Non-commercial weights. |
| SongGeneration 2 / LeVo2 | Rejected | — | Research and education only | Not usable in a product. |

ACE-Step's authors say their training data is licensed, royalty-free or synthetic. That is their statement, not an independent guarantee that a particular output resembles no existing work. The app doesn't claim otherwise.

## What the slice does

- **Contract** (`this_voice_thing/core/music/contract.py`, version 1): `MusicRequest` (prompt, instrumental or vocal, the user's own lyrics, length, takes, seed, optional BPM, key, beats per bar, genre, mood, instrumentation); `MusicCapabilities` per engine; `validate()` returns every problem in plain words, and controls an engine lacks are refused with its reason. `MusicResult` and `MusicTake` carry the exact model and source revisions, license, device, timings, peak GPU memory, loudness and peak, plus what the engine says it chose (tempo, key).
- **Service** (`core/music/service.py`): the only place music is generated. Qt-free, so a future agent adapter (#130) calls the same entry point under the app's model ownership. It takes no file paths from callers. It validates every take (length within 10%, finite samples, not silent), masters to −16 LUFS with a −1 dBTP ceiling, and removes partial files on failure or cancel.
- **Engine** (`engines/music_models.py`, `engines/acestep/acestep_worker.py`): an isolated subprocess speaking the existing JSON-lines worker protocol. The worker runs with Hugging Face offline and refuses to load if a weight folder is missing, so a start never downloads. Install (after the consent dialog) clones the pinned commit, builds from upstream's lock file and fetches the pinned weights revision. Cancel ends the worker's whole process tree.
- **Music page** (sidebar *Make › Music*): prompt, genre, mood and instruments; Instrumental (lyrics field when off); length; takes; seed; tempo, key and beats per bar, each disabled with a reason when an engine lacks it; a limits line; Generate and Cancel with progress; takes A, B and so on, with Play, *Switch A/B* (the other take from the same moment), *Keep in library* and *Keep and add to Studio*; a Kept music list with Play, Rename, Delete, Export and Add to Studio.
- **One big model at a time:** starting music asks to unload a voice model on the GPU, and unloads a sound model. Starting a sound model or loading a voice model unloads music, and waits if music is composing. Live Voice must be stopped first.
- **Library and Studio:** kept takes are Sound library assets with `kind: "music"` (a new optional field; older entries read as sounds). They store 24-bit WAV masters, SHA-256, prompt, settings, lyrics, model and source revisions, seed, license, loudness, peak, duration, sample rate and channels. Writing an asset is now all-or-nothing: no index entry without its master, no orphaned master. Studio places music as an ordinary `sound` clip, so `AudioProject` stays at schema v1. Trim, fades, gain, ducking under narration, save, reopen and export all apply unchanged, with the 512 MiB mix budget kept.

## Measurements on this PC

MEASUREMENTS_PLACEHOLDER

## Tests

TESTS_PLACEHOLDER

## Outstanding

OUTSTANDING_PLACEHOLDER
