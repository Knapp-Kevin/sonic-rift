# Rebrand audit: Chatterbox-origin code, licenses and risks (#55)

> **Historical research snapshot, 2026-10-13.** Counts, source comparisons, package inventories, model licensing, and recommendations describe the audited revision, **not the current Sonic Rift `main`**. Subsequent implementation includes independent provider #77, core refactors #75/#78/#85/#86, and adopted MOSS soundscape implementation. Review current `docs/upstream-provenance-audit.md`, `THIRD_PARTY_NOTICES.md`, and release issue #61 before treating any result as a live production assertion. No new tests or downloads were performed during this archival integration.

**Status:** audit complete, read-only; nothing was removed, renamed or installed. It extends [../upstream-provenance-audit.md](../upstream-provenance-audit.md) and doesn't replace it. **Not legal advice.**
**Date:** 2026-10-13. **Upstream reference:** `AcTePuKc/Chatterbox-TTS-UI` @ `22460fd` (also present in this repo's history).

| File | Contents |
| --- | --- |
| [audit_file_matrix.md](audit_file_matrix.md) | All 122 tracked files: origin, coupling, KEEP / REFACTOR / RENAME / RETIRE |
| [audit_upstream_diff.md](audit_upstream_diff.md) | Function-level and line-level comparison with upstream |
| [audit_legacy_symbols.md](audit_legacy_symbols.md) | Every "chatterbox" occurrence by category, and what renaming each needs |
| [audit_import_graph.md](audit_import_graph.md) | Module dependency graph, fan-in/out, where upstream code is reached |
| [audit_risks.md](audit_risks.md) | Data-loss, integration, attribution and Windows risks; owner questions |
| [licenses_summary.md](licenses_summary.md) | Package licenses per environment (app and each engine) and attribution inventory |
| [licenses_models.md](licenses_models.md) | Model-weight licenses and commercial use |
| [licenses/](licenses/) | Full per-environment package lists (CSV) |

## Findings

**Provenance**
- **122 tracked files:** 5 byte-identical to upstream, 19 adapted from upstream, 98 original.
- **Upstream `main.py` / `launch_app.py`:** of 83 functions, 41 survive at ≥ 95% similarity and 64 have a counterpart at ≥ 50%.
- **Further than the 2026-10-09 audit found:** upstream code also survives in `ui/pages/player.py`, `model_loading.py`, `generation.py`, `generate.py`, `model_settings.py`, `ui/widgets.py` and `app.py` (upstream `launch_app.py`, 92% similar).
- **Git history under-reports provenance:** files split out of `main.py` show the fork author as their creator.
- **Installers and launchers are upstream with tiny edits:** `setup_env.*` differ by 4 lines each, `run.*` by 1, and `scripts/install_torch.py` adds 15 lines.
- **Attribution therefore stays required:** keep the root `LICENSE` notice word for word and the README acknowledgements, and add the owner's own notice beside them rather than rewriting them.

**Coupling that matters for the refactor (verified in code)**
- **`ui/threads.py:77` and `ui/pages/model_loading.py:27,151`:** if `chatterbox-tts` fails to import, **every engine** refuses to load (Qwen, Kokoro, VoxCPM2…), not just Chatterbox. `threads.py:87` also logs "Attempting to load Chatterbox model" for every engine.
- **`ui/main_window.py:96`:** outputs go to `os.getcwd()/chatterbox_outputs`, not the project root that all other data uses. Starting from another directory can create a second output folder.
- **249 "chatterbox" occurrences in 53 files:**
  - **Runtime names a rename would touch (13):** the output folder, the `chatterbox_` file prefix, the `CHATTERBOX_INSTALL_LOG` variable and the misleading log line.
  - **No settings key contains "chatterbox"**, so settings need no migration.
  - **The Chatterbox engine identity (Resemble AI) stays.**
- **The window title is hard-coded:** `scripts/restart_app.py` finds the app by the exact title "This Voice Thing". A rename must change it together with `APP_NAME` (4 places plus 1 test), or graceful restarts fall back to a force-kill, which loses settings.
- **Import structure is clean:** 62 modules, no cycles, and `core`, `engines` and `integrations` never import `ui`. 32 modules don't touch upstream-derived code at all.

**Licenses**
- **VoxCPM environment: `kaldiio 2.18.1` ships an NTT evaluation-only license** (no redistribution, evaluation use only). It arrives via `voxcpm` → `funasr` and is never used by the app. Candidate fixes: pin an older MIT release, or install `voxcpm` without `funasr`. Both are untested.
- **Main app process:**
  - `praat-parselmouth` (via the Perth watermarker) and `pykakasi` (via chatterbox-tts) are **GPL-3.0**.
  - **PySide6 is LGPL-3.0.** It's fine as pip-installed; it matters if a bundled installer is ever shipped.
- **Kokoro environment:** GPL-3.0 espeak-ng and phonemizer components.
- **Model weights:**
  - OmniVoice is **CC-BY-NC-4.0** (non-commercial).
  - VibeVoice is MIT, but its card says **research use only**.
  - Chatterbox, Kokoro, VoxCPM2, Qwen3-TTS and Whisper allow commercial use, which matches the app's license badges.

## Recommendation for #57 (refactor), in order

1. Remove the `CHATTERBOX_AVAILABLE` gate for non-Chatterbox engines, and fix the per-engine load log line, with a test (no user-visible rename).
2. Base the output folder on the project root, and make the folder name and file prefix configurable with a **dual-read migration**: list old and new folders, and never move or delete without consent.
3. Rename `ChatterboxApp` behind a compatibility alias. Change title, `APP_NAME` and `restart_app.TITLE` in one commit, or have the restart script import the constant.
4. Rename `CHATTERBOX_INSTALL_LOG` in all three files at once, keeping a fallback read of the old name.
5. Resolve kaldiio in the VoxCPM install before any public "commercial use" claim.
6. Keep upstream-adapted installers and helpers attributed. Renaming doesn't remove derivation.

## Open questions for the owner

1. Do any of your own scripts read `chatterbox_outputs/` or `chatterbox_*.wav`, or rely on the local API's saved-file paths?
2. New output folder name and file prefix (depends on #58), and should existing files be moved, or listed alongside?
3. Fix the `os.getcwd()` output base now?
4. Keep the tagline "Definitely not just Chatterbox UI." and the "Began as a fork…" tooltip? The tooltip doubles as in-app attribution.
5. Rename `ChatterboxApp`, keeping an alias for compatibility?
6. Add your own copyright line to `LICENSE` beside the upstream notice?
7. Delete `docs/screenshots/upstream_original.png`? It's referenced only by the audit docs.
8. Accept or fix the kaldiio evaluation license in the VoxCPM engine?
