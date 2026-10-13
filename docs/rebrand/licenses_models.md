# Model weight licenses (issue #55)

Source: the local Hugging Face cache (`~/.cache/huggingface/hub`), reading README.md front-matter and the
license/usage sections of the card in each cached snapshot. Where the local card was missing, the license field came
from the Hugging Face Hub API (repo metadata only). No weights were downloaded. **Not legal advice.**
"Commercial use" reflects only what the license or card states. **REVIEW** marks items that need owner or legal review.

| Repo (cached) | License as stated | Commercial use? | Attribution / conditions | Source |
|---|---|---|---|---|
| ResembleAI/chatterbox | MIT | Yes | Keep the MIT notice if weights are redistributed. Output is watermarked with Perth (resemble-perth, MIT). The app applies the Perth watermark to other engines' output too, which is good practice. | Web (Hub API). The local snapshot has no README. |
| hexgrad/Kokoro-82M | Apache-2.0 | Yes (the card explicitly welcomes commercial deployment) | Apache-2.0 LICENSE/NOTICE if weights are redistributed. The card lists CC-BY training audio (Koniwa, CC BY 3.0; SIWIS, CC BY 4.0). Carry those credits if weights are re-hosted. | Local card |
| openbmb/VoxCPM2 | Apache-2.0 | Yes (the card says "free for commercial use") | Apache-2.0 notice. The card **forbids** impersonation, fraud and disinformation, and asks that AI-generated content be labeled. | Local card |
| Qwen/Qwen3-TTS-12Hz-1.7B-Base | Apache-2.0 | Yes | Apache-2.0 notice. The card requests citation for research use. | Local card |
| Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice | Apache-2.0 | Yes | Apache-2.0 notice | Local card |
| Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign | Apache-2.0 | Yes | Apache-2.0 notice | Local card |
| Qwen/Qwen3-TTS-12Hz-0.6B-Base | Apache-2.0 | Yes | Apache-2.0 notice | Web (Hub API). The local cache holds only config.json. |
| Qwen/Qwen3-TTS-Tokenizer-12Hz | Apache-2.0 | Yes | Apache-2.0 notice | Web (Hub API). The local cache holds only config.json. |
| deAPI-ai/qwen3-tts-12hz-1-7b-voicedesign | Apache-2.0 (Hub tag) | Conditional. **REVIEW:** this is a third-party re-upload or derivative of Qwen3-TTS VoiceDesign, so provenance depends on the Qwen original. | Apache-2.0 notice, crediting both Qwen and deAPI-ai | Web (Hub API). The local cache holds only config.json. |
| k2-fsa/OmniVoice | Code Apache-2.0. **Weights CC-BY-NC (4.0)** "due to constraints from its training data (e.g., Emilia)". The Hub repo has no license tag. | **No** (non-commercial) | CC-BY attribution plus the NonCommercial restriction. The disclaimer prohibits unauthorized cloning, impersonation and fraud. | Local card (License section) |
| Serveurperso/OmniVoice-GGUF | CC-BY-NC-4.0 (links to the k2-fsa/OmniVoice license) | **No** | The same terms as OmniVoice. The GGUF conversion inherits the NC terms. Attribute both k2-fsa and Serveurperso. | Local card |
| microsoft/VibeVoice-1.5B | MIT | **Unclear / REVIEW.** The MIT license itself allows it, but the card says it is "limited to research purpose use" and "not recommended … in commercial or real-world applications". It lists out-of-scope uses (voice impersonation without recorded consent, disinformation, and others). | MIT notice. Output carries an audible AI disclaimer and an imperceptible watermark (per the card). | Local card |
| vibevoice/VibeVoice-1.5B-hf | MIT | Unclear / REVIEW (the same research-only card language) | Same as above | Local card |
| vibevoice/VibeVoice-7B-hf | MIT | Unclear / REVIEW (the same research-only card language). Only the README is cached, so the weights are not downloaded. | Same as above | Local card |
| openai/whisper-large-v3-turbo | MIT | Yes | MIT notice if redistributed | Web (Hub API). The local snapshot has no README. |
| *dataset* bezzam/vibevoice_samples | MIT | Yes (as stated). **REVIEW:** the provenance of the speaker voices in the sample clips is not documented. | MIT notice | Local card |
| lj1995/VoiceConversionWebUI (RVC assets; **not cached, not installed**) | MIT (Hub tag) | Yes as stated. HuBERT and RMVPE provenance has not been verified (**REVIEW** if RVC is ever integrated). | MIT notice | Web (Hub API) |

## Notes

- `models.json` already records these licenses (`mit`, `apache-2.0`, `cc-by-nc-4.0`, `mit-research`). These findings
  match it. Keep the red "non-commercial" badge for OmniVoice and the amber "research-only" badge for VibeVoice.
- Weights are **not shipped** with the repo or an installer today. Users download them from the Hub at first use, so
  the terms bind the end user. If a future installer pre-bundles weights, only the MIT and Apache-2.0 models (Chatterbox,
  Kokoro, VoxCPM2, Qwen3-TTS, Whisper) are candidates. OmniVoice must never be bundled in a commercial product, and
  VibeVoice needs a decision from the owner.
- Voice-cloning ethics clauses (VoxCPM2, OmniVoice, VibeVoice, Chatterbox's Perth watermarking) argue for keeping the
  app's consent and watermark defaults during the rebrand.
