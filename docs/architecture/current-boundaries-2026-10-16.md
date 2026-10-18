# Sonic Rift current architecture boundaries and acceptance contract

Status: **working architecture index entry, updated after Windows local-use GO evidence** (2026-10-16). Tracking: [#56](https://github.com/Knapp-Kevin/sonic-rift/issues/56), [#71](https://github.com/Knapp-Kevin/sonic-rift/issues/71), [#61](https://github.com/Knapp-Kevin/sonic-rift/issues/61), [#13](https://github.com/Knapp-Kevin/sonic-rift/issues/13).

This document distinguishes the *integrated capabilities recorded by the delivery issues* from unverified future architectural contracts. It is not a declaration of full Windows runtime acceptance or commercial-license clearance. Code and accepted ADRs take precedence when this working summary conflicts.

## Canonical delivery boundaries

| Concern | Current responsibility / contract | Follow-up authority |
| --- | --- | --- |
| Application shell / journeys | Source-launched Qt desktop app keeps Create, Voices, Sounds, Live, Models and settings operational. Project editor is opt-in and must preserve legacy single-text Create. | #61 integrated Windows acceptance; #54 migration |
| Project state | Versioned, locally persisted track/clip project with source references, bounded undo/redo and safe save/reopen. The project model is the edit authority, not waveform pixels. | #71 composer |
| Timeline view | `this_voice_thing/ui/project_timeline.py` renders lanes, waveform previews, ruler, playhead and reports click/selection/seek signals. It does not own project mutations. `this_voice_thing/core/timeline_visual_math.py` holds Qt-independent ruler/envelope logic. | #71 drag/trim review |
| Mixing / export | Frame-based mixing, normalization and WAV/MP3/OGG delivery/stems are integrated according to #71. Verify actual measured output on combined main before acceptance. | #61 |
| Sound and voice assets | Generated/imported media remain identified sources; source/media mutation and saved project stale-update conflicts must fail safely. Maintain license and consent provenance independently of filenames. | #61, #55 |
| Background work | Long import/export/generation operations must not block Qt's UI, and cancellation/late results must not mutate the wrong project or clip. | #61, #71 |
| Live audio | Realtime output and monitor sinks, queue and model switching have distinct lifecycle and failure conditions; full device/latency/soak qualification remains open. | #13 |
| Providers / hardware | Provider and model boundaries may be reused across journeys, but a TTS engine is not assumed to provide sound generation or arbitrary accent control. Installed engine/weight rights and source inheritance are separate decisions. | #55, #57, #40 |
| Plugins / external integration | **No stable external plugin API is certified by this document.** Define explicit versioned permissions, data exchange and lifecycle only when implementation is approved. | #56 subsequent ADR |

## Composer editing invariants (drag/trim integrated in #111; continue enforcing for future slices)

1. Timeline pointer events produce *proposed* clip edits, never direct mutation of project data inside paint code. Session/project state validates and commits; UI rerenders accepted state.
2. Positions and durations are canonical integer frames at the project's sample rate. Convert display seconds/pixels at the UI boundary with documented rounding; guard zero/negative length, overflow and out-of-range starts.
3. Move and trim preserve stable clip/source identifiers, original source recordings and source hashes. No destructive rewrite of source PCM.
4. A single completed gesture is one undoable transaction. Escape, pointer cancel, interrupted drag or stale project revision must leave the original project intact.
5. Asynchronous generation and import carry project/clip/revision identity. A late result for a closed/replaced project is rejected; validated replacement retains the previous take until its commit succeeds.
6. Visual preview, exported mix and reopened project must agree on clip geometry and effective audio; regression tests should compare frames and media hashes, not only screenshots.
7. Mouse, keyboard/focus and high-DPI behavior require *real* Windows Qt verification. Pure-Python math tests cannot certify interactive dragging.

## Verification levels, not synonyms

- **Static/source evidence:** reviewed code and precise commit/blob identity.
- **Automated isolated tests:** deterministic behavior for that exact code revision.
- **Installed-source GUI evidence:** real Windows startup, Qt painting, device, model and interaction paths with isolated profile.
- **Audio acceptance:** measured duration/peak/loudness, physically audible monitoring and device/route observations.
- **Owner/product acceptance:** distinct explicit review after technically passing checks.

The original #99/#101/#103/#104 per-PR checks and #105 math tests did not establish integrated acceptance alone. Later Windows regression and exact merged-tree verification for `c0fc13bba6d88bc5fb9a94d24dba09bc24c43e3b` were recorded in #61, supporting GO **for local source-run use** with explicit device, audible-latency, and owner-listening exclusions. This does not automatically certify subsequent commits or distribution. Packaging, signing and Store distribution are deferred P4; they do not block source-app acceptance.

## Decision register still open

- Choose the public stable project-file/schema and migration policy after the implementation contract is inspected, including forward-version refusal and backup recovery. Do not invent format compatibility.
- Specify the cross-provider generation job / cancellation / error envelope, ownership and failure recovery in an accepted ADR before calling it a public extension interface.
- Decide whether project timeline edits permit overlap within a track and how snapping works; make current mixer behavior the test oracle rather than changing it implicitly.
- Verify actual installed model/source/weight licenses and remaining derived UI/worker functions under #55/#57 before removing upstream notices or claiming independence.
- Preserve #107/#108 monitor/queue regression evidence and investigate remaining first-line monitor offset, physical latency and external routes under #13.

## Update discipline

Issue #56 tracks architecture reconciliation; #71 tracks composer features; #61 tracks integrated source-run acceptance; #13 tracks Live Voice reliability. Update these at the same commit/PR checkpoint. Do not replace feature evidence with this architecture summary and do not close issues on planning text alone.

## Proposed extension track (2026-10-18): Performance Direction

**Research and architecture only; not an accepted implementation or shipped engine.** [Issue #116](https://github.com/Knapp-Kevin/sonic-rift/issues/116) tracks a first-class phrase-level speech-direction capability, with Fish Audio Drama 3 as an evaluation backend rather than an architectural dependency.

- [Proposed ADR 002: Performance Direction](../adr-002-performance-direction-proposed.md) records the verified provider features, engine-neutral authoring model, compatibility boundaries and open decisions.
- [Testable prototype and comparison specification](../performance-direction-prototype-spec.md) defines deterministic editor/compiler cases, scoped markup, accent experiments, privacy/license gates and evidence-driven promotion.
- Current \`AudioProject\` schema v1 remains canonical; no additional project keys, user-data migration, loaded model, implementation API or live feature is authorized by these research docs. Any persistent performance structure needs a separate approved versioned format decision.
- Keep #71 composer delivery, #13 Live audio QA, #61 Windows source-run acceptance and the #40/#44 Accent Studio approval gates independent. If future implementation proceeds, reconcile provider capability mapping and job ownership against current code and this index before code merge.
