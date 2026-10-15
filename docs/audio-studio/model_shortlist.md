# Phase 0 (#53): model shortlist for a local benchmark

> **Historical research snapshot, 2026-10-13.** Counts, source comparisons, package inventories, model licensing, and recommendations describe the audited revision, **not the current Sonic Rift `main`**. Subsequent implementation includes independent provider #77, core refactors #75/#78/#85/#86, and adopted MOSS soundscape implementation. Review current `docs/upstream-provenance-audit.md`, `THIRD_PARTY_NOTICES.md`, and release issue #61 before treating any result as a live production assertion. No new tests or downloads were performed during this archival integration. **Stable Audio 3 was evaluated but not retained as the selected shipping sound model; MOSS and procedural generation were adopted later.**

**Nothing has been downloaded.** Everything below is proposed and needs the owner's approval before any download.
Citations are in `model_matrix.md`. Sizes come from HF file listings (hub API) on 2026-10-13.

## Licensing gate (read first)

1. **Stability models (SA3, SAO).** Commercial use of outputs is allowed under the Stability AI Community License **only while the owner or entity is under US$1M annual revenue (from any source)**. The owner must also:
   - **register** with Stability for commercial use, and
   - **prominently display "Powered by Stability AI"** wherever the materials are made available.

   Outputs are owned by the user (Sec. IV(c)(iii)).
   - **Decision for the owner:** Does the website/business qualify, and is the attribution acceptable? It is unclear whether the attribution duty applies when you only publish *outputs* rather than distribute the model. The clause covers distributing or making available "Stability AI Materials" or derivative works. **Get a legal read or ask Stability.**
   - The license file for SA3 itself could not be read (gated). I am assuming it matches SAO's, but this is **unverified**.
2. **Apache/MIT-tagged models** (MOSS-SoundEffect v2, EzAudio, Make-An-Audio 2) are permissive on paper. However:
   - Their **training-data provenance is undisclosed** (MOSS, MAA2), or
   - they were trained on YouTube-derived AudioSet/VGGSound/AudioCaps (EzAudio).

   A permissive weights license does not clear the training data.

## Ranked shortlist (max 3)

### 1. `stabilityai/stable-audio-3-small-sfx`: top recommendation
- **Download:** ≈ **3.5 GB**: `model.safetensors` 2.27 GB + `t5gemma-b-b-ul2/` 1.18 GB + tokenizer files ≈ 0.04 GB. The repo is gated, so the owner must accept terms on HF.
- **Why it ranks first:**
  - It is purpose-built for SFX and ambience, and new (May 2026).
  - Its training data is licensed (AudioSparx) plus CC Freesound, which is the cleanest provenance in the field.
  - **120 s stereo 44.1 kHz per call** covers a 60 s loop plus margin in one shot.
  - **Inpainting/continuation** can heal a loop seam. One way: rotate the clip by half its length, then inpaint the middle region. This is my proposed technique and is untested.
  - It is **designed to run on CPU** (Mac CPU 1.7 s per 30 s per the repo), which is the no-GPU fallback.
  - VRAM is ~2.4 GB, so it fits alongside Chatterbox on 16 GB.
  - flash-attn is apparently not required for Small (the README says it is required "for Medium").
- **Risks:**
  - torch 2.7.1 pin vs the app's torch 2.8 → plan a **separate venv or subprocess worker**.
  - Blackwell sm_120 needs a cu128 build (the README says this is installable).
  - No Windows statement from Stability.
  - Quality on long ambience is unverified by ear.

### 2. `stabilityai/stable-audio-3-medium`: quality ceiling, Windows risk
- **Download:** ≈ **10.4 GB** (`model.safetensors` 9.22 GB + T5Gemma ≈ 1.22 GB). Gated.
- **Why:** Same license and data as #1. It is 1.4B, goes up to 380 s, and handles music beds as well as SFX. Peak VRAM is ~5–6.5 GB (H200 measurement).
- **Risk:** **flash-attn is required.** Windows plus sm_120 plus torch 2.7.1 wheels are a known pain point.
  - Benchmark it only if a matching prebuilt Windows wheel exists. Otherwise, defer it or run it under WSL2.
  - It has no CPU fallback.

### 3. `OpenMOSS-Team/MOSS-SoundEffect-v2.0`: permissive-license alternative
- **Download:** ≈ **11.2 GB**:
  - `text_encoder/` 4.06 GB (Qwen3-1.7B)
  - `transformer/` 5.66 GB
  - `vae/vae_128d_48k.pth` 1.49 GB
  - tokenizer ≈ 0.02 GB
- **Why:** It is **Apache-2.0** with no revenue cap or attribution clause. It is 48 kHz, up to 30 s per call, claims environmental/urban SFX coverage, and is actively maintained (2026-05).
  - It is the hedge if the Stability license is unacceptable (over $1M revenue, or the attribution is unwanted).
- **Risks:**
  - **Training data undisclosed.**
  - 30 s max means a 60 s loop needs a crossfade or stitching (no inpainting is documented).
  - torch 2.9 / Py 3.12 / Triton / torch.compile on Windows means a separate venv. Set `TORCHDYNAMO_DISABLE=1` if Triton fails.
  - The **VAE `.pth` is a pickled full model object**, so load it only in an isolated process.
  - About 3x the download of #1.

**Alternate, not shortlisted:** `stabilityai/stable-audio-open-1.0` (model.safetensors 4.85 GB, 47 s). It has the same license as SA3 and is superseded by it. It is useful only as a lower-risk Windows path via `diffusers` StableAudioPipeline if the SA3 install fails.

## Benchmark plan sketch (if approved)
- **Prompts:** ocean waves, steady rain, distant thunderstorm, forest birds, UI chime / success / error.
- **Lengths:** 10 s and 60 s (SA3), 30 s (MOSS).
- **Measure:**
  - wall time on GPU and on CPU (SA3-small)
  - peak VRAM
  - loop-seam quality: inpaint-heal vs crossfade
  - subjective blind rating against the DSP baseline
- **Isolation:** Write outputs to scratch only, and run in a separate venv per model.

## EXCLUDE (and why)

| Model | Reason |
|---|---|
| AudioGen, MusicGen (all), MAGNeT, JASCO (Meta AudioCraft) | Weights **CC-BY-NC 4.0**, so no commercial use |
| AudioLDM, AudioLDM 2 | Weights **CC-BY-NC-SA 4.0** |
| Tango, Tango 2 | Weights **CC-BY-NC-SA 4.0** |
| TangoFlux | "Non-commercial research use only"; WavCaps academic-only |
| MMAudio | Weights **CC-BY-NC 4.0**; Ubuntu-only testing |
| AudioX (all variants) | **CC-BY-NC** code+models; outputs watermarked |
| PrismAudio / ThinkSound | Research/education only despite the MIT tag; video-to-audio focus |
| YuE2 (music) | CC-BY-NC |
| HunyuanVideo-Foley | Requires video input; Tencent community license not reviewed |
| Stable Audio Open Small | Same license as SA3, but 11 s max; SA3 Small supersedes it |
| EzAudio | MIT weights, **but** trained on YouTube-derived AudioSet/VGGSound/AudioCaps with GPT-4o-mini captions; 24 kHz output. Provenance too weak for commercial assets |
| Make-An-Audio 2 | MIT tag, but data withheld "for copyright issues"; stale (2024) |

## Unverified points (explicit)
- The SA3 `LICENSE.md` text was not readable (gated). Equivalence to the Community License Agreement is assumed from the same file size (11,852 B) and the card text.
- Whether "Powered by Stability AI" attribution is required when only **outputs** are published on a website is unclear.
- SA3 sample rate per variant: the README states SAME is 44.1 kHz stereo, but the per-model config was not read (gated).
- SA3 Small runs without flash-attn: inferred from "required for Medium" wording.
- None of the VRAM or speed figures were measured on Windows or RTX hardware. The SA3 figures are H200/Mac; MOSS has none.
- MOSS-SoundEffect v2: channels (mono vs stereo), VRAM and training data are unknown.
- Native seamless-loop generation: **no model documents it**. The loop approach (inpaint the seam, or crossfade) is my proposal.
- Music-bed models (ACE-Step 1.5 MIT, HeartMuLa Apache-2.0, Magenta RT 2 CC-BY-4.0): training-data provenance not reviewed.
- Third-party ports (sa3.cpp GGUF, MOSS GGUF/MLX) are unaudited.

## Zero-model baseline
Procedural DSP covers several needs: noise-based rain, surf and wind beds, plus synthesized UI chimes. It is license-free, loops perfectly by construction, runs on CPU, and should ship regardless as the fallback and as the comparison baseline.
