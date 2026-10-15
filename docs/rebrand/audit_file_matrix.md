# File provenance matrix (issue #55)

> **Historical research snapshot, 2026-10-13.** Counts, source comparisons, package inventories, model licensing, and recommendations describe the audited revision, **not the current Sonic Rift `main`**. Subsequent implementation includes independent provider #77, core refactors #75/#78/#85/#86, and adopted MOSS soundscape implementation. Review current `docs/upstream-provenance-audit.md`, `THIRD_PARTY_NOTICES.md`, and release issue #61 before treating any result as a live production assertion. No new tests or downloads were performed during this archival integration.

Generated from `git ls-files` at local HEAD; **122 tracked files**. Upstream reference: AcTePuKc/Chatterbox-TTS-UI @ `22460fd`.

Column key:
- **Up%**: share of the file's significant lines (>=20 chars, non-comment, stripped) that occur verbatim anywhere in upstream main.py, launch_app.py, install_torch.py, model_backends.py, launchers, Readme, CONTRIBUTING, .gitignore, models.json, requirements.in or .all-contributorsrc. Values under ~7% are import/boilerplate collisions and are not evidence of derivation. VERIFIED metric; the origin label built on it is an INFERENCE except for byte-identical files.
- **Origin**: upstream-identical = same Git blob as an upstream file (VERIFIED). upstream-adapted = function-level difflib ratio >=0.5 for at least one upstream function, or Up% >=15%, or diff against the same-named upstream file shows small edits. original = no such evidence.
- **cb**: count of lines matching `chatterbox` (case-insensitive). **Coupling**: none / name-only (names, comments, strings, engine identity) / structural (imports the backend, gates on it, or owns a legacy runtime path/class name other code depends on).
- **Added by**: author of the commit that first added the path (git log --follow --diff-filter=A). Note: files split out of upstream main.py (common.py, threads.py, player.py...) show the fork author, so Git history alone under-reports provenance.


## Totals

| Origin | Files |
|---|---:|
| original | 98 |
| upstream-adapted | 19 |
| upstream-identical | 5 |

| Recommendation | Files |
|---|---:|
| KEEP | 113 |
| REFACTOR | 6 |
| RENAME-WITH-MIGRATION | 2 |
| RETIRE-CANDIDATE | 1 |

| Coupling | Files |
|---|---:|
| name-only | 47 |
| none | 69 |
| structural | 6 |

Only one RETIRE-CANDIDATE: `docs/screenshots/upstream_original.png` (no references). Removing it does not change attribution duties (LICENSE and Readme Acknowledgements stay). Two other unreferenced files (logo lockup, social preview) are kept because their use is likely outside the repo.

## entry/launch (9)

| File | Lines | Up% | cb | Origin | Coupling | Rec. | Added by | Reason |
|---|---:|---:|---:|---|---|---|---|---|
| `main.py` | 7 | 25.0 | 0 | original | none | KEEP | Shteryan Nikolaev | Path kept from upstream (git rename source of main_window.py); body is a new 7-line shim |
| `run.bat` | 24 | 90.0 | 0 | upstream-adapted | none | KEEP | Shteryan Nikolaev | Upstream run.bat with 1 changed line (SCRIPT_NAME) |
| `run.sh` | 17 | 87.5 | 0 | upstream-adapted | none | KEEP | Shteryan Nikolaev | Upstream run.sh with 1 changed line (SCRIPT_NAME) |
| `setup_env.bat` | 213 | 97.1 | 1 | upstream-adapted | name-only | REFACTOR | Shteryan Nikolaev | Upstream installer, 4 changed lines; CHATTERBOX_INSTALL_LOG env var |
| `setup_env.sh` | 160 | 95.1 | 1 | upstream-adapted | name-only | REFACTOR | Shteryan Nikolaev | Upstream installer, 4 changed lines; CHATTERBOX_INSTALL_LOG env var |
| `this_voice_thing/__init__.py` | 3 | 0.0 | 0 | original | none | KEEP | Knapp-Kevin | Defines APP_NAME (one of 4 copies of the product name) |
| `this_voice_thing/__main__.py` | 5 | 0.0 | 0 | original | none | KEEP | Knapp-Kevin | `python -m this_voice_thing` entry |
| `this_voice_thing/app.py` | 84 | 82.9 | 0 | upstream-adapted | none | KEEP | Shteryan Nikolaev | Upstream launch_app.py adapted: TeeFile 1.00, main 0.86, show_startup_error 0.82 |
| `this_voice_thing/paths.py` | 15 | 0.0 | 1 | original | name-only | KEEP | Knapp-Kevin | Root/assets/engines/logs paths; docstring lists chatterbox_outputs/ |

## ui shell (9)

| File | Lines | Up% | cb | Origin | Coupling | Rec. | Added by | Reason |
|---|---:|---:|---:|---|---|---|---|---|
| `this_voice_thing/ui/__init__.py` | 1 | 0.0 | 0 | original | none | KEEP | Knapp-Kevin | Package marker |
| `this_voice_thing/ui/api_bridge.py` | 116 | 2.9 | 0 | original | none | KEEP | Knapp-Kevin | Local API to UI-thread bridge |
| `this_voice_thing/ui/common.py` | 451 | 64.4 | 26 | upstream-adapted | structural | REFACTOR | Knapp-Kevin | Upstream bootstrap/config helpers (8 functions at 0.93-1.00); sole importer of chatterbox_backend |
| `this_voice_thing/ui/main_window.py` | 461 | 37.9 | 8 | upstream-adapted | structural | RENAME-WITH-MIGRATION | Shteryan Nikolaev | Git rename of upstream main.py; ChatterboxApp class, chatterbox_outputs path, CHATTERBOX_AVAILABLE gate |
| `this_voice_thing/ui/taskbar.py` | 94 | 1.8 | 0 | original | none | KEEP | Knapp-Kevin | AppUserModelID KnappKevin.ThisVoiceThing; changing it re-groups pinned taskbar icons |
| `this_voice_thing/ui/theme.py` | 510 | 0.0 | 1 | original | name-only | KEEP | Knapp-Kevin | APP_NAME copy + TAGLINE "Definitely not just Chatterbox UI." |
| `this_voice_thing/ui/threads.py` | 470 | 42.4 | 11 | upstream-adapted | structural | REFACTOR | Knapp-Kevin | Upstream ModelLoaderThread/AudioGeneratorThread; "Chatterbox" log + gate for all engines; chatterbox_ file prefix |
| `this_voice_thing/ui/tiles.py` | 248 | 2.5 | 0 | original | none | KEEP | Knapp-Kevin | Model tiles |
| `this_voice_thing/ui/widgets.py` | 137 | 15.7 | 0 | upstream-adapted | none | KEEP | Knapp-Kevin | SliderWithValue derived from upstream (get_value 1.00, __init__ 0.57); other widgets original |

## ui pages (22)

| File | Lines | Up% | cb | Origin | Coupling | Rec. | Added by | Reason |
|---|---:|---:|---:|---|---|---|---|---|
| `this_voice_thing/ui/pages/__init__.py` | 1 | 0.0 | 1 | original | name-only | KEEP | Knapp-Kevin | Docstring "mixins of ChatterboxApp" |
| `this_voice_thing/ui/pages/advanced.py` | 108 | 0.0 | 2 | original | name-only | KEEP | Knapp-Kevin | Mixin docstring only |
| `this_voice_thing/ui/pages/api_server.py` | 307 | 1.2 | 1 | original | name-only | KEEP | Knapp-Kevin | Writes to output_directory/api (= chatterbox_outputs/api) |
| `this_voice_thing/ui/pages/discover.py` | 93 | 1.4 | 1 | original | name-only | KEEP | Knapp-Kevin | Mixin docstring only |
| `this_voice_thing/ui/pages/documents.py` | 70 | 4.8 | 1 | original | name-only | KEEP | Knapp-Kevin | Mixin docstring only |
| `this_voice_thing/ui/pages/engine_controls.py` | 352 | 0.3 | 4 | original | name-only | KEEP | Knapp-Kevin | Engine-identity tooltips (Chatterbox built-in voice, Perth watermark) |
| `this_voice_thing/ui/pages/estimates.py` | 201 | 2.0 | 3 | original | name-only | KEEP | Knapp-Kevin | "chatterbox" used as engine key for speed table (engine identity) |
| `this_voice_thing/ui/pages/finishing.py` | 149 | 0.0 | 1 | original | name-only | KEEP | Knapp-Kevin | Mixin docstring only |
| `this_voice_thing/ui/pages/generate.py` | 274 | 20.5 | 4 | upstream-adapted | name-only | KEEP | Knapp-Kevin | refresh_language_options 0.90, apply_selected_text_preset 0.93; rest original |
| `this_voice_thing/ui/pages/generation.py` | 278 | 40.0 | 1 | upstream-adapted | name-only | KEEP | Knapp-Kevin | Upstream generation callbacks 0.63-1.00 |
| `this_voice_thing/ui/pages/library.py` | 219 | 0.5 | 2 | original | name-only | KEEP | Knapp-Kevin | Mixin docstring only |
| `this_voice_thing/ui/pages/model_loading.py` | 256 | 46.9 | 5 | upstream-adapted | structural | REFACTOR | Knapp-Kevin | Upstream model-load methods 0.53-1.00; CHATTERBOX_AVAILABLE gate blocks every engine |
| `this_voice_thing/ui/pages/model_settings.py` | 171 | 5.8 | 1 | upstream-adapted | name-only | KEEP | Knapp-Kevin | apply_hf_token_setting 0.75 vs upstream; dialogs rewritten |
| `this_voice_thing/ui/pages/models.py` | 373 | 1.7 | 2 | original | name-only | KEEP | Knapp-Kevin | Mixin docstring only |
| `this_voice_thing/ui/pages/player.py` | 203 | 72.1 | 1 | upstream-adapted | name-only | KEEP | Knapp-Kevin | 13 upstream player methods at 0.91-1.00 (72% line overlap) |
| `this_voice_thing/ui/pages/pronunciations.py` | 97 | 0.0 | 1 | original | name-only | KEEP | Knapp-Kevin | Mixin docstring only |
| `this_voice_thing/ui/pages/recording.py` | 107 | 6.0 | 1 | original | name-only | KEEP | Knapp-Kevin | Mixin docstring only |
| `this_voice_thing/ui/pages/studio.py` | 764 | 0.2 | 5 | original | name-only | KEEP | Knapp-Kevin | Chatterbox delivery controls = engine identity |
| `this_voice_thing/ui/pages/transcribe.py` | 234 | 0.6 | 1 | original | name-only | KEEP | Knapp-Kevin | Mixin docstring only |
| `this_voice_thing/ui/pages/voice.py` | 79 | 1.9 | 1 | original | name-only | KEEP | Knapp-Kevin | Mixin docstring only |
| `this_voice_thing/ui/pages/voice_picker.py` | 162 | 2.6 | 10 | original | name-only | KEEP | Knapp-Kevin | CHATTERBOX_BACKENDS constant; "Chatterbox's own voice" = engine identity |
| `this_voice_thing/ui/pages/voice_use.py` | 135 | 3.0 | 1 | original | name-only | KEEP | Knapp-Kevin | Mixin docstring only |

## dialogs (6)

| File | Lines | Up% | cb | Origin | Coupling | Rec. | Added by | Reason |
|---|---:|---:|---:|---|---|---|---|---|
| `this_voice_thing/ui/dialogs/__init__.py` | 1 | 0 | 0 | original | none | KEEP | Knapp-Kevin | Package marker |
| `this_voice_thing/ui/dialogs/google_docs.py` | 231 | 0.6 | 0 | original | none | KEEP | Knapp-Kevin | Google Docs picker |
| `this_voice_thing/ui/dialogs/models.py` | 347 | 2.3 | 1 | original | name-only | KEEP | Knapp-Kevin | Engine filter "Chatterbox" (engine identity) |
| `this_voice_thing/ui/dialogs/pronunciation.py` | 166 | 0.9 | 0 | original | none | KEEP | Knapp-Kevin | Pronunciation editor |
| `this_voice_thing/ui/dialogs/recording.py` | 255 | 1.0 | 0 | original | none | KEEP | Knapp-Kevin | Recorder dialog |
| `this_voice_thing/ui/dialogs/voices.py` | 145 | 1.0 | 1 | original | name-only | KEEP | Knapp-Kevin | Lists Chatterbox among cloning engines |

## engines adapters (9)

| File | Lines | Up% | cb | Origin | Coupling | Rec. | Added by | Reason |
|---|---:|---:|---:|---|---|---|---|---|
| `this_voice_thing/engines/__init__.py` | 1 | 0.0 | 1 | original | name-only | KEEP | Knapp-Kevin | Docstring |
| `this_voice_thing/engines/chatterbox_backend.py` | 232 | 100.0 | 22 | upstream-identical | structural | KEEP | Shteryan Nikolaev | Byte-identical upstream model_backends.py; active load path; engine identity |
| `this_voice_thing/engines/kokoro.py` | 134 | 1.4 | 3 | original | name-only | KEEP | Knapp-Kevin | "Chatterbox-compatible facade" = interface contract wording |
| `this_voice_thing/engines/omnivoice.py` | 189 | 0.9 | 2 | original | name-only | KEEP | Knapp-Kevin | Same facade contract |
| `this_voice_thing/engines/qwen.py` | 167 | 1.2 | 4 | original | name-only | KEEP | Knapp-Kevin | Same facade contract |
| `this_voice_thing/engines/rvc_feasibility.py` | 385 | 1.0 | 0 | original | none | KEEP | Kevin Knapp | No in-package importer, but used by scripts/, tests/ and CI workflow |
| `this_voice_thing/engines/vibevoice.py` | 167 | 1.1 | 2 | original | name-only | KEEP | Knapp-Kevin | Same facade contract |
| `this_voice_thing/engines/voxcpm.py` | 137 | 1.3 | 2 | original | name-only | KEEP | Knapp-Kevin | Same facade contract |
| `this_voice_thing/engines/worker.py` | 125 | 1.3 | 1 | original | name-only | KEEP | Knapp-Kevin | Shared JSON-lines worker plumbing |

## engine worker scripts (5)

| File | Lines | Up% | cb | Origin | Coupling | Rec. | Added by | Reason |
|---|---:|---:|---:|---|---|---|---|---|
| `engines/kokoro/kokoro_worker.py` | 127 | 5.8 | 0 | original | none | KEEP | Knapp-Kevin | Spawned by path from engines/kokoro.py |
| `engines/omnivoice/omnivoice_worker.py` | 138 | 4.9 | 0 | original | none | KEEP | Knapp-Kevin | Spawned by path from engines/omnivoice.py |
| `engines/qwen/qwen_worker.py` | 188 | 4.9 | 0 | original | none | KEEP | Knapp-Kevin | Spawned by path from engines/qwen.py |
| `engines/vibevoice/vibevoice_worker.py` | 126 | 5.4 | 0 | original | none | KEEP | Knapp-Kevin | Spawned by path from engines/vibevoice.py |
| `engines/voxcpm/voxcpm_worker.py` | 122 | 5.9 | 0 | original | none | KEEP | Knapp-Kevin | Spawned by path from engines/voxcpm.py |

## core (9)

| File | Lines | Up% | cb | Origin | Coupling | Rec. | Added by | Reason |
|---|---:|---:|---:|---|---|---|---|---|
| `this_voice_thing/core/__init__.py` | 1 | 0.0 | 0 | original | none | KEEP | Knapp-Kevin | Package marker |
| `this_voice_thing/core/audio_effects.py` | 253 | 1.8 | 0 | original | none | KEEP | Knapp-Kevin | Finishing/effects |
| `this_voice_thing/core/documents.py` | 318 | 1.5 | 0 | original | none | KEEP | Knapp-Kevin | Document import/chunking |
| `this_voice_thing/core/model_registry.py` | 631 | 1.7 | 16 | original | name-only | KEEP | Knapp-Kevin | Chatterbox repo ids/labels/key files = engine identity |
| `this_voice_thing/core/pronunciation.py` | 166 | 0.0 | 0 | original | none | KEEP | Knapp-Kevin | Pronunciation dictionary |
| `this_voice_thing/core/subtitles.py` | 207 | 0.7 | 0 | original | none | KEEP | Knapp-Kevin | Subtitle export |
| `this_voice_thing/core/transcription.py` | 133 | 1.4 | 0 | original | none | KEEP | Knapp-Kevin | Whisper transcription |
| `this_voice_thing/core/voice_library.py` | 217 | 0.0 | 0 | original | none | KEEP | Knapp-Kevin | voice_library/ data store |
| `this_voice_thing/core/voice_studio.py` | 161 | 2.1 | 2 | original | name-only | KEEP | Knapp-Kevin | Engine branch comment |

## integrations (3)

| File | Lines | Up% | cb | Origin | Coupling | Rec. | Added by | Reason |
|---|---:|---:|---:|---|---|---|---|---|
| `this_voice_thing/integrations/__init__.py` | 1 | 0.0 | 0 | original | none | KEEP | Knapp-Kevin | Package marker |
| `this_voice_thing/integrations/google_docs.py` | 277 | 0.0 | 0 | original | none | KEEP | Knapp-Kevin | Google Docs import |
| `this_voice_thing/integrations/local_api.py` | 282 | 0.5 | 1 | original | name-only | KEEP | Knapp-Kevin | Docstring documents chatterbox_outputs/api/ (external contract) |

## scripts (3)

| File | Lines | Up% | cb | Origin | Coupling | Rec. | Added by | Reason |
|---|---:|---:|---:|---|---|---|---|---|
| `scripts/install_torch.py` | 290 | 98.6 | 1 | upstream-adapted | name-only | REFACTOR | Shteryan Nikolaev | Upstream install_torch.py + 1 added nvidia-smi fallback block; CHATTERBOX_INSTALL_LOG |
| `scripts/restart_app.py` | 82 | 2.4 | 0 | original | none | KEEP | Knapp-Kevin | Finds window by exact title "This Voice Thing" - breaks if title changes |
| `scripts/rvc_feasibility.py` | 63 | 5.3 | 0 | original | none | KEEP | Kevin Knapp | CLI for RVC feasibility check |

## tests (7)

| File | Lines | Up% | cb | Origin | Coupling | Rec. | Added by | Reason |
|---|---:|---:|---:|---|---|---|---|---|
| `tests/test_quiet_thread.py` | 39 | 5.6 | 0 | original | none | KEEP | Knapp-Kevin | Covers ui.threads |
| `tests/test_rvc_feasibility.py` | 102 | 3.1 | 0 | original | none | KEEP | Kevin Knapp | Covers rvc_feasibility |
| `tests/test_taskbar.py` | 35 | 5.0 | 0 | original | none | KEEP | Knapp-Kevin | Covers taskbar identity |
| `tests/test_theme.py` | 160 | 0.9 | 0 | original | none | KEEP | Knapp-Kevin | Asserts APP_NAME == "This Voice Thing" |
| `tests/test_transcription.py` | 115 | 1.4 | 0 | original | none | KEEP | Knapp-Kevin | Covers transcription/local_api |
| `tests/test_voice_studio.py` | 128 | 1.3 | 4 | original | name-only | KEEP | Knapp-Kevin | FakeChatterbox test double (engine identity) |
| `tests/test_window_structure.py` | 44 | 3.8 | 1 | original | structural | KEEP | Knapp-Kevin | Imports main_window.ChatterboxApp by name; must change with any class rename |

## docs (22)

| File | Lines | Up% | cb | Origin | Coupling | Rec. | Added by | Reason |
|---|---:|---:|---:|---|---|---|---|---|
| `CHANGELOG.md` | 90 | 0.0 | 5 | original | name-only | KEEP | Knapp-Kevin | Records lineage and the rename |
| `CONTRIBUTING.md` | 70 | 58.1 | 3 | upstream-adapted | name-only | KEEP | Shteryan Nikolaev | Upstream CONTRIBUTING extended (58% overlap) |
| `LICENSE` | 22 | 0.0 | 0 | upstream-identical | none | KEEP | Shteryan Nikolaev | Upstream MIT notice; must be preserved |
| `Readme.md` | 638 | 3.7 | 21 | original | name-only | KEEP | Shteryan Nikolaev | Git lineage from upstream Readme but ~4% line overlap; holds attribution section |
| `docs/live-voice-advanced-integrations.md` | 589 | 0.0 | 0 | original | none | KEEP | Kevin Knapp | Design doc (live voice / RVC) |
| `docs/live-voice-adversarial-review.md` | 545 | 0.0 | 0 | original | none | KEEP | Kevin Knapp | Design doc (live voice / RVC) |
| `docs/live-voice-architecture.md` | 787 | 0.0 | 0 | original | none | KEEP | Kevin Knapp | Design doc (live voice / RVC) |
| `docs/live-voice-microphone-transformation-roadmap.md` | 439 | 0.0 | 0 | original | none | KEEP | Kevin Knapp | Design doc (live voice / RVC) |
| `docs/live-voice-product-spec.md` | 538 | 0.0 | 0 | original | none | KEEP | Kevin Knapp | Design doc (live voice / RVC) |
| `docs/rvc-feasibility.md` | 140 | 0.0 | 0 | original | none | KEEP | Kevin Knapp | Design doc (live voice / RVC) |
| `docs/screenshots/advanced.png` | - | - | 0 | original | none | KEEP | Knapp-Kevin | Screenshot of this app, referenced by Readme |
| `docs/screenshots/discover.png` | - | - | 0 | original | none | KEEP | Knapp-Kevin | Screenshot of this app, referenced by Readme |
| `docs/screenshots/generate_light.png` | - | - | 0 | original | none | KEEP | Knapp-Kevin | Screenshot of this app, referenced by Readme |
| `docs/screenshots/generate_progress.png` | - | - | 0 | original | none | KEEP | Knapp-Kevin | Screenshot of this app, referenced by Readme |
| `docs/screenshots/generate_qwen_dark.png` | - | - | 0 | original | none | KEEP | Knapp-Kevin | Screenshot of this app, referenced by Readme |
| `docs/screenshots/model.png` | - | - | 0 | original | none | KEEP | Knapp-Kevin | Screenshot of this app, referenced by Readme |
| `docs/screenshots/recording.png` | - | - | 0 | original | none | KEEP | Knapp-Kevin | Screenshot of this app, referenced by Readme |
| `docs/screenshots/studio.png` | - | - | 0 | original | none | KEEP | Knapp-Kevin | Screenshot of this app, referenced by Readme |
| `docs/screenshots/transcribe.png` | - | - | 0 | original | none | KEEP | Knapp-Kevin | Screenshot of this app, referenced by Readme |
| `docs/screenshots/upstream_original.png` | - | - | 0 | upstream-identical | none | RETIRE-CANDIDATE | Shteryan Nikolaev | Byte-identical upstream screenshot; no references in tracked files except the audit doc |
| `docs/screenshots/voice.png` | - | - | 0 | original | none | KEEP | Knapp-Kevin | Screenshot of this app, referenced by Readme |
| `docs/upstream-provenance-audit.md` | 80 | 0.0 | 12 | original | name-only | KEEP | Kevin Knapp | Prior provenance audit |

## assets (10)

| File | Lines | Up% | cb | Origin | Coupling | Rec. | Added by | Reason |
|---|---:|---:|---:|---|---|---|---|---|
| `assets/branding/this-voice-thing-app-icon.png` | - | - | 0 | original | none | KEEP | Kevin Knapp | Referenced by ui/theme.py, taskbar.py or Readme |
| `assets/branding/this-voice-thing-banner.jpg` | - | - | 0 | original | none | KEEP | Knapp-Kevin | Referenced by ui/theme.py, taskbar.py or Readme |
| `assets/branding/this-voice-thing-logo-lockup.png` | - | - | 0 | original | none | KEEP | Kevin Knapp | Not referenced in repo; likely external-use brand asset (inferred) - keep |
| `assets/branding/this-voice-thing-social-preview.jpg` | - | - | 0 | original | none | KEEP | Kevin Knapp | Not referenced in repo; GitHub social preview (inferred) - keep |
| `assets/branding/this-voice-thing.ico` | - | - | 0 | original | none | KEEP | Knapp-Kevin | Referenced by ui/theme.py, taskbar.py or Readme |
| `assets/check_dark.svg` | 1 | 0.0 | 0 | original | none | KEEP | Knapp-Kevin | Referenced by ui/theme.py, taskbar.py or Readme |
| `assets/check_light.svg` | 1 | 0.0 | 0 | original | none | KEEP | Knapp-Kevin | Referenced by ui/theme.py, taskbar.py or Readme |
| `assets/chevron_down_dark.svg` | 1 | 0.0 | 0 | original | none | KEEP | Knapp-Kevin | Referenced by ui/theme.py, taskbar.py or Readme |
| `assets/chevron_down_light.svg` | 1 | 0.0 | 0 | original | none | KEEP | Knapp-Kevin | Referenced by ui/theme.py, taskbar.py or Readme |
| `assets/logo.svg` | 16 | 0.0 | 0 | original | none | KEEP | Knapp-Kevin | Referenced by ui/theme.py, taskbar.py or Readme |

## config (8)

| File | Lines | Up% | cb | Origin | Coupling | Rec. | Added by | Reason |
|---|---:|---:|---:|---|---|---|---|---|
| `.all-contributorsrc` | 29 | 45.5 | 0 | upstream-adapted | none | KEEP | Shteryan Nikolaev | Upstream contributor credits (attribution) |
| `.gitattributes` | 2 | 0 | 0 | original | none | KEEP | Knapp-Kevin | CRLF for .bat |
| `.github/workflows/rvc-feasibility-ci.yml` | 53 | 0.0 | 0 | original | none | KEEP | Kevin Knapp | CI for RVC feasibility |
| `.gitignore` | 85 | 40.0 | 1 | upstream-adapted | name-only | RENAME-WITH-MIGRATION | Shteryan Nikolaev | Upstream-derived; ignores chatterbox_outputs/ - update with any path migration |
| `models.json` | 139 | 33.7 | 1 | upstream-adapted | name-only | KEEP | Shteryan Nikolaev | Upstream-format model list, extended; ResembleAI/chatterbox repo id = engine identity; user-edited file |
| `requirements.in` | 5 | 100.0 | 1 | upstream-identical | name-only | KEEP | Shteryan Nikolaev | Byte-identical upstream; chatterbox-tts dependency |
| `requirements.lock.txt` | 451 | 0.0 | 16 | upstream-identical | name-only | KEEP | Shteryan Nikolaev | Byte-identical upstream lock |
| `uv.toml` | 3 | 0.0 | 0 | original | none | KEEP | Knapp-Kevin | Perth override |
