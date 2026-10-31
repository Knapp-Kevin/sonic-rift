# Sonic Rift: repository hygiene and pre-release work ledger

**Audited:** October 30, 2026 · **Reference code commit:** `f51897cb5a2bfe299aa6c6a0c82c85932c0b3ea0`  
**Evidence:** live GitHub repo/PR/issue/branch inventory, repository source and documentation, not a local Windows execution.  
**Purpose:** define the *current* disposition; the [earlier checkpoint](https://github.com/Knapp-Kevin/sonic-rift/blob/1662d9d852c89cd4ad0963a35f63eb8dce648060/docs/operations/sonic-rift-2026-10-30-repository-hygiene.md) is historical and must not be treated as current. Recompute GitHub truth before each write or release decision.

## Current summary

| Gate | Observed / disposition |
| --- | --- |
| Open PRs | **0** after PRs #113, #120–#125 (where applicable) merged |
| Open issues | **26**: 3 P0, 4 P1, 6 P2, 13 P3 |
| Git branches | **59** total at audit start: `main` + **58** other refs; this document's working branch adds one temporary hygiene ref |
| Branch proof | **52** non-main refs are heads of *merged* PRs; **2** correspond to closed-unmerged PRs; **3** older refs have no matching PR from the fetched PR inventory |
| Published GitHub releases | **0**; source-run application and marketing files are not a published installer |
| Approved marketing assets | owner approved October 30 via #123; #118 **closed**. Website prototype integration is a separate task and was not completed in this source-repo audit |
| Integrated runtime | PR #124 audio reliability merged `a210908`; PR #125 PyTorch loader isolation merged `f51897c` |
| Combined Windows exact-head qualification | **OPEN #61**: individual Windows test receipts do *not* constitute a fresh full test on their combined merged SHA |
| Release and license rights | **OPEN #55/#57/#58/#60**: inherited source, model/installed package rights, trademark and source-license decision; historical MIT notice retained |

This report does not claim independently rerun Windows tests, resolved vulnerability alerts, fork detachment, or a public-release GO. Windows executable/installer/Store and signing **implementation** remain owner-deferred P4. The signing instructions in #121 are not a signed build.

## Active issue disposition

| Priority | Issue(s) | Keep open until |
| --- | --- | --- |
| **P0** | [#13](https://github.com/Knapp-Kevin/sonic-rift/issues/13) Live reliability | VoxCPM2 cold rebuffering, device-loss/recovery, virtual mic/Discord/Zoom/OBS and owner listening are addressed or documented with explicit scoped exclusions; do not reintroduce the obsolete first-line 0.30 s artifact without new evidence |
| **P0** | [#61](https://github.com/Knapp-Kevin/sonic-rift/issues/61) exact merged-head Windows acceptance | Full tests and real Studio/Voices/Speech/Live/source-run smoke on `f51897cb5a2bfe299aa6c6a0c82c85932c0b3ea0` or later, protected owner data and documented untested hardware/engines |
| **P0** | [#71](https://github.com/Knapp-Kevin/sonic-rift/issues/71) Studio composer | #113's in-place narration is **merged**; timeline zoom/navigation/loop-region transport and streaming, bounded-memory long-project export are still required |
| **P1** | [#55](https://github.com/Knapp-Kevin/sonic-rift/issues/55) provenance and rights | Current function-level lineage, installed dependencies/weights and precise retain/replace/notice decisions |
| **P1** | [#57](https://github.com/Knapp-Kevin/sonic-rift/issues/57) source independence | #125 global torch hook **removed**; inherited Qt worker/bootstrap/window/launcher logic requires staged parity-backed replacement, not cosmetic renaming |
| **P1** | [#58](https://github.com/Knapp-Kevin/sonic-rift/issues/58) branding clearance | Owner/legal trademark/domain collision review. Selecting the Sonic Rift name is not legal clearance |
| **P1** | [#60](https://github.com/Knapp-Kevin/sonic-rift/issues/60) metadata/license/dependencies | Align stale GitHub repo description/topics, investigate floating `chatterbox-tts @ ...@master` input versus pinned `requirements.lock.txt`, current notices and ownership license. No unapproved fork detach |
| **P2** | [#15](https://github.com/Knapp-Kevin/sonic-rift/issues/15), [#53](https://github.com/Knapp-Kevin/sonic-rift/issues/53), [#54](https://github.com/Knapp-Kevin/sonic-rift/issues/54) epics/roadmap | Parent navigation and explicit owner program acceptance, not duplicate P0 bug tickets |
| **P2** | [#29](https://github.com/Knapp-Kevin/sonic-rift/issues/29) RVC research | Feasibility and permitted dependencies/models, no implied real-time changer release |
| **P2** | [#59](https://github.com/Knapp-Kevin/sonic-rift/issues/59) optional brand/UI polish | Approved media and icons are delivered; verify remaining accessibility/light/dark/splash scope or close once owner accepts optional leftovers as deferred |
| **P2** | [#116](https://github.com/Knapp-Kevin/sonic-rift/issues/116) Performance Direction | #117 is an **ADR/research proposal**, not deployed Drama 3 capability |
| **P3** | [#40–48](https://github.com/Knapp-Kevin/sonic-rift/issues/40), [#50–52](https://github.com/Knapp-Kevin/sonic-rift/issues/50) accent program | 12 separately-scoped gated research/implementation tickets; do not implement #45–48 before #44 owner GO and source/weight/consent evidence |
| **P3** | [#34](https://github.com/Knapp-Kevin/sonic-rift/issues/34) Apple Silicon | Community-only platform exploration, not a Windows release blocker |

**No issue closed in this audit:** all 26 retain documented unmet or optional owner-approved scope. #118 was already completed and closed.

## Branch hygiene: decision and safeguards

The historical branches are significant provenance evidence. GitHub's squash merges do not put the old branch HEAD itself into `main`; match by **merged PR metadata**, not by `git merge-base --is-ancestor` alone.

At the audit starting point:

- **52 merged-PR branches** are archival-delete candidates *after* a repository backup and after ensuring no active worktree, cross-repo dependency, release tag or needed unmerged commit references them. The completed PR metadata and commit SHAs remain addressable even after branch deletion. Do not delete automatically from a PR title alone.
- **2 closed-unmerged PR branches:** `docs/source-provenance-checkpoint-20261016`, `refactor/torch-load-compat-boundary`. Retain pending an explicit disposition of #91's superseded torch compatibility design and #112's provenance evidence.
- **3 non-main branches without a matching fetched PR:** `audit/pre-release-source-independence-20261030-no-ci`, `feat/journey-nav`, `hardening/rvc-requirements-boundary`. Audit individually; the independence audit has one unique documentation commit, the RVC boundary has two unique commits, and `feat/journey-nav` has no commits ahead of `main` per Git compare. Do not conflate unmerged with unused.
- **`chore/repository-hygiene-refresh-20261030-no-ci`** is the current documentation-only hygiene branch. Dispose of it after its PR is merged and the records are preserved.

**Merged PR branches in the candidate group (52):**

- `audit/upstream-provenance-inventory` (#37)
- `audit/upstream-runtime-provenance` (#38)
- `chore/installed-license-inventory` (#102)
- `chore/public-identity-attribution-boundary` (#84)
- `chore/reproducible-source-lineage-audit` (#100)
- `design/sonic-rift-brand-identity` (#72)
- `docs/accent-studio-research-2026-10-10` (#49)
- `docs/current-architecture-boundaries-20261016` (#106)
- `docs/independent-project-positioning` (#36)
- `docs/performance-direction-drama3-20261018` (#117)
- `docs/platform-system-requirements` (#35)
- `docs/provenance-startup-refactor-reconciliation` (#87)
- `docs/rebrand-audit-audio-studio-phase0` (#62)
- `docs/reconcile-provenance-after-provider-merge` (#82)
- `docs/sonic-rift-independence-license-decision` (#74)
- `feat/audio-create-project-editor` (#99)
- `feat/audio-project-edit-session` (#98)
- `feat/audio-project-export-bundle` (#97)
- `feat/audio-project-media-resolver` (#96)
- `feat/audio-project-mixer-core` (#94)
- `feat/audio-project-schema-v1` (#93)
- `feat/audio-project-speech-ducking` (#95)
- `feat/audio-studio` (#69)
- `feat/editor-generate-narration` (#113)
- `feat/live-voice-qa` (#24)
- `feat/project-timeline` (#103)
- `feat/sonic-rift-app-icon` (#83)
- `feat/timeline-drag-trim` (#111)
- `feat/ui-cohesion` (#101)
- `fix/clean-exit-code` (#81)
- `fix/explain-long-project-export` (#110)
- `fix/kokoro-smart-app-control` (#80)
- `fix/live-format-switch-queue` (#108)
- `fix/live-rebuffer-after-underrun` (#104)
- `fix/live-reliability-13` (#124)
- `fix/perth-watermark-inference-mode` (#39)
- `fix/restart-sonic-rift-window-title` (#73)
- `fix/sonic-rift-name-leftovers` (#79)
- `fix/tab-leaves-text-boxes` (#109)
- `fix/test-settings-isolation` (#89)
- `fix/timeline-ruler-envelope-long-sessions` (#105)
- `fix/voxcpm-numba-free-audio` (#88)
- `fix/waveform-nondivisible-rate-20261016` (#115)
- `integrate/live-voice` (#92)
- `refactor/console-core-isolation` (#86)
- `refactor/core-hardware-probe-independence` (#78)
- `refactor/engine-scoped-torch-loading-20261030-no-ci` (#125)
- `refactor/independent-chatterbox-provider` (#77)
- `refactor/independent-config-io` (#85)
- `refactor/provider-neutral-model-loader` (#75)
- `refactor/sonic-rift-app-shell-identity` (#76)
- `tools/archive-fork-metadata-read-only` (#90)

This tool session did **not** delete any branch: no authenticated branch-delete action is exposed. A subsequent authorized cleanup must re-enumerate branch heads and confirm safe disposal before deleting.

## Dependency, security and public metadata

1. **Floating direct dependency:** `requirements.in` currently uses `chatterbox-tts @ git+https://github.com/resemble-ai/chatterbox.git@master`, while `requirements.lock.txt` fixes commit `65b18437192794391a0308a8f705b1e33e633948`. Both Windows and POSIX setup scripts can **recompile the lockfile when the input appears newer**. Avoid an unreviewed upgrade during routine installs. Stage a separate minimal pin or verified lock/installer consistency change, tested with `uv` and offline/Windows acceptance; do not modify environments or Python versions as part of documentation hygiene.
2. **Security alerts not certified:** repository API access here did not expose private Dependabot/code-scanning alert endpoints. This report is **not** evidence of zero vulnerabilities. Review GitHub Security alerts with authorized repo access; document affected packages/versions, exploitability, false positives and source/weight license implications. No auto-bump of CUDA, Torch or isolated engines.
3. **Public GitHub repository fields are stale:** description still starts `This Voice Thing` and the topics emphasize `chatterbox`. Suggested accurate description: **“Sonic Rift: local-first Windows creative audio studio for speech, voice design, soundscapes, timeline mixing and live output.”** Use current app-capability topics; retain Chatterbox as a documented *provider*, not the parent product identity. GitHub fork relationship/rights need a separate owner decision.
4. **Documentation fixed in this hygiene branch:** `Readme.md` current Studio narration, Live and release gates; `CHANGELOG.md` current product identity and integrated milestones; this ledger. Avoid changing Windows runner workflows merely to make a hygiene check green.
5. **Marketing approval is not website deployment:** approved `docs/marketing` remains on `main`; no media regeneration or website changes belong in this repository hygiene work.

## Next actions and ownership

1. **Review/merge the documentation-only hygiene PR**. Verify its links, markdown, source SHA and file diff; no Actions required.
2. **Claude (Windows) or authorized local developer:** validate the combined `main` regression #61, then qualify a narrow reproducible dependency pin/lock parity PR under #60. No new downloads or owner profile writes without approval.
3. **Owner/GitHub admin:** verify private security alerts and update the repository description/topics; archive or delete only the verified 52 merged branches after recording heads and confirming no active worktrees. Keep the five exceptional branches until separately disposed.
