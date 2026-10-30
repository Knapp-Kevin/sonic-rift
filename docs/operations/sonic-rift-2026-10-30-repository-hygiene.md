# Sonic Rift — repository hygiene and release qualification ledger

**Date:** 2026-10-30. **Source:** GitHub live PR and issue inventory, not a local Windows runtime run. Canonical owner-facing status until the next evidence update.

## Decision

- **GO:** narrow Qt-independent waveform math correction PR #115, squash-merged as `3db24817`; exactly fetched source and test blobs matched GitHub blob SHAs, isolated NumPy/unittest 10/10 passed. Does **not** qualify integrated waveform rendering on Windows.
- **GO for documentation only:** proposed Performance Direction research PR #117, squash-merged as `1720457f`; ADR explicitly remains **PROPOSED**, no engine change or owner approval.
- **SUPERSEDED:** draft PR #119, closed after every original Studio-first/media file was carried into #120. Do not replay #119 independently.
- **HOLD:** draft PR #120, retargeted to `main` as **the single consolidated Studio-first UI + wave background + staged media candidate**, head `444792ac`. Its GitHub `mergeable` flag is NOT an exact-head Windows acceptance receipt. Contains an **unapproved historical** 67-second film and screenshot set requiring replacement.
- **HOLD:** draft PR #113, head `15181c2`, stale in-place narration implementation; requires reconciliation with #120's editor, model-ownership and state semantics, then exact-head Windows acceptance.
- The issue queue is 27 open issues. No issue is automatically closed just because a related document or PR merged.

## Open issue disposition (all 27)

| Priority | Issue | Action, dependencies and completion criteria |
| --- | --- | --- |
| P0 | [#13](../issues/13) Live audio reliability | Measure and remediate **64 underruns in a prior 30-minute mixed soak**; prove cached pad start and audible Stop latencies, unplug/replug recovery and virtual/conferencing routes on actual Windows device. No external-routing release claims until confirmed. |
| P0 | [#61](../issues/61) Windows integrated qualification | Fresh scratch-profile source-run on the **exact combined head**; full Python/Qt suite, keyboard/visual/resize, playback, project save/reopen/export, regression and no user-data writes; report environment and independent failures. Historical `c0fc13b` and #119's 463 tests are NOT exact-head evidence. |
| P0 | [#71](../issues/71) layered composer | Maintain delivered model/timeline/export; rebase/reconcile #113's same-clip narration generation after #120, test undo/cancel/stale result and model exclusivity, long-export bounded memory, wave alignment at varied sample rates. Keep until defined capability outcomes pass. |
| P1 | [#55](../issues/55) current-source provenance | Trace remaining inherited code and dependency source/license boundaries to CURRENT source SHA and real installed dependencies; evidence, owner decisions and notices. |
| P1 | [#57](../issues/57) independence hardening | Replace/reconcile remaining UI/worker lifecycle and inherited adapters only where necessary, supported by exact source map and regression; avoid a gratuitous rewrite. |
| P1 | [#58](../issues/58) brand clearance | Owner/legal verification of Sonic Rift trademark/search/domain collision before commercial public launch; do not conflate selecting a name with clearance. |
| P1 | [#60](../issues/60) repo metadata/licensing | Set stale GitHub description/topics to Sonic Rift, pin Chatterbox `@master` install path consistently with lockfile SHA or document approved reproducible source mechanism, reconcile source rights, THIRD_PARTY_NOTICES, current changelog and packaging notices. Installer/signing remains owner-deferred P4. |
| P2 | [#15](../issues/15) Live epic | Keep as parent tracking #13 acceptance; no duplicate separate Live implementation sprint. |
| P2 | [#29](../issues/29) RVC feasibility | Research-only until real model/weights rights, latency/VRAM and route acceptance on target Windows GPU; no live changer claim. |
| P2 | [#53](../issues/53) roadmap | Track proven composer/Live/product outcomes and milestones, avoid counting research or website media as shipped function. |
| P2 | [#54](../issues/54) product migration epic | Canonical release-blocker overview; this ledger is the current disposition; packaging/Store deferred P4. |
| P2 | [#59](../issues/59) visual/brand polish | Actual wave-background look against owner-selected reference, Studio header/scroll/contrast, light/dark, real screenshots, icon/transparent lockup font consistency. |
| P2 | [#116](../issues/116) Performance Direction | PR #117 docs merged, **proposal only**. No Drama 3 installation, provider auth, schema changes or implementation without separate owner GO; evidence/ADR gate remains. |
| P2 | [#118](../issues/118) site media | Once #120 UI qualified, replace five genuine UI screenshots, poster and 67s no-voiceover click tour with narrator-led 90–105s **Studio construction story**, synthetic Guide/Keeper/Traveler as three *distinct* voice identities, additional **Keeper clone** preserving original, real ocean bed, true playback/export, silent captions/VTT, transcript, checksum/provenance, logo font correction and owner listening/visual sign-off. No publication before approval. |
| P3 | [#34](../issues/34) macOS Apple Silicon | Community evidence only, no unsupported compatibility promise or Windows release blocker. |
| P3 | [#40](../issues/40) Accent Studio parent | Keep gated evidence program; no implementation until owner acceptance of #44 and benchmark rights. |
| P3 | [#41](../issues/41) model/rights matrix | Research: verify engine accent capabilities and licenses, evidence feeding #44. |
| P3 | [#42](../issues/42) corpus/consent taxonomy | Research: region/language semantics and allowed/consented speech fixtures. |
| P3 | [#43](../issues/43) local accent benchmark | Prior 56-clip protocol is **not executed**; collect real local audio plus qualified listener evidence before claims. |
| P3 | [#44](../issues/44) owner GO/NO-GO | Explicit decision on #40 based on #41–43/#50–52 and benchmarks; blocks #45–48. |
| P3 | [#45](../issues/45) AccentSpec adapters | Blocked pending #44; versioned model contract only after approved. |
| P3 | [#46](../issues/46) accent UI | Blocked pending #44/#45; no new controls before verified engine contract. |
| P3 | [#47](../issues/47) accent persistence | Blocked pending #44/#45; no schema changes without migration safeguards. |
| P3 | [#48](../issues/48) accent regional QA | Blocked pending #44–47 and real listener fixtures. |
| P3 | [#50](../issues/50) phonology methods | Research-only contribution to #44. |
| P3 | [#51](../issues/51) DEFINE feasibility | Research-only: model/rights/source evaluation, no unapproved install/train. |
| P3 | [#52](../issues/52) regional data permissions | Research-only: consent/license for Scottish/French fixtures, no public real-person clones. |

## Consolidated PR dependency graph

1. #115 and #117 are merged to `main`; their merge receipts are separate from Windows source-run acceptance.
2. #120 is the **single UI/media staging PR** inheriting #119; do not merge unvalidated code or publish historical staged media. Windows owner/Claude can qualify it on the exact final commit and obtain explicit merge authorization per current branch policies.
3. #113 has independent in-place generation behavior; reconcile **after #120 UI is qualified** before calling the composer feature complete. Do not silently overwrite editor/new Studio navigation with stale code.
4. #118 media capture follows a verified integrated GUI and must be approved by the owner, including independent synthetic voice auditions and copyright/provenance.

## Next three operational steps

1. **Claude local qualification**: execute full exact-head Windows source-run and visual QA for #120 at realistic display scales, fix behavioral faults, capture final commit receipts. No CI/Actions, use `[skip ci]` and isolated settings/data.
2. **UI integration + #113 reconciliation**: merge qualified #120 when governance permits, rebase #113 and run the in-place generation regression gate separately; fix P0 #13 reliability as a distinct audio acceptance track.
3. **Media recapture after UI GO**: use genuine live UI to produce five or more polished screenshots, narrated multi-voice story, real Studio mix/export, captioned silent version, poster, logo SVG/PNG variants, updated site-ready README/manifest and explicit owner-approved sound/image review. **No website deployment without sign-off**.

## Scope protection

All issue priorities are maintained as previously owner-directed. P4 packaging, MSIX/MSI/signing and Store distribution remain **deferred**, not conditions of source-run Windows alpha acceptance. No branch deletion, secrets handling, unapproved model installation or arbitrary architecture replacement is authorized by this ledger.
