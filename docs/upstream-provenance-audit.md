# Upstream Provenance and Legacy Cleanup Audit

Status: **Historical baseline audit (2026-10-09) with a 2026-10-15 mainline reconciliation; not legal clearance or dead-code certification.**

Original audit snapshot: 2026-10-09. Scope: the then-current `main` branch file trees of `Knapp-Kevin/this-voice-thing` and `AcTePuKc/Chatterbox-TTS-UI`. Upstream commit tree: `22460fd99ceb78c309f879b93878240241a0dc9b`. This Voice Thing baseline tree: `17657c653d9bed89f86b526cbae704cf12308d36`.

## Verified findings

- Upstream contains **17 tracked files**, including **4 Python files**. This Voice Thing contains **121 tracked files**, including **78 Python files**. Counts describe architectural expansion, **not** independently authored code share.
- At the **2026-10-09 baseline**, Git object hashes established the following exact upstream payloads. **This table is historical, not an assertion that all entries remain byte-identical on current `main`:**

| Upstream file | Current file | Disposition |
| --- | --- | --- |
| `model_backends.py` | `this_voice_thing/engines/chatterbox_backend.py` | **2026-10-09 only:** identical upstream implementation. **2026-10-15:** replaced by a compatibility re-export facade in #77; see reconciliation below. Retain attribution for other derived code. |
| `requirements.in` | `requirements.in` | **Identical upstream dependency declaration.** |
| `requirements.lock.txt` | `requirements.lock.txt` | **Identical upstream dependency lock.** |
| `LICENSE` | `LICENSE` | **Identical MIT notice. Preserve.** |
| `screenshot_1.png` | `docs/screenshots/upstream_original.png` | **Identical upstream screenshot.** Historical-only; removable if unreferenced, but do not remove attribution for other surviving upstream code. |

- `main.py` shrank from a 76 KB upstream application to a 221-byte entry point; that does **not** prove upstream UI implementation was rewritten. `this_voice_thing/ui/common.py` retains the upstream-style device-selection/bootstrap code near its top; function-level comparison remains open.
- Setup scripts, launchers, and the product README have changed Git hashes, but changed hashes alone do **not** prove independent authorship.
- GitHub reports this repository as an actual fork of `AcTePuKc/Chatterbox-TTS-UI`. Repo metadata may be detached as a separate hosting operation, but that does not extinguish third-party copyrights or the MIT notice requirements.

## Rules for cleanup

1. **Keep MIT and upstream copyright/permission notices** in distributed copies while upstream-origin code or substantial portions remain. New original work may carry its own authorship notice after ownership confirmation.
2. Preserve the **Chatterbox engine identity**, Resemble AI references, and the official model dependency. They describe currently supported functionality, not obsolete UI branding.
3. Keep `chatterbox_outputs/` as a compatibility path until a migration handles existing files, saved configuration and external scripts without data loss.
4. No bulk code deletion or automatic renaming based on the string “chatterbox.” Require a caller/reference scan, tests and migration plan.
5. Distinguish license for the **application source** from each engine's **model weights and their separate terms**.

## Next provenance verification

- Compare upstream `main.py` functions and UI sections against current `ui/common.py`, `ui/main_window.py`, `ui/pages/*`, `ui/threads.py` and `app.py`, including moved/modified blocks.
- Compare upstream `install_torch.py` with `scripts/install_torch.py`; compare both `setup_env` scripts and `run` launchers line by line.
- Identify all code copied or materially adapted from upstream, even where filenames/structures differ. Record file-to-file/function-to-function relationships and licenses.
- Check whether `docs/screenshots/upstream_original.png` is linked in documentation. Only delete it if it is unused and removal serves the project.
- Audit runtime data paths and legacy symbols before any renaming. Add migration/compatibility tests before changing paths.
- Run application unit tests after any cleanup and review the complete diff for retained notices.

## Release decisions

**Current disposition:** independent product branding is appropriate; **upstream attribution remains required** on present evidence. Do not characterize this repository as a clean-room rewrite, remove the original MIT notice, or claim a verified replacement percentage.

**Out of scope for this documentation-only audit:** runtime refactoring, model downloads, hardware tests, GitHub fork detachment, relicensing, and deletion of legacy user data.

## Follow-up function-level audit (2026-10-09)

### Verified surviving executable paths

This audit compared upstream `main.py` with present application components by function/class names and inspected the implementation call sites. **This is evidence of retained adapted code, not a quantitative copyright allocation.**

| Upstream implementation | Current implementation | Runtime evidence | Assessment |
| --- | --- | --- | --- |
| `model_backends.py` entire implementation | `this_voice_thing/engines/chatterbox_backend.py` | **At 2026-10-09 only:** identical blob in active model-load path. **Current:** facade forwards to `engines/chatterbox_provider.py` via the existing `ui/common.py` import. | **Original copied backend replaced in #77; separate provenance review still required for any similar new code.** |
| `main.py::ModelLoaderThread` | `ui/threads.py::ModelLoaderThread` | Shared initializer and CUDA fallback logic; `ui/pages/model_loading.py` constructs the worker | **Adapted upstream code, actively used** |
| `main.py::AudioGeneratorThread` | `ui/threads.py::AudioGeneratorThread` | Retains `stop`, `set_seed_internal`, `run` entry points; `ui/pages/generation.py` imports and uses it | **Adapted upstream generation code; active** |
| `main.py` console/config helper functions | `ui/common.py` | `patched_torch_load`, `configure_console_stream`, `safe_console_text`, `TeeStream`, `read_models_config_payload`, `load_models_config`, `read_json_payload`, `write_json_payload` survive by name and structure | **Relocated upstream-derived logic; individual call-site necessity requires detailed tests before deletion** |
| `main.py::ChatterboxApp` | `ui/main_window.py::SonicRiftApp` (legacy alias `ChatterboxApp`) | Class identity changed in #76; `_init_ui`, settings, logging, window methods persist, alongside substantial redesign. | **Evolved/partly adapted UI; class renaming is not a source rewrite.** |
| Original `main.py` | New 221-byte `main.py` delegating to `this_voice_thing.app.main` | Entry point is replaced, but implementation is relocated into current package | **Entry-point rewrite alone has no implications for upstream-code removal** |

### Product identity versus implementation provenance

**Product conclusion:** Sonic Rift (formerly This Voice Thing) is a distinct, much broader creative-audio workbench with independently expanded capabilities. It need not be described in prominent marketing copy as a Chatterbox UI edition or continuation.

**Code conclusion (updated 2026-10-15):** PR #77 replaced the byte-identical legacy Chatterbox UI backend with a new adapter, preserving model-loading and generation behavior in local real-audio tests. Other identifiable upstream Chatterbox UI-derived implementation remains in the threads, common bootstrap, UI shell, and launch scripts. Do not assert full source independence or remove required notices. The new adapter itself requires authorship/provenance assessment independent of whether it differs in Git hashes.

### Safe cleanup classification

- **Remove/promote out of prominent product copy:** legacy fork-centered branding. Already addressed by the independent-product README work.
- **Retain:** Chatterbox TTS as an optional engine; the now-thin `chatterbox_backend.py` compatibility import facade; legacy output directory, settings migration paths, MIT notice, and accurate upstream attribution in Acknowledgements.
- **Refactor only with behavior tests:** remaining `ModelLoaderThread`, `AudioGeneratorThread`, `ui/common.py` bootstrap helpers, app shell methods, and launcher/installer legacy implementation. The `ChatterboxApp` class was renamed with a compatibility alias in #76; this did not eliminate code derivation.
- **Potentially remove after reference check:** the archived upstream screenshot and redundant history-oriented narrative; neither should be used as evidence that active upstream code is gone.
- **Do not detach as a substitute for attribution:** GitHub fork-network detachment changes hosting metadata, not code origins or obligations.

### Criteria for a future reduced-provenance claim

To assert that original UI runtime code is no longer used, demonstrate all of the following: (1) exact backend replacement or removal, (2) replaced/adjudicated upstream worker and helper functions, (3) comparable full application behavior in automated and local tests, (4) provenance review of startup scripts and UI methods, and (5) preservation of all remaining applicable notices. Even complete rewriting does not transfer third-party authorship or change the licenses of engine dependencies/model weights.

**Audit disposition:** Retain MIT and upstream notices. Distinct product branding is supported. No code deletion or fork detachment is justified merely by codebase growth.

## Mainline reconciliation, 2026-10-15 (after PRs #75, #76, #77, #78, #81)

The dated findings above deliberately preserve what was true at the initial audit commit. For **current status**, rely on these rechecked paths:

| Area | Current mainline implementation | Evidence | Residual disposition |
| --- | --- | --- | --- |
| Chatterbox UI backend | `engines/chatterbox_backend.py` is now a small compatibility import facade; `engines/chatterbox_provider.py` implements the active adapter using published Resemble AI Chatterbox TTS APIs. | #77 merged as `7c16a923`; the facade is no longer the original byte-identical 232-line implementation. | Adapter authorship and any retained adapted structures still need separate source review. Model weights and third-party package licenses remain separate. |
| Model selection | `core/engine_loading.py` owns provider-neutral loading and validation; `ui/threads.py` delegates through it. | #75. | Thread lifecycle and generation code remain to be reviewed/replaced by provenance, not renamed wholesale. |
| CUDA/NVIDIA probes | `core/hardware.py` owns shared hardware detection independently of optional Chatterbox imports. | #78; reused in #77. | Real hardware behavior must be measured on the release commit, as with other engine checks. |
| Window class identity | `ui/main_window.py::SonicRiftApp` is canonical and the old `ChatterboxApp` import is a compatibility alias. | #76. | Much of the implementation remains adapted upstream code. |
| Startup and close | Branding and restart behavior corrected; #81 addresses the exit-code/late-log failure. | #72, #73, #79 and #81. | Entry-point and installer provenance still open. |
| Remaining legacy source | `ui/threads.py`, `ui/common.py`, and portions of UI modules/installers/launch scripts. | Earlier function-level audit and draft #62, which must be reconciled against new main. | Do not issue a clean-room or fully independent-source claim yet. |

**Functional acceptance of #77:** Claude's local Windows test record in [PR #77](https://github.com/Knapp-Kevin/sonic-rift/pull/77) reports V2, V3, and English TTS, with/without voice reference, GPU and CPU, offline cache, existing settings/voice library, output and relaunch. Nine speech clips transcribed without errors in the tested phrases; CPU audio matched bit-for-bit and GPU differences were within measured run variation. The test suite passed locally and no new GitHub Actions were run. A third-party custom fine-tune model was **not** downloaded or validated. These results establish a substantial regression check, not a universal speech-quality guarantee.

**Legal/provenance limitation:** A different file path or a distinct implementation text does not by itself erase obligations for derived code. Preserve the original MIT notice while material remains, and maintain separate dependency/model/artwork license inventories. Any new Sonic Rift-owned code licensing decision belongs to #60, with its own permission and attribution review.

**Follow-up:** revise historical counts and matrices in draft #62 against actual current `main`; do not quietly reinterpret the original 2026-10-09 file totals as 2026-10-15 totals. The delivery/release gate remains #61.
