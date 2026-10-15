# License / SPDX inventory: Python environments (issue #55)

> **Historical license inventory (October 13, 2026).** This documents then-installed environments and cached model metadata, NOT the shipped dependency inventory. Reconcile the actual packaged builds and current source/weights terms before release. Some originally flagged VoxCPM optional dependencies were subsequently removed. See [current notices](../../THIRD_PARTY_NOTICES.md) and [release gate #61](https://github.com/Knapp-Kevin/sonic-rift/issues/61).

Read-only inventory taken 2026-10-13 from the local checkout
`C:\LocalAI\Voice\Chatterbox\Chatterbox-TTS-UI-main\Chatterbox-TTS-UI-main`. Nothing was installed or modified.
This is an engineering inventory, **not legal advice**. Items marked **REVIEW** need owner or legal review.

Method: `inventory.py` was run with each venv's own interpreter (`python -I`) via `importlib.metadata`.
`normalize.py` maps `License-Expression`, then the `License` field, then trove classifiers to SPDX, plus a short
list of manual overrides that were checked against the installed LICENSE files (PySide6/shiboken6, kaldiio,
llvmlite, audioread 3.0.1, torchcodec, espeakng-loader, num2words). Per-package detail is in `licenses_full_<venv>.csv`.

Packages whose metadata says only "BSD" with no variant (Jinja2, numba, sympy, torchaudio, torchvision, networkx and
others) are recorded as `BSD (variant unspecified)` and counted as permissive.

## Counts by license family

| Environment | Total | Permissive (MIT/BSD/Apache/ISC/PSF…) | Weak copyleft (LGPL/MPL) | Strong copyleft (GPL/AGPL) | Non-commercial / restricted | Unknown |
|---|---|---|---|---|---|---|
| main app `.venv` | 138 | 128 | 8 | 2 | 0 | 0 |
| `engines/kokoro/.venv` | 100 | 95 | 3 | 2 | 0 | 0 |
| `engines/omnivoice/.venv` | 89 | 85 | 4 | 0 | 0 | 0 |
| `engines/qwen/.venv` | 89 | 85 | 4 | 0 | 0 | 0 |
| `engines/vibevoice/.venv` | 63 | 60 | 3 | 0 | 0 | 0 |
| `engines/voxcpm/.venv` | 146 | 141 | 4 | 0 | **1** | 0 |

No `engines/rvc` environment exists. RVC is only a feasibility harness (`this_voice_thing/engines/rvc_feasibility.py`,
upstream RVC-Project WebUI, MIT, assets from `lj1995/VoiceConversionWebUI`, MIT on the Hub). It is not installed.

Five packages had no usable license metadata and were resolved from their shipped LICENSE files. After that, nothing
is left as UNKNOWN. These were the five:
`audioread 3.0.1` (main venv) is MIT according to its LICENSE file. `llvmlite 0.50.0` is BSD-2-Clause, and its
LICENSE.thirdparty covers bundled LLVM (Apache-2.0 WITH LLVM-exception). `torchcodec 0.17.0` is BSD-3-Clause and ships
third-party notices. `espeakng-loader` and `kaldiio` are covered in the list below.

## Every non-permissive package

| Package | Version | Venv(s) | SPDX (normalized) | Pulled in by | Why it matters |
|---|---|---|---|---|---|
| **kaldiio** | 2.18.1 | voxcpm | `LicenseRef-NTT-Software-Evaluation-License` | funasr / modelscope (VoxCPM deps) | **Top risk. REVIEW.** The installed wheel's LICENSE is an NTT "Software License Agreement for Evaluation": internal evaluation use only, no distribution, no sublicensing, Japanese law and Tokyo arbitration. Older kaldiio releases were MIT. Never bundle this. Check whether VoxCPM really needs funasr/kaldiio at runtime, or pin a kaldiio version still under MIT. Even installing it at the user's setup time puts each end user under evaluation-only terms. |
| **espeakng-loader** | 0.2.4 | kokoro | Loader declares no license. The bundled `espeak-ng.dll` and `espeak-ng-data` are GPL-3.0-or-later (eSpeak NG) | misaki[en] | The package itself ships no LICENSE file in its dist-info, so its metadata is effectively UNKNOWN. It **bundles a compiled GPL-3.0 espeak-ng.dll**. If this goes into an installer, that is GPL distribution: corresponding source and the GPL text must be supplied, and whether the app counts as a combined work is a **REVIEW** item. Installing it at user setup time is lower risk. |
| **phonemizer-fork** | 3.3.2 | kokoro | GPL-3.0-or-later | misaki[en] | GPL Python library imported in-process by the Kokoro worker. The worker is a separate process from the GPL-free main app, which helps separation, but bundling it is GPL distribution. **REVIEW** if shipped. |
| **praat-parselmouth** | 0.4.7 | main | GPL-3.0-or-later | resemble-perth (Perth watermarker) | **REVIEW.** This is a GPL package in the *main app process*, loaded alongside PySide6 and the app code. It is not needed for source distribution. If the main venv is ever frozen or bundled (for example with PyInstaller), the result arguably becomes a GPL combined work. Find out whether Perth's implicit watermarker actually imports parselmouth, and whether it can be made optional. |
| **pykakasi** | 2.3.0 | main | GPL-3.0-or-later | chatterbox-tts (Japanese text in multilingual) | Same issue: GPL in the main app process. Bundling has the same consequences as parselmouth. **REVIEW** whether it can be lazily or optionally installed. |
| PySide6 / PySide6_Essentials / PySide6_Addons / shiboken6 | 6.9.0 | main | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only (the app uses the LGPL option) | direct dependency | LGPL-3.0 with dynamic linking is fine when installed with pip. If an installer is shipped: keep Qt/PySide6 as replaceable shared libraries (no static linking, no single-file freezing that blocks relinking), include the LGPL-3.0 and GPL-3.0 texts and the Qt notices, give a source offer or link for the exact Qt/PySide versions, and do not prohibit reverse engineering in the EULA. The Addons wheel includes Qt modules that are GPL-only in some Qt builds (for example parts of Qt Charts, Data Visualization, and WebEngine with proprietary codecs), so **REVIEW** which Addons modules are actually imported. |
| soxr | 0.5.0.post1 (main); 1.1.0 (engines) | all 6 | LGPL-2.1-or-later | librosa, datasets | It bundles libsoxr as a compiled extension. Installing with pip is fine. In a bundle, ship the LGPL text and keep the library replaceable. |
| num2words | 0.5.14 | kokoro | LGPL-2.1-or-later (metadata says only "LGPL") | misaki | Pure-Python LGPL. Installing with pip is fine. Bundling requires the LGPL notice, and users must be able to swap the module (unmodified .py files satisfy this). |
| certifi | 2025.4.26 / 2026.7.22 | all 6 | MPL-2.0 | requests | File-level copyleft. Unmodified redistribution only needs a notice. Low risk. |
| tqdm | 4.67.1 / 4.70.1 | all 6 | MPL-2.0 AND MIT | many | Same as certifi. Low risk. |
| orjson | 3.11.9 / 3.12.0 | main, omnivoice, qwen, voxcpm | MPL-2.0 AND (Apache-2.0 OR MIT) | gradio, rdflib | Same as certifi. Low risk. |

### Bundled native code that is not visible in package metadata (relevant only if an installer is built)

- **PyTorch cu128 wheels** (`torch/lib/*.dll`, present in every venv) ship NVIDIA CUDA, cuBLAS, cuDNN and cuFFT
  redistributables under the NVIDIA CUDA/cuDNN EULAs, not BSD. Redistributing them is allowed with conditions, and
  the EULA terms must be carried along. **REVIEW** if torch is bundled. Today torch is installed at setup time.
- **soundfile** (BSD-3-Clause) bundles `libsndfile_x64.dll` (LGPL-2.1-or-later). It needs the LGPL notice and a
  replaceable DLL if bundled.
- **torchcodec** bundles third-party notices (libavif and others), and **llvmlite** bundles LLVM
  (Apache-2.0 WITH LLVM-exception).
- **FFmpeg / Rubber Band**: the README credits them, and `pydub`, `pyrubberband` and `sox` call external binaries.
  The repo ships no binaries (no .exe or .dll found outside the venvs). An FFmpeg build may be LGPL or GPL depending on
  how it was configured, and the Rubber Band CLI is GPL-2.0-or-later (or commercial). Any future installer that ships
  these must check which build it includes. **REVIEW**.
- **spaCy models**: `en_core_web_sm 3.8.0` (kokoro venv) declares MIT. That is permissive, but it was trained on
  OntoNotes 5. spaCy publishes its small models under MIT, so no issue is expected.
- **misaki 0.9.4 / kokoro 0.9.4** are Apache-2.0. Their own G2P is permissive. The GPL exposure comes only from the
  espeak-ng fallback (`phonemizer-fork` and `espeakng-loader`).

## Distribution channels

| Channel | What is distributed | License exposure |
|---|---|---|
| **1. Source distributed in the repo** | App Python code, `assets/` (project branding and own SVG icons), `models.json`, scripts, docs, and the repo-root `LICENSE` (MIT, upstream Resemble AI / AcTePuKc notice). No third-party source is vendored, and there are no binaries outside the venvs. | MIT only. The upstream copyright notice and permission text must be kept. **Check:** `reference_recordings/`, `soundboard/`, `voice_library/` and `chatterbox_outputs/` exist in this working copy and hold user audio. Make sure they are git-ignored and never published. This folder is not a git checkout, so tracking could not be verified. |
| **2. Installed at user setup time** (`setup_env.*`, `requirements.lock.txt`, per-engine `PACKAGES` installed by `engine_worker.install_env`) | Every package listed above, plus model weights downloaded from the Hugging Face Hub at first use. | The end user receives each package directly from PyPI or the Hub under that package's own license. GPL/LGPL obligations generally attach to the distributor (PyPI or the author), not to this project. The exception is **kaldiio's evaluation-only terms, which bind the end user**. Model licenses (see `licenses_models.md`) also bind the end user. The app should keep showing license badges and require confirmation for non-commercial or research-only models. |
| **3. Would be bundled if we ship an installer** (for example PyInstaller or Briefcase of the main venv, with engine venvs pre-built) | Main venv: PySide6/Qt (LGPL), soxr/libsoxr and libsndfile (LGPL), **praat-parselmouth and pykakasi (GPL-3.0)**, torch plus the NVIDIA DLLs (EULA), chatterbox-tts and resemble-perth (MIT). Engine venvs, if pre-built: **espeak-ng.dll and phonemizer-fork (GPL-3.0)**, **kaldiio (evaluation-only, not redistributable)**, num2words (LGPL). | This is where real obligations apply. Required: a THIRD-PARTY-NOTICES file, the LGPL relinking ability, source offers for GPL and LGPL components, the NVIDIA EULA terms, and removing kaldiio or replacing it with an MIT version. Recommended: keep engine venvs installed at setup time rather than bundled, and make parselmouth and pykakasi optional in the main venv. **REVIEW before any installer work.** |

## Attribution inventory: what a renamed product must carry

1. **Repo-root `LICENSE` (MIT)**: keep it as is. Its copyright line reads
   `Copyright (c) 2025 Resemble AI (https://www.resemble.ai) - AcTePuKc Developments Ltd.Co.Uk.Gov.Som.uk`.
   **REVIEW:** this line is unusual. It appears to combine the Resemble AI notice from `resemble-ai/chatterbox` with the
   AcTePuKc fork notice. When renaming, do not delete or rewrite it. Add the project owner's own copyright line for new
   work *alongside* it, either in the same file or as `LICENSE` plus `NOTICE`, and keep the original notice verbatim.
   The README "Acknowledgements" section already credits AcTePuKc, lowkeytea and Resemble AI. Keep that text through
   the rename.
2. **Engine code credits** (already in the README Acknowledgements, so keep them): Resemble AI Chatterbox (MIT),
   resemble-perth watermarker (MIT, Resemble AI), Qwen3-TTS / qwen-tts (Apache-2.0, Alibaba Qwen), VoxCPM (Apache-2.0,
   OpenBMB), VibeVoice (MIT code, Microsoft, research-use model card), OmniVoice (Apache-2.0 code, k2-fsa/Xiaomi,
   **CC-BY-NC-4.0 weights**), Kokoro and misaki (Apache-2.0, hexgrad), Whisper large-v3-turbo (MIT, OpenAI).
   Apache-2.0 components need their LICENSE text and any upstream NOTICE file *only when redistributed*. Today they are
   not redistributed. They are installed at setup time.
3. **Model-weight attributions**: see `licenses_models.md`. Required if outputs or weights are redistributed: CC-BY-NC
   attribution for OmniVoice, and the Kokoro card's CC-BY training-data credits if the weights are ever re-hosted.
4. **If an installer is built**, also add a `THIRD-PARTY-NOTICES` file generated from `licenses_full_main.csv` (and from
   the engine CSVs if engines are pre-bundled). It should include the LGPL-3.0, GPL-3.0, LGPL-2.1 and MPL-2.0 texts, Qt
   attributions, the NVIDIA CUDA/cuDNN EULA notices, eSpeak NG (GPL-3.0) if Kokoro is bundled, and the libsndfile and
   libsoxr notices.
5. **The name and branding** must not suggest endorsement by Resemble AI, Microsoft, Alibaba or others. Apache-2.0
   section 6 grants no trademark rights. Engine names may only be used descriptively.

## Items flagged for owner or legal review

1. kaldiio 2.18.1 uses the NTT evaluation-only license (voxcpm venv). Is it needed? Can it be pinned to an MIT release
   or dropped?
2. GPL-3.0 packages in the main app process: praat-parselmouth (via resemble-perth) and pykakasi (via chatterbox-tts).
   This matters if the main app is ever bundled.
3. The espeak-ng.dll (GPL-3.0) and phonemizer-fork (GPL-3.0) in the Kokoro engine.
4. The PySide6 LGPL relinking obligations and the Qt Addons module licensing, if bundled.
5. NVIDIA CUDA DLLs inside the torch wheels, if bundled.
6. The unusual copyright line in the repo-root LICENSE, and how to add the new owner's notice during the rename.
7. Model weights: OmniVoice (CC-BY-NC-4.0) and VibeVoice (MIT, but the card says research-only and not recommended for
   commercial use). See `licenses_models.md`.
