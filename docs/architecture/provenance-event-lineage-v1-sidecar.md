# Per-clip creation-event ledger prototype

**Date:** 2026-11-10  
**Status:** P0 research/implementation prototype, **not integrated into Studio export or signed**.  
**Owner issue:** [Sonic Rift #177](https://github.com/Knapp-Kevin/sonic-rift/issues/177), within [P0 Epic #169](https://github.com/Knapp-Kevin/sonic-rift/issues/169).  
**Base:** draft source-capture [PR #175](https://github.com/Knapp-Kevin/sonic-rift/pull/175).

## Decision proposal: v1-compatible companion, not schema migration

Current v1 project tests explicitly require `AudioProject.SCHEMA_VERSION == 1`. An inline field such as `Clip.creation_event_id` would break existing readers. This prototype therefore tests a sibling `<project filename>.lineage.json` document with:
- A schema version, project identity, exact project revision and canonical project-document SHA-256.
- **Creation-event ID** (UUID32) distinct from the media byte SHA-256, plus source asset ID, observed origin, engine/model family and actual recorded revision when available.
- **Per-clip binding:** clip ID → creation-event ID. Two clips referencing the **same** `voice_<sha256>` can be distinct: one application-observed generated source event, another unknown import. A clip split or duplicate can point to the original event if the app **explicitly** links it.
- Separate mutation API: `capture`, `bind_existing`, `advance` on validated project snapshots; creates no files or edits project JSON unless `save_lineage` is called. A source-asset replacement drops its old clip binding; undo/redo can explicitly advance the ledger while checking snapshots.
- Local ledger event history is append-only when replacing a sidecar through the application helper; missing/stale/malformed files **fail closed**, never become human-only or verified.
- Prompts, lyrics, user identity, machine paths, reference voices, seeds and private settings have no fields in this initial minimal event schema.

## Risks and constraints

**This is not a production solution yet.** The project JSON and its sibling sidecar are separate filesystem objects and cannot be atomically renamed as a single transaction. The reader checks project revision and canonical content fingerprint on every read; a torn save therefore produces a **stale/invalid, untrusted** sidecar instead of upgrading origin, but may lose proof that was not committed as part of the same transaction. C2PA signing and a durable journal/transaction protocol are later gates. Do not wire to the export path until failure/recovery and undo/cancel behavior are independently tested.

A source event can be appended only through application-owned code, but local JSON and metadata can be altered by anyone with write access. A SHA-256 checks consistency, **not** creator truth, signature trust, a model's training license or ownership. No `human_capture` event is accepted from this unauthenticated prototype; external/optional creator declarations belong to separate, opt-in trust handling.

The existing source library has a digest-scoped `.origin-ambiguous` conservative fallback when two origin contexts produce byte-identical voice media. This ledger must eventually replace that global fallback with per-clip event references while retaining the conservative behavior for legacy clips without events. The prototype does **not** remove existing collision quarantine, retroactively attest imports or silently convert old source records.

### Alignment with the new P0 Epic #169 comment

The [cross-product strategy note](https://github.com/Knapp-Kevin/sonic-rift/issues/169#issuecomment-6776394076) explicitly keeps Sonic Rift **AI-first** with required P0 generated-media disclosure. The optional human-creator process/benefit program is [Optic Rift #64](https://github.com/Knapp-Kevin/optic-rift/issues/64), **P1 discovery only**, not a new Sonic Rift feature commitment.

The event model deliberately separates **observed source creation** from **signer integrity**, **identity**, **rights/licensing**, and **artistic merit**. It has no creator score, human-made badge, AI detector, opt-in identity publication or implied transfer of copyrighted materials. Public C2PA must remain independently readable; detailed private evidence may be separately encrypted under a future owner-approved key policy. Production signer/fallback authority stays undecided in [Sonic #174](https://github.com/Knapp-Kevin/sonic-rift/issues/174).

## Qualification checklist

1. Unit tests on exact branch head, from Windows with a disposable profile; confirm save and reopen of existing `schema_version=1` project bytes is unchanged by ledger save.
2. Distinct event identities for byte-identical audio with generated vs imported origin; no collision-induced silent promotion. A split/duplicate only inherits an event when explicitly bound; mismatched asset IDs rejected.
3. Undo/redo and gain/placement edits advance the ledger to the exact new revision; asset replacement drops stale binding, and a reopened stale sidecar refuses classification.
4. Corrupted/dangling/duplicate events, unknown schema, oversized sidecar, symlink, mismatched project, stale revision, appended-event deletion and overwrite of unrelated projects all fail closed with no unexpected user-media writes.
5. Cancellation and project-save crash window: deliberately inject failures between project and sidecar saves. Define recovery and migration before any UI binding or export use.
6. Independent review before merging this stacked draft PR, then only integrate in Studio through one approved, transactional authority. C2PA SDK Windows round-trip and trusted issuer are separate [#171](https://github.com/Knapp-Kevin/sonic-rift/issues/171)/[#172](https://github.com/Knapp-Kevin/sonic-rift/issues/172) gates.

**No release, signing identity, C2PA SDK, encrypted appendix, audio embedding, new provider, CI run or schema-v2 migration is authorized by this prototype.**
