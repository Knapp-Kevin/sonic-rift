# Legacy "chatterbox" symbol inventory (issue #55)

Source: `git grep -n -o -i -I -E '[A-Za-z_./-]*chatterbox[A-Za-z_.*-]*'` at local HEAD `bb18cf7` (tracked files only). **249 token occurrences in 53 files** (`.py`: 161 occurrences). Categorised by rule script `tools/symbols.py` (per-line list in `tools/symbols.json`), then spot-checked by hand; boundaries between "comment" and "user-visible text" are approximate (+/-3).

## Counts by category

| # | Category | Count | Action class |
|---|---|---:|---|
| E1 | Engine dependency (`requirements.in`, `requirements.lock.txt`: `chatterbox-tts` package and its pins) | 19 | **Must stay** |
| E2 | Byte-identical upstream backend `engines/chatterbox_backend.py` | 24 | **Must stay** (engine + attribution) |
| E3 | Engine id / repo / key strings (`ResembleAI/chatterbox`, `"chatterbox"` engine key in speed table, model filter, license map) | 13 | **Must stay** |
| U | User-visible text naming the engine (model labels "Chatterbox multilingual/original", "Chatterbox's own voice", install prompts "needs packages Chatterbox doesn't use", tooltips) | 20 | **Must stay** (engine identity) |
| C | Comments/docstrings: 27 mixin docstrings ("Mixed into ChatterboxApp" x26, "mixins of ChatterboxApp" x1) + engine-contract comments ("Chatterbox-compatible facade") | 52 | Rename the 27 mixin docstrings with the class; keep engine comments |
| I1 | `ChatterboxApp` class definition and code references (`main_window.py:71`, `:456`; `tests/test_window_structure.py:15`) | 3 | Rename candidate (code only; no user data) |
| I2 | Other identifiers: `CHATTERBOX_AVAILABLE` (9), `chatterbox_backends` alias (12), `load_chatterbox_model` (4), `UnsupportedChatterboxRepoError` (4), `CHATTERBOX_BACKENDS` (4), `CHATTERBOX_KEY_FILES` (3), local var `chatterbox` (2), test `FakeChatterbox` + test name (4) | 43 | Keep where they describe the engine; refactor the gate (see L) |
| L | Log/status messages | 5 | Fix (see below) |
| B | Product branding in UI | 3 | Product decision |
| P1 | Data path `chatterbox_outputs` (code, .gitignore, docstrings) | 5 | **RENAME-WITH-MIGRATION only** |
| P2 | Env var `CHATTERBOX_INSTALL_LOG` | 3 | Internal; rename freely in one commit |
| P3 | Output filename prefix `chatterbox_` | 3 | **RENAME-WITH-MIGRATION only** (external scripts) |
| D | Docs (`Readme.md` 21, `CHANGELOG.md` 5, `CONTRIBUTING.md` 3, provenance audit 12, plus doc tokens) | 56 | Keep attribution/engine mentions; review prose |
| | **Total** | **249** | |

Every runtime name in P1-P3 and L, plus `app_settings.json`, was **inherited from upstream** (VERIFIED: upstream `main.py:408` "Attempting to load Chatterbox model", `:618` `f"chatterbox_{timestamp}…"`, `:658` output dir, `:188` `app_settings.json`; `install_torch.py:22` `CHATTERBOX_INSTALL_LOG`).

## 1. Product branding visible to users (B)

| Location | Text | Note |
|---|---|---|
| `ui/theme.py:25` | `TAGLINE = "Definitely not just Chatterbox UI."` | Shown in title tooltip; deliberate joke branding |
| `ui/main_window.py:248-249` | Tooltip "Began as a fork of AcTePuKc/Chatterbox-TTS-UI; Resemble AI's Chatterbox is one of its engines." | Doubles as in-app attribution; keep some form of it |
| `Readme.md:5, 15, 262` | Tagline and "Not Chatterbox" jokes | Docs |

Window title, `QApplication` name/display name, taskbar name already read "This Voice Thing" (VERIFIED: `main_window.py:78, 453-454`, `taskbar.py:18`). The product name string is defined **four times**: `this_voice_thing/__init__.py:3`, `ui/theme.py:24`, `ui/taskbar.py:18`, `scripts/restart_app.py:16` (`TITLE`), plus asserted in `tests/test_theme.py:156`. A rebrand must change all five together.

## 2. Log and status messages that are wrong for non-Chatterbox engines (L) - VERIFIED

| Location | Message | Problem |
|---|---|---|
| `ui/threads.py:86-88` | `"Attempting to load Chatterbox model from repo '…' using backend '…'"` | Printed **before every load**, including Qwen, Kokoro, VoxCPM, OmniVoice, VibeVoice (the engine branch follows on line 90). Misleading log. |
| `ui/threads.py:77-79` | `if not CHATTERBOX_AVAILABLE: emit("ChatterboxTTS library is not installed.")` | **Structural**: if `chatterbox-tts` fails to import, *no* engine can load, although the worker engines do not need it. |
| `ui/pages/model_loading.py:27, 151-153` | Same `CHATTERBOX_AVAILABLE` gate, `"ChatterboxTTS library not installed."` | Same structural gate on the UI side. |
| `ui/main_window.py:164-175` | `"Status: Chatterbox library not found."` | Startup status; accurate only for the Chatterbox engine. |
| `ui/common.py:133` | `"WARNING: chatterbox-tts library not found."` | Accurate (engine-specific); keep. |

Renaming these is safe (no persisted data). Removing the gate for non-Chatterbox backends is a behaviour change that needs a test.

## 3. Class / function names (I1, I2)

- `ChatterboxApp` (`ui/main_window.py:71`) is the main window, composed from 21 page mixins whose docstrings say "Mixed into ChatterboxApp". Code references: `main_window.py:456`, `tests/test_window_structure.py:15`. No string/settings/pickle use found (VERIFIED by grep). A rename is code-only: change 3 code refs + 27 docstrings; optionally keep `ChatterboxApp = <NewName>` alias for one release.
- `load_chatterbox_model`, `UnsupportedChatterboxRepoError`, `CHATTERBOX_*` constants: describe the Chatterbox **engine** and live in or alias the byte-identical upstream backend. **Keep.** Renaming the backend's own symbols would break byte-identity with upstream and gains nothing.
- `chatterbox_backends` alias in `ui/common.py:128` is an upstream name (`import model_backends as chatterbox_backends`). Keep or rename with `common.py` refactor.

## 4. Runtime data paths, settings, identifiers (P1-P3 and related)

| Item | Where (VERIFIED) | Current value | Who depends on it | What a rename needs |
|---|---|---|---|---|
| Output folder | `ui/main_window.py:96` | `os.getcwd()/chatterbox_outputs` | Player list (`player.py:76`), generation (`generation.py:99`), API saves to `chatterbox_outputs/api/` (`api_server.py:231`; documented contract in `integrations/local_api.py:19`), transcript/subtitle save dialogs, `.gitignore:44`, Readme lines 33/158/555, user scripts (inferred) | One-time move or dual-read (new dir + legacy dir listed in player), `.gitignore` entry for both, API docs note, test that legacy files remain visible and nothing is deleted. Also fix the `os.getcwd()` base (see risks). Owner's install currently holds 16 files there (incl. `previews/`). |
| Output filename prefix | `ui/threads.py:353-355` | `chatterbox_<timestamp>_seed<n>[_partial\|_full_stitched]` | Code comment explicitly cites scripts that glob `chatterbox_*.wav` | Decide on new prefix; keep old files untouched; test that the player sorts mixed prefixes. |
| Settings file | `ui/common.py:236` | `app_settings.json` in project root | All settings | Name has no "chatterbox"; **no rename needed**. |
| Settings keys | `app_settings.json` (owner copy keys: `finishing`, `finishing_expanded`, `hf_token`, `last_clone_entry`, `sampling`, `studio_engine`, `tuning_expanded`, `window_*`) | No key contains "chatterbox" | - | **No migration needed.** Values such as `last_clone_entry = ["ResembleAI/chatterbox", "multilingual", …]` and `speed_by_model` keys contain the engine repo id; these are engine identity and must not be rewritten. |
| `models.json` | root | `repo_id: "ResembleAI/chatterbox"` | User-edited model list | Engine identity; **keep**. |
| Env var | `setup_env.bat:20`, `setup_env.sh:18`, `scripts/install_torch.py:23` | `CHATTERBOX_INSTALL_LOG` | Only these three files (VERIFIED) | Rename all three atomically; optional read of old name as fallback. |
| AppUserModelID | `ui/taskbar.py:17` | `KnappKevin.ThisVoiceThing` | Windows taskbar grouping and pinned shortcuts | Already rebranded; contains no "chatterbox". Changing it again orphans existing pins (see risks). |
| Window title | `ui/main_window.py:78` via `theme.APP_NAME` | `This Voice Thing` | `scripts/restart_app.py:16` matches exact title for graceful WM_CLOSE | Change both together. |
| Log files | `app.py:15`, setup scripts | `logs/app_startup_*.log`, `logs/installer_*.log` | - | No "chatterbox"; no change. |
| Other data dirs | `paths.py`, `common.py:237`, `core/voice_library.py:22` | `reference_recordings/`, `voice_library/`, `engines/<name>/.venv` | - | No "chatterbox"; no change. |
| Shortcuts | none created by the app (VERIFIED: no `.lnk` handling in code); taskbar relaunch command set at runtime (`taskbar.py:56-58`) | `.venv/Scripts/pythonw.exe main.py` | Pinned taskbar buttons | Path changes (repo folder rename) break existing pins (inferred). |

## 5. Engine identity that MUST stay

Resemble AI Chatterbox is a supported engine. Keep: `chatterbox-tts` dependency and lock pins; `engines/chatterbox_backend.py` (byte-identical upstream, attribution); `ResembleAI/chatterbox` repo ids in `models.json`, `core/model_registry.py`, `ui/common.py`; engine labels and tooltips (category U); `KNOWN_LICENSES` entry; `CHATTERBOX_KEY_FILES`; the Perth watermark wording; Readme engine table and Acknowledgements (lines ~608-611); `CHANGELOG.md:3` and `CONTRIBUTING.md:46-47` lineage notes; `LICENSE`.

## 6. Rename-safe vs migration-required (summary)

- **Safe, code-only** (tests must pass): `ChatterboxApp` + 27 docstrings; `CHATTERBOX_INSTALL_LOG`; misleading log line `threads.py:87`; status texts.
- **Behaviour change, needs a test**: `CHATTERBOX_AVAILABLE` gate blocking all engines.
- **Migration + test required**: `chatterbox_outputs/` folder, `chatterbox_` filename prefix, local API save path.
- **Do not rename**: engine identity (E1-E3, U), upstream backend file and its symbols.
