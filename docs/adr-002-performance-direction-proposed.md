# ADR (proposed): Performance Direction as a first-class Sonic Rift authoring capability

**Status:** PROPOSED / RESEARCH ONLY. Not accepted for implementation, persistence migration or model integration.
**Date:** 2026-10-18
**Owner issue:** [#116](https://github.com/Knapp-Kevin/sonic-rift/issues/116)
**Related authorities:** [current architecture index](architecture/current-boundaries-2026-10-16.md), [ADR 001](adr-001-sonic-rift-timeline.md), [composer #71](https://github.com/Knapp-Kevin/sonic-rift/issues/71), [architecture #56](https://github.com/Knapp-Kevin/sonic-rift/issues/56), [Accent Studio #40/#43/#44](https://github.com/Knapp-Kevin/sonic-rift/issues/40), [source/weight rights #55/#60](https://github.com/Knapp-Kevin/sonic-rift/issues/55).
**Companion specification:** [performance-direction-prototype-spec.md](performance-direction-prototype-spec.md)

## Problem and product outcome

The existing Sonic Rift workflows can create or clone a voice, choose model-level settings, generate speech, save takes and arrange them in a project. They cannot yet **author, inspect, revise and preserve performance direction at the phrase/word/character-turn level** as an independent product concept. A provider accepting markup in an ordinary text box is not equivalent to an editable, portable, understandable performance plan.

The desired outcome is a creator selecting a span of text, applying a performance instruction, auditioning comparable takes, and preserving the intended direction and the actual generated take separately. The ability to choose an expressive model is a backend detail, not the feature definition.

## Verified local baseline (GitHub main inspected 2026-10-18)

- `models.json` registers Chatterbox, Qwen3-TTS, Kokoro, VoxCPM2, OmniVoice and VibeVoice. None is registered as Drama 3.
- `this_voice_thing/ui/pages/studio.py` exposes Clone/Design/Remix, model and language, description, preview takes, and model-dependent Chatterbox delivery controls. It does not offer a scoped-script annotation interface.
- `this_voice_thing/ui/pages/generation.py` passes a single text value plus voice/model-level settings into `AudioGeneratorThread`.
- `this_voice_thing/core/audio_project.py` defines strict `AudioProject` schema v1; `Clip` has `text`, one `voice_id`, an asset reference, and integer-frame timing. Unsupported schema/fields are not acceptable implicit migrations.
- `this_voice_thing/core/audio_project_session.py` validates edits on copies, commits one undoable revision, and checks stale async result attachment.
- `this_voice_thing/ui/pages/project_editor.py` provides the versioned project timeline and narration editing. Existing in-place generation work is tracked by #71 / PR #113; do not assume that unfinished branch is on current main.

All these observations refer to repository code, not newly executed Windows runtime tests.

## Primary-source Drama 3 capability evidence

Fish Audio's October 2026 [Drama 3 documentation](https://docs.fish.audio/features/text-to-speech/drama-3) and [launch description](https://fish.audio/blog/fish-audio-drama-3/) show:

| Mechanism | Verified syntax/behavior | Sonic Rift representation |
| --- | --- | --- |
| Natural-language directions | Square-bracketed text preceding the affected passage, including mid-line changes | Nonspoken instruction on a phrase/utterance |
| Vocal events | Square-bracketed sound/pause instructions placed at event position | Ordered, nonspoken cue event |
| Paired span tags | Documented: `whisper`, `emphasis`, `soft`, `fast`, `slow`, `stress`, `forceful` | A bounded delivery span, no provider markup in source text |
| Speaker turns | `<|speaker:0|>` through `<|speaker:15|>` with ordered `reference_id` voice IDs | Ordered utterance-to-voice binding |
| Language switching | Scoped language tags, explicitly experimental | Distinguish spoken language from accent |
| Pronunciation | `<|phoneme_start|>` and `<|phoneme_end|>`; language-specific phoneme alphabet | Optional pronunciation override with typed alphabet |

**Not established**: reliable Scottish, French-accented English, or any regional accent **parameter**; calibrated accent intensity; independent control of accent without speaker-timbre drift; local Windows 16 GiB latency/performance; universally available editing/inpainting API. Natural-language accent directions remain hypotheses requiring blinded listening.

**API verification hazard:** docs say an omitted/misspelled `model: drama-3` header falls back silently to `s2.1-pro`. A response is not evidence of Drama 3 unless requested backend selection and actual backend identity are verifiable; if the provider cannot attest the actual model, label the sample "provider-unverified" and exclude it from conclusive comparison.

## Options

1. **Raw Drama 3 markup in `Clip.text`**. Cheap to demonstrate, but ties saved content to a provider, pollutes plain reading and risks another engine speaking or stripping markup. **Reject as canonical representation**.
2. **Engine-neutral performance document + explicitly versioned provider compiler**. Separates user intent, editing, engine feature claims and generated asset provenance. Can feed Drama 3 first and other engines only as evidence allows. **Preferred proposed direction**.
3. **Entirely independent Drama 3 scene generator**. Reduces first integration risk, but duplicates voice libraries, project editing and audio takes. **Reject as product architecture**; a disposable external research harness is still permissible.
4. **Directly expand project schema v1 with arbitrary fields**. Creates incompatible files without migration guarantees. **Reject**.

## Proposed decision pending owner acceptance

**Treat Performance Direction as a capability owned by Create / voice narration / the layered project editor, using an engine-neutral, versioned `PerformanceScript` intent model.** Treat Drama 3 as a candidate compiler/backend, not as the schema owner.

**No implementation permission is implied by this proposal.** The first executable prototype may operate entirely in memory and may serialize to a temporary, isolated test fixture. It must not overwrite or silently extend existing `*.sonicrift.json` v1 projects.

### Proposed intent model, not an existing shipped schema

- `version`: explicit format revision, starting at 1 for the standalone draft format only.
- `utterances`: ordered records with stable IDs; each identifies a speaker from a local cast table, exact spoken `text`, an optional `direction_before` string, spoken `language`, optional **unverified** `accent_hint`, ordered events at validated text boundaries, and scoped `delivery_spans`.
- `delivery_spans`: `{start, end, kind}`, half-open offsets against utterance text. Initial `kind` allowlist is the seven documented Drama 3 paired tags. Never accept arbitrary HTML/XML as generated code.
- `cast`: stable local voice identity and permissioned audio reference metadata. A local `voice_id` is not a Fish Audio cloud `reference_id`; resolve it at generation time only with consent and backend mapping.
- `provenance`: stored with the generation result, not with editable user direction: engine ID, actual model/revision when verifiable, runtime API/local mode, request/intent hash, output hash, voice permission status, cost/rights decision, generation timing, listener verdict.

An *utterance* is an authoring/edit unit, not necessarily one physical audio clip. One scene may need many utterances. Project placement uses the existing immutable audio result/media resolver.

### Text editing and compilation contracts

1. Keep spoken text **separate** from all nonspoken direction and events. User selection edits structured spans, not a literal tag string.
2. Normalize a working text unit to NFC, define offsets as Python Unicode code-point indices in the model, and translate safely at the Qt editor boundary (Qt cursor positions can use UTF-16). Reject span endpoints bisecting extended grapheme clusters; preserve emoji, combining marks and RTL text across save/restore.
3. Span rules in v1 draft: sorted, non-overlapping spans; reject crossing/invalid/zero-length ranges; allow contiguous ranges. Avoid unspecified nesting semantics. Directions before utterances affect subsequent words until another direction; UI must not claim hard acoustic segment boundaries.
4. Compilers validate capabilities and supported tags per engine. Unsupported instructions cause a **visible actionable refusal or explicit user-authored flattening decision**; they must never silently disappear or be spoken verbatim. The plain-text fallback is *only* the spoken text and needs consent before generation.
5. For Drama 3, emit only allowlisted paired tags, escaped spoken text, properly ordered bracketed directions/events and speaker tags; map up to 16 permissioned reference IDs deterministically. Do not invent a standardized `[accent]` control or claim a speed slider is calibrated.
6. Prevent injection of structural tokens from user prose: literal brackets, `<|speaker:...|>` and paired tag-shaped input must not be reinterpreted as user-authorized directions. Prove the backend can faithfully speak literal reserved characters; if impossible, refuse with a clear message rather than leaking untrusted markup.
7. Validate constraints, length, voice rights and backend identity *before* allocating model resources, uploading audio, or starting billable API calls. No automatic remote fallback from local to hosted inference.
8. Re-render creates a new immutable take. Modifying one direction invalidates affected preview status but never rewrites previously accepted audio. New/Open/Cancel/Undo and stale job results retain the #71 session, revision and clip safeguards.

### Project schema evolution

Current schema is `AudioProject.SCHEMA_VERSION == 1`. Persistent performance intent cannot be smuggled into `Clip.text` or appended to v1. After approval, separately decide **v2 project schema versus a versioned linked intent asset** with safe source IDs and immutable hashes. Define v1-to-v2 import, new-version refusal, atomic save/reopen, backups and cross-version user-facing warnings in ADR #56 / #71 before shipping it. Until then use isolated ephemeral prototype state, never modifying real user projects.

### Provider capability taxonomy

Expose independently evidenced states: `native_scoped`, `native_direction`, `prompt_only_experimental`, `reference_conditioned`, `unsupported`. Each visible UI control must identify which state the selected engine truly supports. No undifferentiated "accent" slider; separate **spoken language**, **accent family/region**, **reference accent**, **requested strength (unvalidated descriptive intent)** and **speaker identity**.

## Licenses, external services and trust

Official [Drama 3 model LICENSE](https://huggingface.co/fishaudio/drama-3/blob/main/LICENSE) is Fish Audio Community License v1.0, not an OSI permissive license. Its community commercial rights depend on a USD 500,000 annual-revenue threshold and other terms; independent hosted self-serve TTS requires separate written permission. Verify the full applicable terms, notices and weight/runtime rights with #55/#60 before distribution; no model weight is included in Sonic Rift by this ADR. Hugging Face metadata may show a different license identifier from the model's actual LICENSE. Treat the controlling text as a review issue, not a cleared redistribution decision.

Local research: opt-in resource consumption, pinned weights, isolated process and no automatic downloads. Hosted research: separate explicit consent for transmitting script/reference voice, API usage/cost limit, no cloud credentials in project files/logs, no external calls until authorized. Require voice subject rights/consent and content provenance.

## Promotion gates (no unsupported performance claims)

1. **Pure contract/editor prototype**: unit tests for span edits, grapheme conversion, composition, serialization of test fixtures, provenance and provider mismatch; no engine inference.
2. **Human-directed comparative bench**: paired neutral vs directed lines with matched voice reference, same texts and multiple seeds/takes, holdout samples and failures logged, comparing current Sonic Rift engines and Drama 3. See [prototype spec](performance-direction-prototype-spec.md).
3. **Accent bench**: separate spoken-language and accent hypotheses; blinded regional listeners; record recognizability, naturalness, fidelity, timbre consistency and actual artifacts; coordinate with #43/#44 before calling a region supported.
4. **Runtime/rights feasibility**: measured local Windows 16 GiB VRAM latency/peak memory and recovery, or separately authorized metered API; observe permission, cost and privacy gates.
5. **Reviewer and owner decision**: GO / LIMITED GO / NO-GO with exact evidence; accepted ADR change and narrowly scoped implementation PR only after authority is explicit. Keep composer #71 and Live #13/#61 acceptance unaffected.

## Rejected short-cuts and open questions

- No false `<accent>` markup or native accent dropdown until its semantics and behavioral fidelity are proven.
- No provider-specific tags hidden in ordinary Create text.
- No paid calls or reference-voice transmission as an undocumented benchmark side effect.
- No premature real-time microphone claims. Drama 3 TTS is not RVC.
- Open: neutral provider degradation UX, exact Qt rich-text selection implementation, clip-wide vs scene-wide authoring ownership, persistence v2 vs linked sidecar, legitimate nested directions, multilingual tag parser, actual model attestation by cloud provider, when owner approves runtime spending.

**Status at writing:** proposal and specification, not a runtime benchmark, prototype UI, installed engine, model comparison result or release approval.
