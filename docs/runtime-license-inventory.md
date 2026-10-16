# Current installed Python dependency rights inventory

**Purpose:** Support source-rights and commercial-use review (#55 and #60) using the actual Python environments on the Windows development machine rather than the historical October 13 package snapshot in `docs/rebrand/licenses_summary.md`.

The [offline read-only script](../scripts/audit_runtime_licenses.py) inspects **distribution metadata only**, via `importlib.metadata` run through each environment's own Python interpreter. It does **not** import audio engines, run PyTorch, download models, call an API, change an environment, or buy a signing certificate.

## Example: capture actual Windows app and engine environments

From a scratch/worktree folder with the repo checked out, create a separate output directory of your choice and run with the project's available interpreters:

```powershell
.\.venv\Scripts\python.exe scripts\audit_runtime_licenses.py `
  --python "main=.\.venv\Scripts\python.exe" `
  --python "kokoro=.\engines\kokoro\.venv\Scripts\python.exe" `
  --python "voxcpm=.\engines\voxcpm\.venv\Scripts\python.exe" `
  --output ".\scratch\license-inventory.json"
```

Adjust the interpreter paths to the actual installed engine locations, and omit unavailable engines. The `scratch` destination directory must already exist. To inventory only the Python environment running the tool, omit the `--python` arguments and the tool will print JSON to stdout. Use `--python LABEL=PYTHON_PATH` repeatedly for every installed optional engine.

No changes to existing voices, model weights, configs or sound recordings should be necessary. If running this as part of a Windows QA session, do so in a separate worktree and avoid writing the report into the owner’s live data folders.

## Report semantics

- `distribution_count` and distribution name/version are observed metadata. Package metadata may report generic or absent licenses, may not describe native components, and may not match package license files.
- `license_expression`, `license_field` and `license_classifiers` are **verbatim metadata fields**. Long `License` fields are truncated and flagged, not treated as a complete copy of the license.
- `review_flags` is a **conservative attention list**, not an approval/denial, not a definitive copyleft determination, and not proof of commercial restrictions for that exact version. Every report is explicitly marked `not_cleared_manual_review_required`.
- A short explicit watchlist draws attention to `kaldiio`, `espeakng-loader`, `phonemizer-fork`, `praat-parselmouth`, `pykakasi` and Qt/PySide packages seen in prior inventories. Some older `kaldiio` builds and newer builds may have **different terms**, so verify the installed wheel's actual copyright/license before drawing any conclusion.
- The audit does **not** inspect model-weight licenses, in-process license obligations, DLL redistribution, bundled fonts/icons, sound recordings, trademark rights, or upstream source authorship. Review those separately, as appropriate to the intended use.
- An unflagged package is **not automatically cleared**. A flagged package is **not automatically prohibited**.

## Verification and follow-up

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_runtime_license_audit.py -v
```

The isolated test suite covers metadata normalization, watched packages, duplicate names, interpreter execution without a shell, a real read-only interpreter scan, and explicit JSON output. Future source-based readiness review should record the exact Git SHA and environment versions alongside the report. Compare against the historical [environment audit](rebrand/licenses_summary.md), reconcile suspected changes by checking the actual package LICENSE files and official model cards, then record decisions in #55/#60.

**Scope control:** Windows EXE packaging, signing, MSIX and Microsoft Store distribution remain deferred P4. Installing or reviewing source-based dependencies is not a pretext to reopen that packaging work.
