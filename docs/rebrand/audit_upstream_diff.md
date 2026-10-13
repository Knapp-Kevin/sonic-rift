# Upstream diff audit (issue #55)

Extends `docs/upstream-provenance-audit.md`; does not repeat its byte-identity table.

**Inputs**
- Upstream: `git clone --depth 1 https://github.com/AcTePuKc/Chatterbox-TTS-UI` -> commit `22460fd99ceb78c309f879b93878240241a0dc9b` (2026-06-11, tree `4aa7b19a…`). Clone lives at `phase0/audit/upstream/`.
- Local: `main` at `bb18cf7…` tree; 122 tracked files.
- Method: `diff --strip-trailing-cr` for scripts; Python `ast` + `difflib.SequenceMatcher` on stripped, comment-free lines per function/method (`tools/fcompare.py`, raw output `tools/fcompare.json`). Line endings ignored: the clone was checked out with `core.autocrlf=true`, so working-tree hashes differ even where committed blobs match.

## 0. History (VERIFIED)

- Local history has 73 commits. The 17 oldest by **Shteryan Nikolaev** (upstream author) plus 1 by **lowkeytea** are upstream commits, and the upstream HEAD `22460fd` is itself a commit in local history (`git cat-file -t 22460fd` = commit). The fork's first own commit is `d42ca68` (2026-10-02, "Fix Windows install…").
- Re-check of the existing byte-identity claim with committed blob IDs (`git ls-tree`): `model_backends.py`=`chatterbox_backend.py` (`217900b`), `LICENSE` (`c8178d4`), `requirements.in` (`d709ddd`), `requirements.lock.txt` (`e97850f`), `screenshot_1.png`=`upstream_original.png` (`8be3890`). **Still identical.**
- Git rename tracking (`git log --follow`) links `this_voice_thing/ui/main_window.py` back to upstream `main.py`, and `this_voice_thing/app.py`, `chatterbox_backend.py`, `scripts/install_torch.py` back to upstream files. Files split out of `main.py` later (`ui/common.py`, `ui/threads.py`, `ui/pages/*.py`, `ui/widgets.py`) show the fork author as creator. **Git history under-reports provenance for those files; content comparison below is the stronger evidence.**

## 1. Installer and launchers (VERIFIED, line level)

| Upstream | Current | Whole-file ratio | Changed lines | What changed |
|---|---|---:|---|---|
| `install_torch.py` (275) | `scripts/install_torch.py` (290) | 0.973 | 2 hunks, +15 lines, 0 removed | `import re` and a new fallback that parses the plain `nvidia-smi` header (`CUDA (?:UMD )?Version`) for newer drivers. Every upstream line kept. Still reads `CHATTERBOX_INSTALL_LOG`. |
| `setup_env.bat` (213) | `setup_env.bat` (213) | 0.981 | 4 | Banner `Chatterbox TTS Installer` -> `This Voice Thing Installer` (2 lines); `install_torch.py` -> `scripts\install_torch.py` (2 lines). Still sets `CHATTERBOX_INSTALL_LOG`. |
| `setup_env.sh` (160) | `setup_env.sh` (160) | 0.975 | 4 | Same 4 edits as the .bat. |
| `run.bat` (24) | `run.bat` (24) | 0.958 | 1 | `SCRIPT_NAME=launch_app.py` -> `main.py`. |
| `run.sh` (17) | `run.sh` (17) | 0.941 | 1 | `SCRIPT_NAME="launch_app.py"` -> `"main.py"`. |
| `launch_app.py` (83) | `this_voice_thing/app.py` (84) | 0.922 | - | `TeeFile` 4/4 methods 1.00; `make_startup_log_path` 0.73; `show_startup_error` 0.82; `main` 0.86 (now `runpy`s `this_voice_thing.ui.main_window`). **New finding: not covered by the prior audit.** |

Conclusion: all five launch/install scripts and the app bootstrap are **upstream code with small edits** (>=94% similar), not rewrites.

## 2. Upstream `main.py` (1,780 lines) -> current package

83 upstream functions/methods (77 in `main.py`, 6 in `launch_app.py`; 1,526 lines). Best-matching current function (same name, or best ratio anywhere in `this_voice_thing/`, `scripts/`, `engines/`):

| Similarity bucket | Units | Upstream lines |
|---|---:|---:|
| >= 0.95 (verbatim or near) | 41 | 323 |
| 0.80 - 0.95 | 10 | 271 |
| 0.50 - 0.80 | 13 | 270 |
| < 0.50 or no counterpart | 19 | 662 |

Module-level code (imports, device pick, `torch.load` patch, stdout tee, NLTK bootstrap, backend `getattr` fallbacks, language test texts, default model config; 169 significant lines): **83% matched in order inside `ui/common.py`**.

Line-level cross-check: 693 of 1,079 distinct significant lines (>=20 chars) of upstream `main.py` still occur verbatim somewhere in the repo (64%). This counts shared lines and is a coarse indicator only (INFERRED that most are inherited, since some are generic PySide6 imports).

### Per destination file

| Current file | Upstream units retained (ratio) | Assessment |
|---|---|---|
| `ui/common.py` | `patched_torch_load`, `configure_console_stream`, `safe_console_text`, `TeeStream` (5 methods), `read_models_config_payload`, `read_json_payload`, `write_json_payload` all **1.00**; `load_models_config` 0.93; module-level block 0.83 | Upstream bootstrap, largely verbatim. Already noted by the prior audit; now quantified. |
| `ui/threads.py` | `ModelLoaderThread.__init__` 0.98, `.run` 0.85; `AudioGeneratorThread.__init__` 0.88, `set_seed_internal` 1.00, `stop` 0.57, `run` 0.47; `_chunk_long_sentence` gone (chunking now in `core/documents`) | Loader near-verbatim; generator heavily reworked. |
| `ui/main_window.py` (`ChatterboxApp`) | `append_console_log`, `load_app_settings`, `restore_window_settings`, `save_window_settings`, `set_status_message`, `resizeEvent` **1.00**; `save_app_settings` 0.86; `closeEvent` 0.69; `__init__` 0.66; `attach_log_sink` 0.40; `_init_ui` 0.16 (rewritten) | Settings and window-state plumbing are upstream; layout is new. |
| `ui/pages/player.py` (**new finding**) | 13 methods: `play_selected_from_log`, `toggle_play_pause`, `stop_audio`, `slider_pressed/released`, `seek_audio_on_move`, `update_slider_position`, `update_duration_info`, `format_time`, `handle_playback_state_changed`, `handle_media_error` **1.00**; `update_output_log` 0.91 | Audio player is upstream code moved into a mixin (72% line overlap). |
| `ui/pages/model_loading.py` (**new**) | `start_default_model_load`, `get_selected_model_repo`, `get_selected_model_entry` 1.00; `on_model_loaded` 0.86; `load_model` 0.74; `set_model_loading_state` 0.72; `on_model_load_error` 0.71; `refresh_model_repo_options` 0.54; `get_visible_model_entries` 0.53 | Upstream model-switch logic, adapted. |
| `ui/pages/generation.py` (**new**) | `update_generation_time`, `on_generation_error` 1.00; `update_generation_time_display` 0.96; `on_generation_thread_finished`, `on_generation_complete` 0.63; `handle_generate_stop_toggle` 0.24 | Callbacks upstream; start/stop flow rewritten. |
| `ui/pages/generate.py` (**new**) | `apply_selected_text_preset` 0.93; `refresh_language_options` 0.90 | Two upstream methods in an otherwise new page. |
| `ui/pages/model_settings.py` (**new**) | `apply_hf_token_setting` 0.75 | Upstream token dialog itself is gone. |
| `ui/widgets.py` (**new**) | `SliderWithValue.get_value` 1.00, `__init__` 0.57 | Small upstream widget, restyled. |

### Upstream units with no counterpart (VERIFIED by name search and ratio < 0.3)

`refresh_hf_token_button_tooltip`, `browse_reference_audio`, `on_experimental_models_toggled`, `refresh_model_details`, `show_model_details_dialog`, `show_model_help_dialog`, `open_hf_token_dialog`, `open_sampling_settings_dialog`, `open_models_config`, `reload_models_config`, `AudioGeneratorThread._chunk_long_sentence`; `_create_slider` exists by name but shares no code (0.00). These upstream features were replaced, not carried.

## 3. Other upstream files

| Upstream | Current | Evidence |
|---|---|---|
| `models.json` | `models.json` | Ratio 0.29; schema and first entry (`ResembleAI/chatterbox`) retained; extended to 139 lines. User-editable data file. |
| `CONTRIBUTING.md` | `CONTRIBUTING.md` | Ratio 0.76; upstream text extended. |
| `Readme.md` | `Readme.md` | Ratio 0.17; 12 of 328 significant lines shared. Effectively rewritten; holds the attribution section (lines ~608-611). |
| `.gitignore`, `.all-contributorsrc` | same | Upstream-derived, small edits. `.all-contributorsrc` carries upstream contributor credits. |

## 4. `docs/screenshots/upstream_original.png` references (VERIFIED)

`git grep -n "upstream_original\|screenshot_1"` hits only `docs/upstream-provenance-audit.md` (lines 18 and 37, both describing the file itself). Not referenced by `Readme.md`, `CHANGELOG.md`, code or tests. **Unreferenced; RETIRE-CANDIDATE.** Removing it does not affect attribution duties.

## 5. Summary

- VERIFIED: 5 upstream files byte-identical; 5 scripts + `app.py` are upstream with 1-15 line edits; 41 upstream functions survive at >=0.95 similarity across 8 current Python files (not 4 as previously listed: `player.py`, `model_loading.py`, `generation.py`, `generate.py`, `model_settings.py`, `widgets.py`, `app.py` were not in the prior audit).
- INFERRED: roughly 864 of 1,526 upstream function lines (57%) have a recognisable counterpart (>=0.5). This is a code-similarity measure, not a copyright allocation.
- Attribution is required while this upstream-derived code remains.
