# Performance Direction: testable editor prototype and Drama 3 evaluation plan

**Status:** RESEARCH SPECIFICATION / NOT IMPLEMENTED
**Date:** 2026-10-18
**Tracking:** [Sonic Rift #116](https://github.com/Knapp-Kevin/sonic-rift/issues/116)
**Architecture proposal:** [ADR 002 (proposed)](adr-002-performance-direction-proposed.md)
**Source of Drama 3 tag support:** https://docs.fish.audio/features/text-to-speech/drama-3

## Product job

Given a script and a selected voice, a user should be able to choose a phrase, direct how it is spoken, compare original/directed takes, and save the intended performance without sacrificing existing plain-text generation or ordinary layered timeline edits. A successful demo shows **editing and control preservation**, not just a textbox that sends tags to an API.

### Target user flow (Qt desktop, opt-in)

1. In Create's optional **Performance** submode or a project narration clip editor, enter plain script text. Initially use a *single narrator and one phrase*, not the full 16-character scene.
2. Highlight a word or phrase. Invoke "Direct selection" from a compact toolbar or keyboard-accessible menu. Offer the seven Drama 3 paired delivery options (only for a Drama 3-compatible preview), plus a free-text **direction before this passage** action.
3. Render visible inline annotations/chips without changing the spoken script. Inspect/edit/remove each one from a small inspector. "Show generated prompt" reveals the model-specific output for diagnosis, separately from editable spoken text.
4. Preview original vs directed take, record subjective verdict, and choose a winner. Each take preserves original text, direction intent hash, speaker binding, model identity, runtime and output media hash.
5. Undo any one annotation as one project-independent intent transaction. Editing text moves/adjusts annotation boundaries deterministically or prompts when ambiguity would discard scope.
6. Optionally set a speaker's spoken language and **accent hint (experimental)**, visibly marked not calibrated and not guaranteed. One voice does not magically become a new region when a text prompt changes.
7. Existing Create and project clips continue to generate normally with no import/export/schema impact. Any future project persistence requires a separate approval and explicit schema decision.

## Interaction model

**Minimum testable prototype**: Qt-free `PerformanceScript` model + compiler + unit tests, followed by a throwaway/scratch-profile PySide6 text editor inspector behind a feature flag. No engine inference needed for the first prototype. Keep it in an isolated test harness or unpublished branch; do not register a provider or alter shipped `models.json`.

- **Document**: stable `script_id`, `version`, local cast, ordered utterances. One utterance has unique ID, `text`, `speaker_id`, spoken `language`, optional free-text `direction_before`, optional `accent_hint`, ordered zero-width cue events, zero or more half-open delivery spans.
- **Selection**: Qt's cursor is not guaranteed to use the same indexing as Python Unicode; explicitly translate with a tested Unicode conversion layer. Reject invalid ranges and grapheme splits; do not silently move annotations from an intended word to adjacent punctuation.
- **Direction**: natural-language bracketed instructions are **not a fixed validated emotion taxonomy**. UI may suggest presets, but preserve user-authored exact text; emit only when provider supports this class. Confirm brackets/structural syntax can be safely represented, otherwise refuse instead of silently injecting tokens.
- **Delivery spans**: initial supported set `whisper, emphasis, soft, fast, slow, stress, forceful`. Do not add undocumented tags by extrapolation; no overlapping or nested spans in first prototype. Ending one scoped span resumes the prior instruction context (verify acoustically).
- **Cues**: ordered sound/pause insertion at a text boundary. Store a structured cue with explicit position and meaning, not a literal escaped bracket string; free-form event directions are provider-specific capability. Duplicate same-boundary event ordering is stable.
- **Accent**: independent of spoken `language`, `speaker_id`, and timbre. Free-text `accent_hint` is the only candidate until tests demonstrate a stable native API. Broad Scottish English and French-accented English are hypotheses; regional subtypes require competent listeners. No percent strength or location authenticity badge.
- **Multi-speaker**: one explicit local speaker reference per turn; allow 1–16 only when using the Drama 3 backend. Compile ordered first-appearance assignments to index tags with corresponding ordered permissioned provider reference IDs. A local voice-library ID is not a provider voice ID. No implicit upload of source audio.
- **Accessibility**: keyboard-only select/apply/remove; annotation list announced to accessibility services; undo/redo works without pointer; high-contrast and 100/125/150% scaling; pasted text receives no executable tag privileges.

## Draft syntax compiler contract

Input is structured intent and a declared engine capability manifest. Output is `compiled_text`, ordered provider voice/reference IDs, warnings/errors, provider manifest ID, intent hash, and a "generation allowed" boolean. No output implies sound generation or API access.

For a Drama 3-capable **single speaker** (illustrative and not a source audio result):

Spoken text: `Do not open the door.`  
Direction before: `voice drops to a terrified whisper`  
Span `emphasis` over `open the door`  
Expected compilation: `[voice drops to a terrified whisper] Do not <emphasis>open the door</emphasis>.`

That exact combination uses bracket directions and an allowed paired tag. Do not fabricate an explicit proprietary `emotion=terrified` API field.

For multi-speaker dialogue, preserve ordered speaker turns and emit `<|speaker:N|>` + accepted directions and spans; `reference_id` array order must match the indices.

For a neutral engine lacking performance support: fail with `UNSUPPORTED_DIRECTION` and present **(a)** switch to a compatible engine, **(b)** edit/remove direction, or **(c)** user-authorized plain-text generation with an explicit warning. Never send markup to unsupported backends and never drop instructions silently.

User text resembling `<whisper>` or `<|speaker:0|>` is **ordinary spoken text** unless independently created as a structured annotation. A compiler must escape it safely if the provider supports literal syntax, or reject unsafe compilation. Literal brackets and markup require adversarial tests; do not assume Fish parsing has a documented literal escape sequence.

## Model-independent test fixtures

| ID | Action / fixture | Deterministic acceptance |
| --- | --- | --- |
| PD-01 | Plain unannotated text | Same spoken text, no markup; existing Create generation adapter unchanged |
| PD-02 | Select `open the door` and apply emphasis | Exactly that substring gains `<emphasis>…</emphasis>`; punctuation unchanged |
| PD-03 | Add direction before phrase midway | Bracketed direction placed before target, without modifying preceding spoken text |
| PD-04 | Remove annotation, then Undo/Redo | Restores identical intent and compiled bytes as one transaction; no audio rewritten |
| PD-05 | Insert/delete text before scoped span | Rebase endpoints correctly; selected words remain selected or explicit conflict shown |
| PD-06 | Edit through an annotated span | Deterministic expansion/shrink policy documented and tested; ambiguous deletion requires explicit resolution |
| PD-07 | Overlap and nested selections | Reject or normalize explicitly, never construct malformed nested markup |
| PD-08 | Pasted literal `<whisper>`/speaker markup | Not treated as a command; safe literal emission or refusal |
| PD-09 | Emojis, accents, combining marks, RTL | Qt-to-model index parity, no split grapheme, lossless fixture round-trip |
| PD-10 | Add two cues at same offset | Stable deterministic event order, no hidden extra spoken text |
| PD-11 | Unsupported model chosen | Refuse with reason; no silent flattening, no tags voiced |
| PD-12 | 16 valid speakers, then 17th | Correct mapping for 16, reject 17th before generation |
| PD-13 | Reorder utterances | Recomputed speaker mapping is deterministic and references remain associated with identities |
| PD-14 | Cloud API disabled | No call or voice upload when auth/consent/cost cap absent |
| PD-15 | Missing/mistyped `model: drama-3` header | Reject or label backend unverified; never count as valid Drama 3 benchmark |
| PD-16 | Async result after project switch/edit/cancel | Do not attach output to stale clip/project; no partial take |
| PD-17 | Write current v1 `*.sonicrift.json` | Existing save/reopen unchanged; no v2 keys or disguised markup inserted |
| PD-18 | Prototype rich editor restart in scratch profile | No live user settings or source media modified |
| PD-19 | Malicious enormous directions, invalid offsets/IDs | Bound inputs; refuse safely before model or network work |
| PD-20 | Non-Drama engine explicit plain-text fallback | Generates spoken text only after user consent, with loss-of-direction notice |

## Proposed controlled audio comparisons (NOT RUN)

**Phase A: evaluate product value before engine local-install feasibility.**
- Tasks: neutral line, whisper on 3–6 words, forceful on 3–6 words, quiet anger, fear building mid-line, laugh/breath cue, mixed speaker turns, mixed language sample (experimental), difficult pronunciation and reference-voice continuity.
- Include a **baseline with no direction** and **control trials where direction is moved to a different phrase**. These measure whether an engine truly obeys *scope*, rather than sounding generally expressive.
- Compare Drama 3 against Sonic Rift's available Qwen3, VoxCPM2, VibeVoice and Chatterbox capabilities only where modes are comparable. Kokoro is a useful speed/basic speech baseline, not a scoped-direction competitor. Use equal human-readable script, reference voice rights and at least two generations per condition; do not claim a model is better based on one lucky take.
- Listen blind and record separately: target-direction correctness, spillover into neutral span, word intelligibility, perceived naturalness, speaker identity continuity, emotional fidelity, language consistency, audible artifacts and take-to-take variance. Log failures, not only best outputs.
- **Accent experiment**: matched spoken English text in neutral, broad Scottish-English and French-accented-English directions; with and without a rights-cleared reference accent; compare to identical text rendered without hint. At least two unseen lines per condition and independent familiar listeners; collect free-response category, perceived strength, naturalness, intelligibility, and speaker/timbre continuity. Report "not reliably controllable" if evidence fails.
- Score as separate measures, not one opaque global score. Define a human-judged minimum before trial; publish raw anonymized ratings and confidence intervals or descriptive uncertainty, not invented pass rates.

**Phase B: runtime/cost feasibility (requires resource approval).**
- Record engine/provider revision, actual backend attestation where possible, tested prompt text hash and settings, input voice permission ID/hash, seed if applicable, output audio hash, cold/warm latency, time-to-first-audio, throughput/RTF, peak VRAM and host RAM, CPU/GPU load, fault recovery, and any model fallback.
- Target owner's Windows machine (RTX 5070 Ti 16 GiB). Prefer isolated sidecar and pinned model revisions; local viability is a question, not a fact. Do not auto-download a 40+ GiB checkpoint or assume quantization yields acceptable quality. A hosted API trial is separately authorized and capped in advance.
- Validate cancellation, stale project, active-model busy arbitration, lost network, provider authentication, permission denied, malformed provider response and failed export; rerun exact-main Windows tests if future integration alters source-run app.

## Stop conditions and decision rubric

**GO for editor implementation** only if:
1. Pure parser/editor prototype passes every applicable deterministic case including existing-text regression and accessibility.
2. At least one model materially obeys scoped changes better than an undirected baseline across independent tests, without unacceptable intelligibility/voice-quality tradeoff.
3. A legally usable, consent-compatible runtime/provider path is feasible and locally documented.
4. Architecture/persistence ADR and owner gate are approved.

**LIMITED GO** if generic directions work but span scope/accents do not. Limit UI to controls backed by evidence, mark accent hints experimental, and leave native accents disabled.

**NO-GO** if scope fidelity fails, provider cannot verify selected model, costs/latency violate agreed budget, code/weight license cannot be cleared, or consent/privacy gates cannot be met. A gorgeous tag editor that reads literal angle brackets aloud is not success.

## Work packages and explicit ownership gates

- **R1 / current:** proposed ADR, spec and source evidence; **docs-only** branch/PR; review with #56 and #40. No installed feature claim.
- **R2 / after docs acceptance:** isolated Qt-free structured intent, safe compiler and fixtures PD-01..PD-20. No user files or runtime models.
- **R3 / after prototype tests:** scratch-profile Qt inspector/UI, keyboard and Unicode selection tests. No source app default toggle, no production schema mutation.
- **R4 / separately authorized:** controlled Drama 3 comparative audio trials with voice rights, runtime/API/cost constraints and blind listener protocol.
- **R5 / explicit decision:** accepted/rejected schema evolution, backend integration, merge and exact-head Windows acceptance.

**Present state:** R1 documents only. No tests executed in this document-writing pass, no prototype code, benchmark recordings, cloud transactions, locally installed Drama 3 engine or shipped UI controls.
