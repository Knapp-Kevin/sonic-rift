# Phase 0 (#53): local text-to-audio / SFX / ambience model matrix

> **Historical research snapshot, 2026-10-13.** Counts, source comparisons, package inventories, model licensing, and recommendations describe the audited revision, **not the current Sonic Rift `main`**. Subsequent implementation includes independent provider #77, core refactors #75/#78/#85/#86, and adopted MOSS soundscape implementation. Review current `docs/upstream-provenance-audit.md`, `THIRD_PARTY_NOTICES.md`, and release issue #61 before treating any result as a live production assertion. No new tests or downloads were performed during this archival integration. **Stable Audio 3 was evaluated but not retained as the selected shipping sound model; MOSS and procedural generation were adopted later.**

Researched 2026-10-13. I only read web pages, model cards, repos and papers. Nothing was downloaded or installed.
Target: RTX 5070 Ti 16 GB (Blackwell, sm_120, needs CUDA 12.8+ builds), Win 11, Python 3.11, torch 2.8 cu128. A no-GPU fallback is also required.
Use: ambience loops (ocean, rain, thunder, forest; 60 s seamless), UI chimes and SFX, maybe music beds. **Generated assets will be used commercially on a website.**

Legend:
- **Commercial?** means commercial use of the weights and outputs: Y = yes, C = conditional, N = no.
- **Windows risk** is my assessment from the stated deps. It is not tested. L = low, M = medium, H = high.
- **Loop support** means a documented inpainting or continuation feature that could be used to heal a loop seam. No model documents native seamless-loop generation.

## Comparison table

| Model | Weights license | Commercial? | Max length / call | SR / ch | VRAM (documented) | Windows risk | Loop support | Ambience fit |
|---|---|---|---|---|---|---|---|---|
| **Stable Audio 3 Small-SFX** (2026-05) | Stability AI Community License (+ Gemma ToU for T5Gemma encoder) | **C**: < US$1M annual revenue, registration, "Powered by Stability AI" | 120 s | 44.1 kHz stereo | 1.7–2.4 GB peak (H200); designed for CPU | L–M | **Yes**: inpainting (multi-region) and continuation | High (SFX-tuned, licensed+CC data); unverified by ear |
| **Stable Audio 3 Medium** (2026-05) | Same as above | **C** (same) | 380 s | 44.1 kHz stereo | 5.1–6.5 GB peak (H200) | **H** (flash-attn required; torch 2.7.1 pin) | **Yes** (same) | High (general music+SFX); unverified |
| Stable Audio Open 1.0 (2024-06) | Stability AI Community License | **C** (same) | 47 s | 44.1 kHz stereo | not documented (~1.2B params) | M | audio-to-audio init only; no documented inpaint ckpt | Good for field recordings and SFX per card |
| Stable Audio Open Small (2025-05) | Stability AI Community License | **C** (same) | 11 s | 44.1 kHz stereo | not documented (0.5B; Arm CPU path) | M | none documented | SFX/short; too short for 60 s beds |
| **MOSS-SoundEffect v2.0** (2026-05) | Apache-2.0 | **Y** (license); training data undisclosed | 30 s | 48 kHz; channels not stated | not documented (1.3–1.4B DiT + Qwen3-1.7B encoder) | M–H (torch 2.9 pin, Py 3.12, Triton/torch.compile) | none documented | Claims natural/urban environments; unverified |
| EzAudio (2024–25) | MIT (HF tag) | Y by license, **but** see provenance | not stated (trained on 10 s clips, unverified) | 24 kHz; ch not stated | not documented | M | **Yes**: inpainting/editing (`mask_start`, `mask_length`) | SFX-focused; 24 kHz is low for ambience |
| Make-An-Audio 2 (2023–24) | MIT (HF tag) | Y by license, data undisclosed ("copyright issues") | not stated (10 s examples) | not stated (likely 16 kHz, unverified) | not documented | M | none documented | Older; superseded |
| AudioGen medium (AudioCraft) | CC-BY-NC 4.0 | **N** | ~5–10 s typical (no max stated) | 16 kHz mono | ≥16 GB stated for medium | M (xformers, torch 2.1 era) | Yes (continuation) | Fair; low SR |
| MusicGen (all sizes) / MAGNeT / JASCO | CC-BY-NC 4.0 | **N** | ~30 s window + extension | 32 kHz mono/stereo | ≥16 GB for medium | M | Yes (continuation) | Music only |
| AudioLDM / AudioLDM 2 | CC-BY-NC-SA 4.0 | **N** | variable (5–10 s typical) | 16 kHz mono | not documented | L (diffusers) | (editing via DDPM inversion in third-party work) | Fair; dated |
| Tango / Tango 2 | CC-BY-NC-SA 4.0 | **N** | ~10 s | 16 kHz | not documented | M | none | Fair |
| TangoFlux | "non-commercial research use only" + Stability Community + WavCaps (academic) | **N** | 30 s | 44.1 kHz stereo | not documented; ~3.7 s/30 s on A40 | M | none documented | Good; but blocked |
| MMAudio | CC-BY-NC 4.0 (code MIT) | **N** | default 8 s | 44 kHz (large_44k_v2) | ~6 GB (16-bit) | M ("only tested on Ubuntu") | none | Good SFX; blocked |
| AudioX (+MAF variants) | CC-BY-NC (code too); outputs watermarked | **N** | 10 s examples | stereo (inferred) | not documented | M | (audio inpainting in paper; unverified) | Blocked |
| PrismAudio / ThinkSound | MIT tag, but card says research/education only, commercial needs authorization | **N** (without written authorization) | n/a | n/a | n/a | M | n/a | Video-to-audio focus |
| HunyuanVideo-Foley | tencent-hunyuan-community | unverified (Tencent community licenses typically carry territory/MAU terms; NOT checked) | not stated | 48 kHz | offload option | H | none | Needs video input; poor fit |
| Procedural / DSP (baseline) | your own code | **Y** | unlimited | any | none (CPU) | L | **native** (loop by construction) | Rain/wind/surf/noise beds are very plausible; thunder, birds and forest detail are weaker |

## Per-model notes (with citations)

### Stable Audio 3: Small-SFX, Small-Music, Medium (Stability AI, May 2026). This is the newest and strongest-fit family.
- **Weights license:** Stability AI Community License. The card says "For commercial use, please refer to https://stability.ai/license". The models are gated on HF (contact-info share). https://huggingface.co/stabilityai/stable-audio-3-small-sfx, https://huggingface.co/stabilityai/stable-audio-3-medium
- **Stability license page:** The Community License covers "Stable Audio 3.0". It is free for orgs with < US$1M annual revenue "regardless of the source of that revenue". Above that, an Enterprise license is needed. https://stability.ai/license
- **Community License agreement terms (Last Updated July 5, 2024):** Users must register for commercial use (Sec. III). Rights end above US$1M revenue (Sec. III). Distributors must "prominently display 'Powered by Stability AI'" (Sec. IV(a)). The AUP is incorporated (Sec. IV(b)). **"You own any outputs generated from the Models"** (Sec. IV(c)(iii)). https://stability.ai/community-license-agreement
  - **Caveat:** I could not read the SA3-specific `LICENSE.md` on HF because the repo is gated (HTTP 401). I am assuming it matches the agreement above, because the file sizes are identical (11,852 bytes, same as SAO's LICENSE.md). This is **unverified**.
- **Second license (Gemma):** The text encoder is redistributed under the Gemma Terms of Use. Sec. 3.2 incorporates the Prohibited Use Policy, and Sec. 3.1 requires passing these restrictions on when you redistribute. Sec. 3.3 says "Google claims no rights in Outputs". https://ai.google.dev/gemma/terms. This matters only if the app *redistributes* the encoder; local use plus distributing audio outputs is fine.
- **Code license:** MIT (`Copyright (c) 2026 Stability AI`). https://raw.githubusercontent.com/Stability-AI/stable-audio-3/main/LICENSE. The README also points at the Community License for the models.
- **Training data:** About 1.28M recordings: 806,284 licensed from AudioSparx plus 472,618 Freesound (CC0 / CC-BY / CC-Sampling+). Music was screened with PANNs and a content-detection company. An attribution list is published at https://info.stability.ai/attributions (HF card). The paper says it was "trained on licensed and Creative Commons data". https://arxiv.org/abs/2605.17991
  - **Provenance caveat:** CC-BY sources can carry attribution expectations. Stability publishes the attribution list; whether downstream output users owe attribution is not addressed. Treat this as low risk but note it.
- **Specs** (from the repo README model table, https://github.com/Stability-AI/stable-audio-3):

  | Variant | Params | Max length | Hardware |
  |---|---|---|---|
  | Small-SFX | 433M | 120 s | CPU-capable |
  | Small-Music | 433M | 120 s | CPU-capable |
  | Medium | 1.4B | 380 s | GPU (CUDA) |
  | Large | 2.7B | n/a | API-only, not released |

  - Audio: SAME autoencoder, stereo, 44.1 kHz.
  - HF param counts differ (Small-SFX 567.6M, Medium "~2B"). The difference is likely encoder/AE inclusion; **unverified**.
- **VRAM (H200, unchunked decode):**
  - Small: 1.69 GB (5 s), 1.89 GB (30 s), 2.40 GB (120 s).
  - Medium: 5.07 GB (5 s) to 6.52 GB (380 s).
- **Speed:**
  - Small on H200: ~0.45 s per 30–120 s clip. On Mac CPU: 1.72 s per 30 s and 5.92 s per 120 s.
  - Medium on H200: 0.65 s per 30 s.
  - Source: the repo README. There are **no Windows or RTX numbers**.
- **Features:** Text-to-audio, audio-to-audio, and inpainting with **multiple non-contiguous regions**. Continuation works by setting the mask start to the source length. LoRA fine-tuning is supported. Loops are **not** mentioned. (repo README; paper sec. 1)
- **Deps:**
  - torch **2.7.1** and torchaudio 2.7.1 are pinned in pyproject. The default is cu126; cu128 is installable manually.
  - **flash-attn is required for Medium.** It is not in pyproject, so use `uv sync --inexact`.
  - Python is likely 3.10 (the flash-attn wheel example is cp310).
  - The repo has no Windows statement. A TFLite runtime has a PowerShell bootstrap that still needs Git Bash/WSL. (repo README)
  - **Implication:** The app's torch 2.8/Py3.11 env does not match the pin, so a separate venv or subprocess is likely needed. Medium on Windows plus Blackwell sm_120 depends on a matching flash-attn Windows wheel, which is **high risk**.
- **No-GPU fallback:** Small is explicitly designed for CPU. A third-party GGUF / sa3.cpp port exists (https://huggingface.co/thepatch/stable-audio-3-small-sfx-GGUF), but it is unaudited.
- **Download size** (HF file listing via hub API; .png excluded):
  - Small-SFX: model.safetensors 2.27 GB + t5gemma encoder 1.18 GB + tokenizer ~0.04 GB ≈ **3.5 GB**.
  - Medium: 9.22 GB + 1.22 GB ≈ **10.4 GB**.
- **Maintenance:** Small-SFX was last updated on HF on 2026-10-06. The repo has 307 commits but no tagged releases.

### Stable Audio Open 1.0 / Open Small (Stability AI, 2024 / 2025)
- **License:** Stability AI Community License (same terms as above). https://huggingface.co/stabilityai/stable-audio-open-1.0, https://huggingface.co/stabilityai/stable-audio-open-small
- **Data:** 486,492 recordings, all CC0/CC-BY/CC-Sampling+ (472,618 Freesound + 13,874 FMA). Attribution CSVs ship in the repo. (cards)
- **1.0:**
  - Up to 47 s, stereo 44.1 kHz, ~1.2B params.
  - The card says it is "better at sound effects and field recordings than at music", and it cannot do realistic vocals.
  - Download: model.safetensors 4.85 GB. Fetch only that file plus config; the repo also has a duplicate 4.85 GB .ckpt and diffusers folders. T5-base is fetched separately.
- **Small:**
  - Up to 11 s, stereo 44.1 kHz, 0.5B params, 8-step "pingpong" sampler.
  - The card has an Arm-CPU LiteRT guide.
  - Download: 1.68 GB.
- **Code:** stable-audio-tools is MIT. It needs PyTorch ≥2.5; flash-attn is optional; `diffusion_cond_inpaint` model type exists but no SAO inpaint checkpoint is documented. https://github.com/Stability-AI/stable-audio-tools
- **Status:** Superseded by SA3, which has the same license, longer clips and inpainting. SAO 1.0 is also usable via `diffusers` (StableAudioPipeline), which is likely the easiest Windows path. That diffusers path is from my knowledge; I did not verify it this session.

### MOSS-SoundEffect v2.0 (OpenMOSS / Fudan-affiliated team, released 2026-05-26)
- **License:** Apache-2.0 on the HF card and family-wide ("Models in MOSS-TTS Family are licensed under the Apache License 2.0"). https://huggingface.co/OpenMOSS-Team/MOSS-SoundEffect-v2.0, https://github.com/OpenMOSS/MOSS-TTS
  - It is the **only actively maintained 2026 SFX model with a fully permissive license**.
- **Training data: NOT disclosed** anywhere I could find (card, family README, v2 README). This is a provenance risk: the permissive license does not tell you whether the training audio was licensed.
- **Specs:**
  - DiT + flow matching, DAC VAE `vae_128d_48k.pth` (48 kHz), Qwen3-1.7B text encoder.
  - Up to **30 s** per call, default 10 s. 100 steps, CFG 4.0.
  - Channels not stated.
  - Claims "natural environments, urban environments".
- **Deps:**
  - Python 3.12, torch 2.9 (family README pins 2.9.1+cu128), transformers 4.57, numpy 1.26, Triton.
  - The DiT is wrapped in `torch.compile` + Triton CUDA Graph (fallback `TORCHDYNAMO_DISABLE=1`).
  - No Windows statement. https://github.com/OpenMOSS/MOSS-TTS/blob/main/moss_soundeffect_v2/README.md
  - Triton on native Windows typically needs the third-party `triton-windows` fork. This is my inference, **unverified**.
- **Security note:** The VAE ships as `.pth` with config note "Full model object, not a pure state_dict". That means a pickle load with `weights_only=False`, which executes arbitrary code from the file. Load only in an isolated process, or convert it once in a sandbox. (`vae/config.json` on HF)
- **Download size** (HF listing): text encoder 4.06 GB + transformer 5.66 GB + VAE 1.49 GB + tokenizer ~0.02 GB ≈ **11.2 GB**.
- **Ports:** Community GGUF and MLX ports exist (e.g. https://huggingface.co/ilintar/moss-soundeffect-gguf). They are unaudited.

### EzAudio (JHU / Tencent AI Lab; Interspeech 2025)
- **License:** Code is MIT (https://github.com/haidog-yaqub/EzAudio). Weights are MIT per the HF tag (https://huggingface.co/OpenSound/EzAudio).
- **Data:** The VAE was trained on AudioSet. Pretraining used AudioSet/VGGSound with synthetic captions (Auto-ACD, Qwen-Audio, **GPT-4o-mini API**), then fine-tuning on AudioCaps. https://arxiv.org/abs/2409.10819 (sec. 2.3, 3.1)
  - AudioSet, VGGSound and AudioCaps are YouTube-derived clips with no redistribution or commercial clearance. That is a **provenance concern even though the weights are MIT**.
- **Specs:** **24 kHz** (paper sec. 3.1). L and XL DiT variants; checkpoints s3_xl 3.5 GB, s3_l 2.39 GB, VAE 0.18 GB (HF listing).
- **Features:** Inpainting and editing are supported in the README (`editing_audio(... mask_start, mask_length)`).
- **Activity:** HF model updated 2026-09-21.

### Make-An-Audio 2 (ByteDance)
- Code is MIT (https://github.com/bytedance/Make-An-Audio-2). The HF weights are tagged MIT (https://huggingface.co/ByteDance/Make-An-Audio-2).
- The README says "We can't provide the dataset download link for copyright issues". The data is undisclosed, so provenance is unclear.
- Only 3 commits; HF last updated 2024-05. **Stale.**

### Meta AudioCraft: AudioGen, MusicGen, MAGNeT, JASCO
- Code is MIT. Weights are **CC-BY-NC 4.0**. https://github.com/facebookresearch/audiocraft (README), https://huggingface.co/facebook/audiogen-medium, https://huggingface.co/facebook/musicgen-medium
- The repo requires Python 3.9 and PyTorch 2.1.0, with xformers.
- **AudioGen medium:** 1.5B params, 16 kHz EnCodec. Supports continuation. Needs ≥16 GB GPU for medium. https://github.com/facebookresearch/audiocraft/blob/main/docs/AUDIOGEN.md
- **MusicGen:** 32 kHz. Trained on 20K h licensed music (internal + ShutterStock + Pond5). Mono and stereo variants; supports continuation. https://github.com/facebookresearch/audiocraft/blob/main/docs/MUSICGEN.md
- **Blocked for commercial use** by the NC weights.

### AudioLDM / AudioLDM 2 (CVSSP)
- Weights are **CC-BY-NC-SA 4.0**. https://huggingface.co/cvssp/audioldm2, https://huggingface.co/cvssp/audioldm-l-full
- 16 kHz. HF last updated 2024-04. **Blocked.**

### Tango / Tango 2 / TangoFlux (declare-lab)
- Tango 2: **CC-BY-NC-SA 4.0** (https://huggingface.co/declare-lab/tango2-full).
- TangoFlux: The card states "The TangoFlux checkpoints are for non-commercial research use only". It is also subject to the Stability Community License and the WavCaps (academic-only) terms. https://huggingface.co/declare-lab/TangoFlux, https://github.com/declare-lab/TangoFlux
  - Specs: 30 s, 44.1 kHz stereo, ~3.7 s per 30 s on an A40. Accepted at ICLR 2026.
- **Blocked.**

### MMAudio
- Code is MIT. Weights are **CC-BY-NC 4.0**. https://github.com/hkchengrex/MMAudio, https://huggingface.co/hkchengrex/MMAudio
- Text-only mode works (omit `--video`). Default 8 s, 44k model, ~6 GB VRAM in 16-bit.
- The repo says "only tested on Ubuntu". Data: AudioSet, Freesound, VGGSound, AudioCaps, WavCaps.
- **Blocked.**

### AudioX (HKUST)
- **CC-BY-NC** for code and models. The README says the models are "watermarked and are strictly for non-commercial use only". https://github.com/ZeyueT/AudioX, https://huggingface.co/HKUSTAudio/AudioX
- **Blocked.**

### Others checked (2025–2026)
- **PrismAudio / ThinkSound** (FunAudioLLM): Tagged MIT, but the card limits use to research and education, and commercial use needs the authors' authorization. It is video-to-audio focused. https://huggingface.co/FunAudioLLM/PrismAudio
- **HunyuanVideo-Foley** (Tencent): Licensed under `tencent-hunyuan-community`. The examples require video input; 48 kHz. https://huggingface.co/tencent/HunyuanVideo-Foley. I did **not** read the license terms; Tencent community licenses often carry territory/MAU clauses, which is **unverified**.
- **Music beds (outside the core SFX scope; listed for the "possibly music" need):**
  - ACE-Step 1.5: MIT (https://huggingface.co/ACE-Step/Ace-Step1.5).
  - HeartMuLa-oss-3B: Apache-2.0 (https://huggingface.co/HeartMuLa/HeartMuLa-oss-3B).
  - Magenta RealTime 2: CC-BY-4.0, which means attribution is required (https://huggingface.co/google/magenta-realtime-2).
  - SA3 Small-Music: Stability Community License.
  - YuE2: CC-BY-NC, **blocked**.
  - For all of these, I did **not** check training-data provenance. A separate pass is needed if music beds become in-scope.
- **LTX-2.x** (Lightricks): Audio+video generation. Third-party reports describe a revenue-gated community license (under $10M, **unverified**). It is a poor fit (video model, heavy).

### Procedural / DSP baseline (zero-model)
- Filtered and modulated noise synthesis covers several of the needs: rain (pink/brown noise with random grain hits), surf (LFO-swelled noise), wind, and room tone.
- Additive or FM synthesis covers UI chimes.
- All of these loop seamlessly by construction, have no license risk, run on CPU in milliseconds, and are fully deterministic.
- Weak spots: realistic thunder, birds and forest detail.
