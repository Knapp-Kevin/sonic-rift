# Rebrand / refactor risks and open questions (issue #55)

> **Historical research snapshot, 2026-10-13.** Counts, source comparisons, package inventories, model licensing, and recommendations describe the audited revision, **not the current Sonic Rift `main`**. Subsequent implementation includes independent provider #77, core refactors #75/#78/#85/#86, and adopted MOSS soundscape implementation. Review current `docs/upstream-provenance-audit.md`, `THIRD_PARTY_NOTICES.md`, and release issue #61 before treating any result as a live production assertion. No new tests or downloads were performed during this archival integration.

Marking: **[V]** verified from source, git or the owner's working tree (read-only); **[I]** inferred. No legal conclusions beyond: attribution is required while upstream-derived code remains.

## A. User data loss

| # | Risk | Evidence | Mitigation |
|---|---|---|---|
| A1 | Renaming `chatterbox_outputs/` hides or strands generated audio. The player lists only `self.output_directory` (`ui/pages/player.py:76`). | [V] `main_window.py:96`; owner's tree holds 16 files there incl. `previews/` | Dual-read (list both dirs) or move-on-first-run with a log line; never delete; test with a fixture dir containing legacy files. |
| A2 | Output dir is based on `os.getcwd()`, not `paths.ROOT` like all other data. Launching from another working directory (e.g. a pinned taskbar relaunch, `python -m this_voice_thing` from elsewhere) writes a second `chatterbox_outputs/` in that directory. Inherited from upstream `main.py:658`. | [V] code; [I] whether pinned relaunch sets cwd to the project | Fix the base path to `paths.ROOT` in the same change as any migration, and look for stray `chatterbox_outputs/` dirs during migration. |
| A3 | Graceful shutdown depends on exact window title: `scripts/restart_app.py:16` `TITLE = "This Voice Thing"`. A title change makes the restart script fall through; force-killing loses settings (window geometry, finishing, sampling are written in `closeEvent`). | [V] code; project memory "graceful restart" | Change title, `theme.APP_NAME`, `__init__.APP_NAME`, `taskbar.APP_NAME`, `restart_app.TITLE` and `tests/test_theme.py:156` together; or have restart_app import the constant. |
| A4 | `app_settings.json` contains a plain-text `hf_token`. Any migration that copies/rewrites settings must not log or move it elsewhere. | [V] key present in owner's file (value not read) | Migration touches only keys it needs; tests use scratch dirs (project rule: tests must not write to the owner's live data). |
| A5 | Settings keys: none contain "chatterbox", so **no settings-key migration is needed** for a rebrand. Values like `last_clone_entry`/`speed_by_model` contain `ResembleAI/chatterbox` (engine id) and must not be rewritten. | [V] | Exclude engine ids from any search-and-replace. |
| A6 | `models.json` is user-edited and holds `ResembleAI/chatterbox`. | [V] | Never rewrite it in a rename pass. |

## B. External scripts and integrations relying on names/paths

| # | Risk | Evidence | Mitigation |
|---|---|---|---|
| B1 | Scripts that glob `chatterbox_*.wav` break if the filename prefix changes. | [V] code comment `ui/threads.py:353-354` says such scripts exist; [I] which ones | Ask the owner; announce in CHANGELOG; optional setting to keep the old prefix. |
| B2 | Local HTTP API returns saved-file details under `chatterbox_outputs/api/` (documented in `integrations/local_api.py:19`). Clients may parse paths. | [V] docstring + `api_server.py:231`; [I] clients exist | Treat as API contract change; document. |
| B3 | `CHATTERBOX_INSTALL_LOG` env var links `setup_env.*` and `scripts/install_torch.py`. Renaming one without the others silently drops installer logging. | [V] 3 files only | Rename atomically; keep fallback read of old name. |
| B4 | `run.bat`/`run.sh` use relative `.venv` and `main.py` (inherited); repo-folder rename (#later) breaks pinned taskbar relaunch command (`taskbar.py:56-58` stores absolute paths) and any user shortcuts. | [V] code; [I] user pins/shortcuts | Note in release notes; app rewrites relaunch command on next start, but existing pins point to the old path until then. |
| B5 | GitHub repo rename: CONTRIBUTING already notes GitHub redirects old URLs. Clones keep working; hard-coded raw URLs in third-party docs may not. | [V] `CONTRIBUTING.md:46`; [I] impact | Low risk; keep redirect (do not reuse the old name). |

## C. Windows taskbar / AppUserModelID

| # | Risk | Evidence |
|---|---|---|
| C1 | AppUserModelID is `KnappKevin.ThisVoiceThing` (`ui/taskbar.py:17`), already free of "chatterbox". Changing it again would split existing pinned buttons from running windows and may show a cached generic icon. | [V] code; [I] Windows behaviour per the module's own docstring |
| C2 | Recommendation: **do not change APP_ID** as part of a rename unless the product name changes; if it does, accept one-time re-pinning and note it in CHANGELOG. `tests/test_taskbar.py` covers identity. | [I] |

## D. Attribution obligations

| # | Finding | Status |
|---|---|---|
| D1 | 5 files are byte-identical to upstream (`chatterbox_backend.py`, `LICENSE`, `requirements.in`, `requirements.lock.txt`, `upstream_original.png`). | [V] blob ids |
| D2 | Upstream code also survives in `scripts/install_torch.py`, `setup_env.*`, `run.*`, `app.py` (>=0.92 file similarity) and in 8 Python modules at function level (41 functions >=0.95). This is broader than the prior audit listed (adds `player.py`, `model_loading.py`, `generation.py`, `generate.py`, `model_settings.py`, `widgets.py`, `app.py`, launchers). | [V] |
| D3 | Attribution is required while this upstream-derived code remains: keep `LICENSE`, Readme Acknowledgements, `.all-contributorsrc`, CHANGELOG/CONTRIBUTING lineage lines. Renaming classes/files does not remove derivation. | Rule from prior audit; unchanged |
| D4 | `LICENSE` copyright line names "Resemble AI … - AcTePuKc Developments …" (upstream wording). The fork adds no own copyright line yet. Whether to add one is an owner decision. | [V] text; decision open |
| D5 | Retiring `docs/screenshots/upstream_original.png` (unreferenced) does not affect attribution. | [V] no references |
| D6 | Model weights and engine packages carry their own licenses (Chatterbox MIT; VibeVoice research-use note in Readme). A rebrand must not blur that. | [V] Readme / `model_registry.KNOWN_LICENSES` |

## E. Behavioural coupling uncovered by the audit

| # | Risk | Evidence |
|---|---|---|
| E1 | If `chatterbox-tts` fails to import, **every** engine is blocked (`CHATTERBOX_AVAILABLE` checked before the engine switch in `ui/threads.py:77` and `ui/pages/model_loading.py:27,151`). Worker engines do not need it. | [V] code; [I] that this is unintended |
| E2 | Log line "Attempting to load Chatterbox model…" printed for every engine (`ui/threads.py:87`). Cosmetic but misleading in support logs. | [V] |
| E3 | `ui.common` mixes engine-neutral helpers with Chatterbox bootstrap (NLTK download, `torch.load` patch, global stdout tee at import time). Importing it has side effects; 17 modules import it. Refactors must preserve import order. | [V] code; [I] side-effect sensitivity |
| E4 | `ChatterboxApp` rename touches 3 code refs + 27 docstrings + `tests/test_window_structure.py`. No persisted or string use. Low risk. | [V] grep |
| E5 | Product name duplicated in 4 places + 1 test (see A3). | [V] |

## F. Process risks

| # | Risk | Status |
|---|---|---|
| F1 | Owner runs the app from this checkout; tests/migrations must write to scratch dirs and never to live `chatterbox_outputs/`, `app_settings.json`, `voice_library/`. | [V] project memory |
| F2 | Close the app via WM_CLOSE before any migration test on the live tree; never force-kill. | [V] project memory |
| F3 | Untracked `soundboard/` dir exists in the checkout (not part of this audit). | [V] `git status` |

## Open questions for the owner

1. Do any of your scripts or tools read `chatterbox_outputs/` or `chatterbox_*.wav`? (B1/B2)
2. New output folder name and file prefix, and should old files be moved or just listed alongside? (A1)
3. Fix the `os.getcwd()` output base now (A2) - yes/no?
4. Keep `TAGLINE "Definitely not just Chatterbox UI."` and the "Began as a fork…" tooltip? (The tooltip doubles as in-app attribution.)
5. Rename `ChatterboxApp`? Keep a compatibility alias?
6. Remove the `CHATTERBOX_AVAILABLE` gate for non-Chatterbox engines (E1)? Needs a test.
7. Add an own copyright line to `LICENSE` alongside the upstream notice (D4)?
8. Delete `docs/screenshots/upstream_original.png`?
