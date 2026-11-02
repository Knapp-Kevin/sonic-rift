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

All runs: RTX 5070 Ti 16 GB, below-normal priority, within the app's recommended limits (8 of 16 CPU threads, 15.4 GB GPU cap), planner on, seed 4100 (4101 for a second take). Every take came back 48 kHz stereo at the requested length, mastered to −16.0 LUFS with true peak at or below −1.1 dBTP and no clipped samples. Times are per take, wall clock, including mastering.

**Loading (final configuration, 2026-11-02):** the 2B renderer, VAE and text encoder stay on the GPU; only the 1.7B planner moves to the CPU between uses (about 1 s each way). After load the GPU holds 8.7 GB; the peak while composing is 10.0 GB. The worker loads the models in 34-43 s; the whole start is about 50 s on an idle PC and was 9 minutes when it competed with a test run at the same priority. A first start after a reboot was about 5 minutes (tokenizer and file cache cold).

| Case | Request | Take times | Engine's plan (BPM, key, meter) |
| --- | --- | --- | --- |
| M01 | 30 s piano and cello underscore, 2 takes | 38.0 s, 17.7 s | 77, C major, 4 · 71, D major, 4 |
| M02 | 60 s travel cue, 110 BPM, D major, 4/4, 2 takes | 34.6 s, 16.8 s | 110, D major, 4 · 110, D major, 4 |
| M03 | 120 s orchestral exploration bed | 39.3 s | 125, F major, 4 |
| M04 | 30 s ambient crescendo | 137 s (earlier, everything offloaded) | — |
| M05 | 60 s folk song, own lyrics, vocal | 27.2 s | 100, F# minor, 2 |

The first take after a start is slower (warm-up). Requested tempo, key and meter were passed through to the plan exactly in M02. The earlier configuration (every idle part offloaded to the CPU, 2026-10-31) took 137-225 s per 30 s take, mostly copying weights: diffusion itself took 0.4-2 s. Keeping everything resident needed more than 16 GB and spilled into shared memory at about 2% GPU use.

**Not measured:** whether the result is musically good, whether the vocal is intelligible and whether the output matches the requested key by ear. That needs the owner's listening review (takes are kept in the scratch run folders, not in the repo).

## Tests

- **Unit and window tests:** `tests/test_music_contract.py`, `tests/test_music_page.py` (real window, fake engine), `tests/test_music_studio.py`, plus `tests/test_resource_limits.py` and `tests/test_worker_kill_tree.py` merged in from #135 and #134. Full suite on 2026-11-02: **583 tests, OK** (below-normal priority).
- **Real window, real ACE-Step** (off-screen window, disposable profile, below-normal priority, 2026-11-02), **20 of 20 checks passed in the light theme**: page opens; an empty prompt is explained; the cost warning appears before the job (2 takes of 30 s: about 4 minutes, 10 GB of 15.4 GB); the model starts off the UI thread (52 s); the longest event-loop gap while composing was 0.52 s; two takes listed; take A plays; Switch A/B continues take B from the same moment (1536 to 2048 ms); keep makes a verified music asset with the pinned revision at −16 LUFS; Keep and add to Studio places it as a sound clip; the project saves, reopens with clip gain and fades, and exports; Cancel returns in 0.1 s, ends the worker tree, frees GPU memory and leaves no partial files; Generate works again afterwards (65 s including the restart); closing the app leaves no worker.
- **Dark theme run:** 17 of 20 passed. Switch A/B restarted take B from 0 (a real bug: Qt ignores a seek before the new file has loaded), fixed with a regression test that fails without the fix. The two worker-count failures were the harness counting its own PowerShell query; no worker was running, and GPU memory was back at baseline.
- **Not done:** listening (the owner's review) and playing audio aloud. The window ran off-screen with volume at 0.

## Outstanding

- **Owner listening review:** quality, vocal intelligibility and whether takes follow the prompt and requested key by ear. Without it this slice is a **CONDITIONAL GO**: functionally complete and measured, musically unreviewed.
- **The same seed doesn't give the same plan across runs:** two real-window runs with seed 2026 planned 77 BPM A minor and 91 BPM D major. The renderer is seeded, but the 1.7B planner samples. Turning off **Plan first** or setting tempo and key pins them; making the planner deterministic is follow-up work.
- **First start after a reboot** is several minutes; later starts about 50 s. The estimate assumes 3 minutes.
- **The estimate shows on every Generate:** 10 GB is more than 60% of the default GPU cap, so each job counts as heavy. Users can switch warnings off in Settings › Performance.
- **Later engines:** HeartMuLa (vocals) and DiffRhythm as comparators; Stable Audio 3 only if the owner reopens it.
- **Agent adapter (#130)** calls `MusicService` and doesn't exist yet.
