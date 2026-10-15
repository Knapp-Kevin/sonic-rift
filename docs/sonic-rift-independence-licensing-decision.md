# Sonic Rift: independence, provenance and source licensing decision

**Status (updated 2026-10-15):** Living decision register, **NOT an approved owned-source license, copyright clearance or GitHub fork-detachment authorization**. Implementation steps already merged are recorded as factual progress; remaining decisions and release gates stay open.

**Repository:** `Knapp-Kevin/sonic-rift`  
**Tracking:** #54 (epic), #55 (provenance), #56 (architecture), #57 (refactor), #60 (license, metadata and packaging), #61 (release gates).  
**Decision already made:** Product brand and repository name are **Sonic Rift** (#72). The app icon (#83), user-facing identity/retained notices (#84), and window/restart/taskbar fixes (#73/#76/#79) are merged. The social preview was uploaded by the owner. Live Voice #24 is not integrated.

## Desired end state

Sonic Rift is a standalone local-first creative-audio application, with independent application code and architecture, provider-neutral contracts for voice, sound effects, soundscapes, arrangement, and live audio. It must not depend on *Chatterbox TTS UI's implementation*. **Chatterbox TTS may remain an optional engine** under its own license and distribution rules.

"Independent" has three distinct meanings:

1. **Product:** Sonic Rift's user-facing name, artwork, messaging and app UI are its own. Branding is already started.
2. **Code and license:** All application code that originated in `AcTePuKc/Chatterbox-TTS-UI` is inventoried and replaced or licensed with retained notices; third-party engine, model-weight and transitive-dependency terms remain independently binding.
3. **GitHub network:** GitHub still lists this repo as a fork until explicitly detached. Detaching the fork is **not** evidence that source code was rewritten or that notices can be discarded.

These workstreams have separate acceptance criteria.

## Evidence on today's main

The [dated upstream provenance audit](upstream-provenance-audit.md) initially identified a byte-identical copied backend. **PR #77 has since replaced its implementation** with a Sonic Rift provider adapter; the old `chatterbox_backend.py` path is now a compatibility facade. Real Chatterbox English/V2/V3 audio tests on Windows support the functional acceptance of that specific replacement. Evolved upstream worker/UI/helper code still exists in `ui/threads.py`, `ui/main_window.py`, startup/install scripts and portions of `ui/common.py`. Current source is **not fully independently authored or legally cleared**.

An expanded file-level analysis is in draft PR #62, which reports 5 byte-identical files and 19 adapted files at its audited revision. These counts are **historical audit evidence**, not current independent-author percentages or legal conclusions. Reconcile #62 against the current branch before using that ledger to authorize source license changes.

As of this 2026-10-15 reconciliation, the root `LICENSE` is inherited MIT text. **Do not remove or overwrite it based on the product rename.** MIT's permission-and-copyright notice requirement continues for redistributed copies or substantial portions of upstream-derived code. If portions are fully and demonstrably replaced, provenance and distribution still need review; historical Git commits are not retroactively re-licensed.

## Recommended implementation sequence

### 1. Build a function-level provenance ledger (#55)

Inventory relevant upstream implementation, its location in the current product, authorship evidence and each dependency/model license. Record for each surviving block:

| Column | Meaning |
| --- | --- |
| Origin | upstream file/commit and corresponding current function or asset |
| Status | exact copy / adapted / independently authored / ambiguous |
| Runtime use | entrypoint and call sites, including import-time behavior |
| Remedy | replace / retain with notice / remove as unused |
| Evidence | review, hashes, diff, tests and model/third-party license references |
| Exit | evidence-backed finding that the block no longer appears in distributed app code, or that its license is correctly honored |

Include launcher, install scripts, model-adapter glue, audio threads, UI shell, tests and assets; scan with attribution-safe methods, not only class or file-name matches. Preserve the original evidence outside any file being replaced.

### 2. Execute provider-neutral refactor slices (#56, #57)

- **Delivered (#77):** replace the original copied Chatterbox UI backend with a Sonic Rift provider adapter around the genuine Chatterbox **TTS library**, with local Windows functional-parity evidence. Authorship/provenance assessment of retained structural similarities remains separate.
- **Partially delivered (#75/#78/#85/#86):** provider-neutral model loading and hardware checks, independent Qt-free JSON config I/O, and independently structured console forwarding. **Not finished:** Qt model/generation workers, torch startup and config normalization, window methods and installers. Draft #91 proposes a torch compatibility boundary but is **not merged** and requires Windows GPU/CPU model-loading validation.
- **Partially delivered (#76):** `SonicRiftApp` is the canonical class with a legacy import alias. Renaming did not replace all adapted UI implementation. Preserve UI behaviors, settings, startup errors, model selection, downloads, output and saved user assets as functional acceptance requirements.
- Keep `this_voice_thing` import entrypoints and `chatterbox_outputs` data paths as documented compatibility shims until tested migrations and rollback evidence permit retirement. A package rename alone does not establish independence.
- Independently adversarially review each slice's provenance, failure paths and regression evidence. Do not equate CI success with release readiness.
- No new metered CI workflows, model downloads, or remote release/deploy as part of planning.

### 3. Validate **all** non-code licensing separately (#55, #60)

Reconcile runtime dependency and model-weight license scans. Draft PR #62 flags noncommercial/research-only model weights and transitive-library concerns; later issue comments report that unused `funasr`/`kaldiio` were removed from the VoxCPM environment. **Re-verify** against current pinned environments rather than reproducing outdated warnings as active blockers.

Separate licenses for:
- Sonic Rift's **original source code**,
- inherited code still present (if any),
- external engine packages and dependencies,
- model weights and runtime inference terms,
- art, fonts, example audio and model outputs where applicable.

An independent application can **use** third-party engines while complying with their licenses; it cannot disregard those licenses simply by changing its GitHub fork status.

### 4. Select Sonic Rift's owned-source license (#60)

**No license change is made by this document.** The owner must decide if Sonic Rift should permit redistribution and commercial modifications or keep proprietary product features.

| Candidate | Advantages | Tradeoffs |
| --- | --- | --- |
| **Apache-2.0** (provisional recommendation **if** open source is the goal) | Permissive, commercial use possible, express patent grant | Requires preserving notices; not a substitute for third-party license checks |
| **MIT** | Familiar, minimal obligations, commercially permissive | Weaker explicit patent provisions and competitors may redistribute modified code |
| **MPL-2.0** | Source availability for modified covered files while allowing larger combined works | File-level copyleft and greater compliance complexity |
| **Proprietary for Sonic Rift-owned modules** | More control over commercial distribution | Requires careful separation of owned and third-party source; public code already published under previous grants cannot be retroactively unlicensed |

After decision: determine rightsholders and contributor authority, document SPDX/NOTICE boundaries, apply new license only where rights permit, review model-weight terms, inspect release bundles, and then update root license/NOTICE only with correct scope.

**Suggested licensing policy:** license the *independently owned source code* separately, with existing [third-party notices](../THIRD_PARTY_NOTICES.md) and future release-specific model/dependency license manifests. Do not claim any new license automatically governs prior commits or dependencies. Legal specialist review is appropriate before claiming clean legal separation.

### 5. GitHub fork-network transition: **hold** (#54, #60)

The official [GitHub fork-detachment documentation](https://docs.github.com/en/pull-requests/how-tos/work-with-forks/detaching-a-fork) states that leaving the network preserves Git commit metadata but **does not retain issues, PRs, comments, stars or other repository metadata**, and the operation is irreversible. Current Sonic Rift project management relies on those artifacts. Do **not** detach now.

Before any GitHub-network action, follow [the preservation runbook](github-fork-detachment-preservation.md), introduced in #90. The archive utility is **available but has not been run against the live account**, and issue/PR identities cannot be losslessly restored.
1. Explicit owner approval of losing the original issue/PR network, or a vetted archival/reconstruction alternative with checked completeness.
2. Export and independently verify issues, PR review discussions, comments, labels, milestones and release refs before irreversible action.
3. Preserve original Git commits, source notices, and full reproducibility/rollback procedures.
4. Confirm the exact fork eligibility and destructive consequences in GitHub's current settings.
5. Choose a maintenance window and separately authorize execution. **No automatic detachment under this decision record.**

## Acceptance criteria

- [ ] File/function provenance ledger reconciled against **current main**, with no unresolved active Chatterbox-UI-derived source for a claimed source-independent release.
- [ ] Provider-neutral application shell and adapters implemented; real speech engines and soundscape flows smoke-tested, including when Chatterbox TTS is unavailable.
- [ ] No data loss on old recordings, voices, project files or settings; supported migrations and rollback paths verified.
- [ ] Source, dependency, model-weight and artwork license inventory reviewed; all applicable notices retained.
- [ ] Owner selects and explicitly approves the license of **owned** code; correct repository and distribution notices applied.
- [ ] Fork-network decision and issue/PR retention risks accepted explicitly, or detachment deferred without falsely claiming hosting independence.
- [ ] Tests performed locally within action-budget constraints; release evidence gathered; owner GO/NO-GO recorded.

## Non-goals

- Deleting license text or Git history to make authorship look cleaner.
- Replacing or removing Chatterbox **TTS** solely because Chatterbox **UI** was the ancestor.
- Wholesale rename of runtime paths or package folders in a visual branding PR.
- Claiming a completed legal or architectural separation before measured evidence.

## Current delivery blockers (October 15, 2026)

| Lane | Mainline / evidence | Still required |
| --- | --- | --- |
| Desktop branding | #72/#73/#76/#79/#83/#84 merged; icon and UI text established | Pinned taskbar shortcut and packaged executable icon on the final Windows build (#59/#61) |
| Speech providers | Chatterbox #77, Kokoro Windows Smart App Control #80 and VoxCPM Numba-free audio #88 merged | Full exact-head multi-engine Windows release smoke; optional research-only/noncommercial distribution checks |
| Source independence | Provider boundary #75/#78, config #85, console #86 merged; audit reconciled #82/#87 | Adapted UI/threads/installers; draft #91 runtime validation and licensed-source provenance (#55/#57) |
| Live Voice | Major implementation and Windows QA evidence retained in #24; fixes integrated separately | Resolve stale branch against current main, independent review, exact integrated Windows device/soak tests and actual merge (#13/#15) |
| Finished Audio Studio | Sounds, model management and asset library delivered | Layered project timeline/composer #71 is still not implemented; final ocean pilot browser playback check #68 |
| Repository licensing/network | THIRD_PARTY_NOTICES index #84 and fork metadata archiver/runbook #90 merged | Rights inventory, owner source-license decision, tested private archive and owner approval for any irreversible detachment |

**Management rule:** acceptance documentation can be merged as an evidence-based register without treating any pending owner decision as approved. Close implementation issues only when their conditions have genuinely passed, and keep draft/blocked PRs separate from released app capability.
