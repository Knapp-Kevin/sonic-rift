# Accent Design Studio: engine and architecture research

**Status:** research finding, not a performance certification or implementation authorization.  
**Checked:** 2026-10-10  
**Workstream:** [epic #40](https://github.com/Knapp-Kevin/this-voice-thing/issues/40), [capability issue #41](https://github.com/Knapp-Kevin/this-voice-thing/issues/41).  
**Decision:** #44 must explicitly approve a scoped implementation after comparative listening evidence.

## Executive finding

This Voice Thing already has the building blocks to **attempt** accent design. Do **not** add an engine or implement a calibrated accent slider yet. Compare (1) free-text Qwen3 VoiceDesign, (2) free-text VoxCPM2 Design, and (3) an explicitly permissioned reference-clone condition. OmniVoice provides a valuable structured-accent baseline **only for its published attribute values**. Glasgow, Edinburgh, French-accented English and accent intensity are **not verified** capabilities of these engines.

Distinguish:
- **Documented API:** can pass a voice description, fixed accent enum, style text or reference audio.
- **Hypothesis:** resulting speech has a particular region's authentic phonology/prosody.
- **Measured result:** only after recordings and competent human evaluation. **No audio trials or native-speaker panels have been run in this research pass.**

## Current application evidence (main as checked)

| Path | Verified behavior | Gap relevant to accent work |
| --- | --- | --- |
| [models.json](../models.json) | Qwen3 custom voice, VoiceDesign and Base; VoxCPM2 dual design/clone; OmniVoice dual design/clone; Chatterbox, Kokoro, VibeVoice configured | Registry has license strings and engine mode but no independently validated accent/region/intensity capability contract |
| [core/voice_studio.py](../this_voice_thing/core/voice_studio.py) | design(model, description, ...); prompt passed to model.instruct, generates candidate; speak(...) clones/refines via saved clip; preserve model state during operations | No typed accent schema, accent-specific prompt compilation or fidelity evaluation |
| [ui/pages/studio.py](../this_voice_thing/ui/pages/studio.py) | Existing Clone/Design/Remix; free-form description; OmniVoice attributes menu; model/language chooser; candidates; save selected take | Language dropdown currently identifies text language only; region and accent source not distinct |
| [core/voice_library.py](../this_voice_thing/core/voice_library.py) | Voice stores kind, repo_id, backend, description, language, origin, clip, notes/tags; JSON persistence | No discrete accent intent, prompt recipe revision, model weight revision, quality/confidence, evaluation or consent fields; backward-compatible schema design needed |
| [engines/qwen.py](../this_voice_thing/engines/qwen.py) and [engines/qwen/qwen_worker.py](../engines/qwen/qwen_worker.py) | Text voice design and Base cloning; longer runs design first section, then clone the anchor | Test accent drift/identity after the section handoff; Base clone-model loading may affect VRAM/performance |
| [engines/voxcpm/voxcpm_worker.py](../engines/voxcpm/voxcpm_worker.py) and [engines/voxcpm.py](../this_voice_thing/engines/voxcpm.py) | Prefixes style/description in parentheses; optionally sends reference and transcript | Need empirical evidence for *accent* retention versus style/emotion; when transcript is supplied, upstream describes continuation as a different cloning mode |
| [engines/omnivoice.py](../this_voice_thing/engines/omnivoice.py) | Hard-coded DESIGN_ATTRIBUTES whitelist, check_description rejects unknown text; supported English accents fixed | Specific Scottish/French English regions are not in the structured list; don't silently map to 'British' |
| [tests/test_voice_studio.py](../tests/test_voice_studio.py) | Fake-model behavioral tests for design, clone and state restoration | Tests cannot measure actual accent accuracy |

**Potential issue for review:** Saved-voice descriptions in the UI say a frozen voice sounds the same every time; saving an anchor preserves the *reference*, not necessarily bitwise or acoustically identical stochastic future generations. Do not promote this promise to accent repeatability without trials.

## Engine capability matrix

Definitions: **native** = public documented API attribute; **free-text** = accepts words, with no guaranteed interpretation; **reference** = condition on permitted speech; **none** = no documented corresponding feature in the current model path; **unverified** = no local perceptual test. Availability below describes configuration/API, **not** whether an engine is currently installed on the user's PC.

| Current engine / variant | Voice creation or conditioning | Accent control actually documented | Intensity mechanism | Reference | License / deployment caution | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen3-TTS 1.7B VoiceDesign | Free-text voice instructions | Free-form descriptive prompt; **no guaranteed Glasgow/Edinburgh/Paris/Quebec output** | Prompt-only, uncalibrated | Reuse via separate Base/clone workflow | Apache-2.0 model metadata; package/model terms must remain traceable | High API / unknown accent fidelity |
| Qwen3-TTS 1.7B Base | Cloning from reference clip and optional transcript | Accent may transfer from reference, unquantified | No documented native accent intensity control | Yes | Apache-2.0 metadata; voice permission required | High API / unknown retention |
| Qwen3-TTS CustomVoice | Built-in speakers with style instruction | Speaker presets/styles, **not** a regional accent selector | Prompt-style guidance, not calibrated | No arbitrary speaker clone in this variant | Apache-2.0 metadata | High API / unknown accents |
| VoxCPM2 | Description-based design, styled clone or reference+transcript continuation | Free-text voice description; no published validated regional accent inventory located | Free-text only, not calibrated | Yes | Apache-2.0 for released code/weights per upstream; local adapter behavior must be tested | High API / unknown accent fidelity |
| OmniVoice | Fixed structured attribute voice design and cloning | English accent enum: American, British, Australian, Canadian, Indian, Chinese, Korean, Japanese, Portuguese, Russian; Chinese dialect enumerations also available | No strength attribute on published list | Yes | **Code Apache-2.0 but pretrained weights CC BY-NC**; not commercially cleared | High enum/license / unknown perceptual effect |
| Chatterbox multilingual | Multilingual reference-audio cloning | Upstream cautions that mismatched reference and language tags can transfer accent; no regional selector in configured API | Exaggeration/CFG are not accent-strength sliders | Yes | MIT model metadata; audio and reference rights apply | High conditioning / unknown regional fidelity |
| Kokoro-82M | Fast preset voices | Specific built-in voice choices, not an arbitrary regional accent-design API | None | Not via official current app adapter | Apache-2.0 metadata | High preset limitation |
| VibeVoice 1.5B | Multi-speaker conversation with supplied speaker audio | No current dedicated region/intensity design control in app | None | Yes, as multi-speaker conditioning | Current repo registry labels research-only; upstream Microsoft VibeVoice card advises research rather than commercial/real-world use; **model identity/source differs from Microsoft's card: verify lineage** | Medium; exclude from initial accent design |

**Special case:** OmniVoice may synthesize many languages, but documented *design attributes* cover English accent enums and Chinese dialect enums specifically. Multilingual synthesis support does not imply free-form accented voice design in every language.

**Special case:** A French-accented English speaker is not the same task as synthesis in French with a metropolitan or Quebec French regional variety.

## Primary upstream evidence reviewed

1. [Qwen3-TTS repository, API, VoiceDesign-to-Clone](https://github.com/QwenLM/Qwen3-TTS) and [single-speaker Base fine-tuning instructions](https://github.com/QwenLM/Qwen3-TTS/blob/main/finetuning/README.md). Free-form voice design is explicitly documented; locality/strength precision is not certified.
2. [VoxCPM2 repository, supported languages, voice design, cloning and weights license](https://github.com/OpenBMB/VoxCPM); [CLI control argument](https://github.com/OpenBMB/VoxCPM/blob/main/src/voxcpm/cli.py). Description is prepended to synthesis text; explicit regional guarantees not established.
3. [OmniVoice exact design attribute vocabulary](https://github.com/k2-fsa/OmniVoice/blob/master/docs/voice-design.md); [official weight license](https://huggingface.co/k2-fsa/OmniVoice). No Scottish or French-English enum, code license differs from checkpoint.
4. [Resemble Chatterbox README and language/reference caveat](https://github.com/resemble-ai/chatterbox). Its documented CFG/exaggeration guidance is expressive control, **not calibrated accents**.
5. [Kokoro-82M official model](https://huggingface.co/hexgrad/Kokoro-82M); [voices directory](https://huggingface.co/hexgrad/Kokoro-82M/tree/main/voices).
6. [Microsoft VibeVoice model-card responsible-use restrictions](https://huggingface.co/microsoft/VibeVoice-1.5B), distinct from the current configured [vibevoice/VibeVoice-1.5B-hf mirror](https://huggingface.co/vibevoice/VibeVoice-1.5B-hf). Model-card usage guidance and license must not be silently generalized to unrelated mirrors.

Model cards, repos and source are evidence of claimed supported APIs, not evidence of quality on any regional dialect.

## Engine decision and benchmark handoff

**Research candidate ranking, not a quality score:**
1. Qwen3 VoiceDesign: initial free-form Scottish and French-English prompt experiments, then Base-clone retention.
2. VoxCPM2 Design: independent free-text comparison; test controllable-clone and transcript continuation separately.
3. OmniVoice: *published enum* baseline (e.g., British versus American). Mark 'Scottish' or 'French' **unsupported as a native selectable attribute**.
4. Chatterbox: reference-only comparison if a legally sourced regional recording is available.
5. Kokoro/VibeVoice: omit from free-form accent design MVP absent contrary evidence.

**Local prerequisites:** confirm installed engine versions/checkpoints, model hashes, PyTorch/CUDA, available VRAM, optional second model load overhead, seed behavior, clip rights and transcript quality. The RTX 5070 Ti 16 GB target from the project's testing history is a target, **not a successfully measured run in this pass**.

**Training fallback:** Qwen documents single-speaker fine-tuning for its Base 0.6B/1.7B series with audio/text/ref_audio JSONL. This is possible in principle, but no claim of a 16GB VRAM fit, necessary dataset size, strength knob or successful accent generalization is justified. No training or downloaded checkpoints are authorized.

## Research gate and unresolved questions

- Does free-form 'Glasgow', 'Edinburgh' or 'French-accented English' produce recognizable phonetics rather than generic British/European speech?
- Can listener-rated accent strength increase monotonically with *requested* intensity while intelligibility remains acceptable?
- Do Qwen designed anchors, VoxCPM cloning, and reference-based Chatterbox preserve accent across 60+ seconds or is there drift?
- Does changing timbre/gender/emotion contaminate the accent comparison?
- Which regional varieties can be evaluated by suitable listeners with consented recordings?
- What is exact runtime memory/time/cold-load behavior on target PC?
- Do any terms or model lineage disclosures change in the pinned version?

**Do not implement regional presets, a percentage intensity slider, new fine-tuned model distribution, or accent-quality claims before #43 and #44.**
