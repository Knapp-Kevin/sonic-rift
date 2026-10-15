# Sonic Rift: independence, provenance and source licensing decision

**Status:** Proposal for owner decision, **not** a copyright clearance, change of license or approval to detach a fork.

**Repository:** `Knapp-Kevin/sonic-rift`  
**Tracking:** #54 (epic), #55 (provenance), #56 (architecture), #57 (refactor), #60 (license, metadata and packaging), #61 (release gates).  
**Decision already made:** Product brand and repository name are **Sonic Rift**; branding merged in #72. Window-title restart compatibility fixed in #73.

## Desired end state

Sonic Rift is a standalone local-first creative-audio application, with independent application code and architecture, provider-neutral contracts for voice, sound effects, soundscapes, arrangement, and live audio. It must not depend on *Chatterbox TTS UI's implementation*. **Chatterbox TTS may remain an optional engine** under its own license and distribution rules.

"Independent" has three distinct meanings:

1. **Product:** Sonic Rift's user-facing name, artwork, messaging and app UI are its own. Branding is already started.
2. **Code and license:** All application code that originated in `AcTePuKc/Chatterbox-TTS-UI` is inventoried and replaced or licensed with retained notices; third-party engine, model-weight and transitive-dependency terms remain independently binding.
3. **GitHub network:** GitHub still lists this repo as a fork until explicitly detached. Detaching the fork is **not** evidence that source code was rewritten or that notices can be discarded.

These workstreams have separate acceptance criteria.

## Evidence on today's main

The initial [upstream provenance audit](../upstream-provenance-audit.md) identifies an **identical** copied backend at `this_voice_thing/engines/chatterbox_backend.py`, and evolved upstream worker/UI/helper code in `this_voice_thing/ui/threads.py`, `ui/main_window.py` and `ui/common.py`. It explicitly says current code is **not a clean-room replacement**.

An expanded file-level analysis is in draft PR #62, which reports 5 byte-identical files and 19 adapted files at its audited revision. These counts are **historical audit evidence**, not current independent-author percentages or legal conclusions. Reconcile #62 against the current branch before using that ledger to authorize source license changes.

At time of writing the root `LICENSE` is inherited MIT text. **Do not remove or overwrite it based on the product rename.** MIT's permission-and-copyright notice requirement continues for redistributed copies or substantial portions of upstream-derived code. If portions are fully and demonstrably replaced, provenance and distribution still need review; historical Git commits are not retroactively re-licensed.

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

- Replace copied Chatterbox UI backend glue with a Sonic Rift-owned engine adapter that imports the genuine Chatterbox **TTS library**, not implementation copied from the old UI.
- Replace or independently reimplement upstream-derived worker, model-loading and common-helper code. Require feature and parity tests before removing legacy code.
- Extract `ChatterboxApp` into a Sonic Rift application shell after preserving UI behaviors, settings, startup errors, model selection, downloads, output and saved user assets.
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

**Suggested licensing policy:** license the *independently owned source code* separately, with explicit `THIRD_PARTY_NOTICES` and model-license manifests. Do not claim any new license automatically governs prior commits or dependencies. Legal specialist review is appropriate before claiming clean legal separation.

### 5. GitHub fork-network transition: **hold** (#54, #60)

The official [GitHub fork-detachment documentation](https://docs.github.com/en/pull-requests/how-tos/work-with-forks/detaching-a-fork) states that leaving the network preserves Git commit metadata but **does not retain issues, PRs, comments, stars or other repository metadata**, and the operation is irreversible. Current Sonic Rift project management relies on those artifacts. Do **not** detach now.

Before any GitHub-network action:
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
