# Sonic Rift | Pre-release UI source-independence audit

**Status:** SOURCE-ONLY ASSESSMENT · DO NOT INTERRUPT DEMO · NOT RELEASE/LEGAL CLEARANCE  
**Recorded:** 2026-10-30  
**Sonic Rift baseline:** `main` `1662d9d852c89cd4ad0963a35f63eb8dce648060` (does **not** incorporate active consolidated UI draft #120)  
**Historical Chatterbox TTS UI reference:** `AcTePuKc/Chatterbox-TTS-UI` `22460fd99ceb78c309f879b93878240241a0dc9b`  
**Owner's objective:** Initial release should use independently maintained Sonic Rift application UI, worker and startup implementations, with original Chatterbox TTS retained only as an optional external speech engine where appropriate, and licensing/notice obligations accurately scoped.

## Current execution boundary

**DEMO FIRST.** Claude is finishing real voice evaluation, the Windows regression suite and a revised, narrator-led, multi-voice marketing demonstration on the Studio-first UI branch. This assessment lives on a **separate audit branch**. It must not change `main`, #120, #113, active Windows worktrees, any media fixture, installed engine, model cache, data directory, or GitHub Actions configuration. Do **not** create another refactor PR or request integration while the demo acceptance window is active.

No runtime code changed in this branch. All findings must be reconciled against the final qualified post-demo integration SHA before implementation.

## Verified source observations at the stated baseline

- GitHub still identifies the repository as a fork of `AcTePuKc/Chatterbox-TTS-UI`. The repository's description still says *This Voice Thing* and refers to Chatterbox UI, despite the app and README identifying as **Sonic Rift**.
- Upstream tree has **17 tracked blobs**, Sonic Rift main has **283 tracked blobs**. **Only two current Git blobs have byte-identical upstream counterparts**: the upstream MIT `LICENSE` and `docs/screenshots/upstream_original.png`. These counts establish object identity, **not** independence, authorship share, or copyright clearance.
- Upstream `main.py` contains `ModelLoaderThread`, `AudioGeneratorThread`, `ChatterboxApp`, and the import-time `torch.load` patch. Sonic Rift retains `ModelLoaderThread` and `AudioGeneratorThread` in `this_voice_thing/ui/threads.py`. Those workers retain older naming and behavioral heritage; audit bodies and execution paths, not just symbols.
- The **process-global PyTorch patch is an exact surviving source span**: both upstream `main.py` and current `this_voice_thing/ui/common.py` define `patched_torch_load`, choose a default `map_location`, and assign `torch.load = patched_torch_load`. This remains active import-time behavior. It is a high-risk runtime and provenance hotspot, not a safe cosmetic deletion.
- `this_voice_thing/ui/main_window.py` now defines `SonicRiftApp`, provider-aware page mixins and the independent application navigation, but still exports `ChatterboxApp = SonicRiftApp` for compatibility. The alias by itself is not a copy-of-class proof and should not be removed until consumers are accounted for.
- The former copied `chatterbox_backend.py` is now a compatibility facade delegating to the provider-specific implementation; prior PR #77 recorded Windows Chatterbox engine acceptance. This is useful architectural progress, but it does **not** independently clear UI/workers.
- `scripts/install_torch.py`, `run.bat`, `setup_env.bat` and shell launch scripts retain an upstream ancestry review requirement. Treat dependency setup and backward-compatible application folders as correctness and data-migration concerns.
- `THIRD_PARTY_NOTICES.md`, `docs/source-lineage-current.md`, `docs/sonic-rift-independence-licensing-decision.md` and `scripts/audit_source_lineage.py` are already present. These inventories distinguish historical/adapted source and external engine/model obligations. Reuse them rather than launching a parallel uncoupled legal spreadsheet.
- The Sonic Rift `LICENSE` still carries the historical upstream MIT notice. The intended new source-license scope is **not yet selected or owner-approved**.

## Treatment of the owner's pre-release assertion

No general executable release has been reported. That means current source boundaries can be resolved **before the first planned release artifact** and before packaging/installer work (already deferred). However, source has already existed in a public fork, and historical copies/public Git revisions are not retroactively changed by a rewrite. Present and future notices depend on what code, assets, packages and substantial derived material actually remain in distributed source/release artifacts, not solely a project age or name change.

**Target:** remove substantive upstream-UI-derived implementation from the *current application deliverable*, retain rights evidence and the applicable historical/third-party notice archive, then decide precise license and attribution scope with competent review. Do not claim that replacing all byte-identical files clears all obligations. The separate optional **Resemble AI Chatterbox TTS engine** and other installed model/weight licenses must be assessed regardless of UI ancestry.

## Post-demo engineering plan, in dependency order

| Slice | Current boundary / risk | Proposed independent Sonic Rift component | Proof of completion |
| --- | --- | --- | --- |
| A · Lineage | `ui/threads.py` workers, `ui/common.py` bootstrap, `main_window.py`, adapted page helpers, launchers | Function-by-function old-to-new source/control-flow map with `copy/adapted/owned/ambiguous` and authored evidence; record responsible notice and proposed action | Audited mapping tied to exact post-demo SHA and historical upstream commit; all disputed files still marked unresolved |
| B · Startup | Global `torch.load` monkeypatch and import-time console/NLTK/download effects in `ui/common.py` | Explicit, engine-scoped model-loading context and intentional startup service initialization. No process-wide monkeypatch of `torch.load` | Real Chatterbox/Qwen/Kokoro/VoxCPM/multi-engine GPU and CPU model-load parity; `torch.load` object remains unchanged across import; no background network downloads without consent |
| C · Workers | `ModelLoaderThread`, `AudioGeneratorThread` retain adapted generation/lifecycle behavior | Owned provider-neutral task orchestration with explicit model ownership, cancellation, progress, sequencing and immutable result/copy semantics; Qt adapter remains thin and familiar | Model-switch, repeated generate, concurrent generation refusal, cancel/Stop, stalled worker, exception handling, missing model, memory cleanup and exact audio-output parity on Windows |
| D · Window / widgets | Large `SonicRiftApp` mixin class and evolved older UI methods | Owned thin composition root, independently maintained navigation/state controllers and shared Qt presentation components; do not rewrite the functioning timeline merely for file-count aesthetics | Studio/Speech/Sounds/Voices/Live routes, focus, light/dark, scaling, keyboard, saved settings, unsaved project and device lifecycle regression, compared to accepted video/UI reference |
| E · Entry points | `ChatterboxApp` alias, `this_voice_thing` package namespace and historical output folders | Explicit documented compatibility shims with deprecation/migration tests, only then optional naming cleanup | No orphaned recordings/voices/project files, no broken CLI/launcher scripts, and rollback of any migration; don't conflate engine name with upstream UI |
| F · Setup | `install_torch.py`, Windows/shell launch and environment setup | Independent, reproducible Sonic Rift bootstrap pinned to reviewed source/lock state | Fresh scratch Windows installation and offline fallback/repair; model license/weight consent, exact Python/torch versions, error messages, startup and user-profile isolation |
| G · Rights/metadata | Upstream MIT root notice, incomplete owned-source license, public fork and legacy GitHub description/topics | Clearly scoped owned-source license and complete dependency/model/asset notices; optional GitHub metadata refresh as authorized | Owner license decision, expert review of current distribution contents, full notice provenance, accurate public description and no unapproved irreversible fork-detachment |

**Architecture principle:** do not introduce a new framework, job scheduler, message bus, plugin manager or provider abstraction for its own sake. Reuse existing `core/engine_loading.py`, provider adapters and stable Qt signal boundaries. Replace real inherited logic where required; avoid expensive rewrites of independently authored, already-tested components.

## Acceptance and non-regression protocol

For **each** post-demo slice:
1. Start from a fresh, **verified** integrated UI/voice demo SHA; create a separate worktree and feature branch. Record source-to-source provenance and whether any derived code still remains before editing.
2. Make one focused replacement with a documented interface contract; retain required engine names, output locations, project schema and user-data semantics.
3. Run pure-unit adversarial tests first, then the full **exact-head** Python/Qt suite in a disposable Windows profile. Run a model-matrix smoke test and audio reference comparison where the touched code affects generation.
4. For startup/worker changes, test multiple sequential engine loads, GPU fallback, model failures, audio generation, cancel/Stop, active work during app shutdown and absence of global side effects. Evaluate user-facing audio/latency, not just CI.
5. Require owner acceptance for any behavior-changing UI revision, especially while marketing footage is pinned. If a slice affects filmed behavior, schedule a conscious media delta review rather than silently invalidating assets.
6. Update `#55` provenance, `#57` replacement tracking, `#60` licensing/metadata and `#61` Windows acceptance with the same exact head receipt. Never close them on a structural diff or test count alone.

## Exit definition before initial release

- All **active, substantial** Chatterbox-TTS-UI-derived application code is either independently replaced with evidence or retained with correctly scoped license/notice and an explicit owner decision; ambiguous ancestry resolved rather than hidden by renaming.
- Chatterbox **TTS engine** optional integration remains functional on a real Windows setup; its separate license and model terms are honored.
- No process-wide hidden PyTorch loader patch; no unconsented boot-time downloads or global state mutations.
- Clean, native Sonic Rift UI and task architecture are demonstrably maintainable; program remains launchable, reliable, reversible and safe with existing saved user data.
- Rights and distribution notices reflect the **actual** first release contents. Owner has approved the owned-source license and public-repo/fork decision. No false claim of retroactive license cancellation.
- Demo assets have their own approval trail. **The already-in-progress demo is not a dependency of this assessment and must not be delayed for this work.**

## Next action and HOLD

Wait for Claude's current demo and exact-head test receipt **before** touching application code. Refresh this ledger against the accepted integrated commit, then implement **slice B first** (startup global-hook isolation) with adversarial tests, followed by slice C. Project/PR #120, current audio tracks and recorded marketing media are explicitly **out of scope** while the demo is underway.

**This branch is a safe audit artifact, not a PR or instruction for Claude to stop, repeat his captures or change his active work.**
