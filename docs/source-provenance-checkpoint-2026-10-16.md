# Current-source provenance checkpoint (2026-10-16)

Status: **partial, code-inspected inventory only; no rights clearance**. Tracks #55, #57 and #60. Inspection was against the GitHub default-branch contents on 2026-10-16. This file documents inspected Git blobs rather than assuming that historical file inventories remain current.

## Directly inspected current source

| File / Git blob | Verified observation | Follow-up action |
| --- | --- | --- |
| `this_voice_thing/ui/common.py` · `369b45250634115d4e8d81f2fde48234824ec394` | Import-time wrapper replaces **global `torch.load`**, choosing CUDA/MPS/CPU unless `map_location` is passed. Startup also configures process stdout/stderr and can attempt **NLTK downloads** if `punkt`/`punkt_tab` is missing. | Treat these as behavior/security/reproducibility risks, not evidence of independent authorship. Do not change during #61 Windows acceptance; replace with engine-scoped behavior only after real-engine parity verification. Explicitly document network/download consent in source-run docs. |
| `this_voice_thing/ui/threads.py` · `a003c93e6e33614bbb6c7b967f1c1591320bba3a` | Qt `ModelLoaderThread` delegates provider selection to `core.engine_loading`, but still owns Qt signals, device probing and lifecycle, and imports shared `ui.common`. Comments describe historical worker implementation. | Compare function-level implementation with upstream at a pinned upstream SHA before assigning derived/original status. Separate lifecycle from providers incrementally, with physical Windows regression. |
| `THIRD_PARTY_NOTICES.md` · `8934a69c06f98b7cd0fd43dcdcd4378e651497b6` | Explicitly states historical upstream derivation and treats code, weights, dependencies and media as separate rights surfaces. | Keep as the current notice index; verify actual installed versions and weight terms in source-run environment. |
| `LICENSE` · `c8178d4e9cca723e0f88be0208044d1d5dd256f7` | Root MIT notice still includes upstream attribution and conditions. | **Retain** pending authorized rights decision. Do not reinterpret rebrand or fork detachment as license transfer. |

## What this inspection does not prove

- No function-by-function upstream comparison has been executed here, and no authorship percentage can be calculated from these four blobs.
- No actual Windows environment package/weight license inventory was obtained.
- A package source license does not automatically authorize redistribution of downloaded weights, recordings or binaries.
- PR #91 was closed **without merge**. Its proposed global PyTorch abstraction is not authorization to reintroduce or approve a process-wide hook.
- Filename identity (`this_voice_thing`) is not sufficient evidence of derivation; conversely, a product rename does not eliminate inherited rights.

## Required next evidence

1. Pin **both** current-main SHA and upstream comparison SHA; generate function-level similarity annotations for remaining `ui/threads.py`, `ui/common.py`, adapted widgets, launchers and installation scripts. Distinguish exact bytes, modified derivation, and unsupported/unknown ownership; attach source paths and comparable spans.
2. Run existing read-only source-lineage and runtime-license inventory scripts without package/model installation. Persist hashes and commands, and explicitly record skipped/unavailable environments.
3. Reconcile installed engine code, weights, transitive dependencies, NLTK resources and FFmpeg obligations with actual source-run environment; separately assess any future redistribution.
4. Preserve the upstream MIT text and historical notices throughout; propose per-file source-license treatment only after #60 owner rights decision.
5. Treat network-triggered import behavior and process-global `torch.load` mutation as engineering concerns requiring real Windows parity testing, not a reason for an unreviewed patch.

This is intentionally a narrow additive checkpoint; #55 remains open until function-level provenance and installed-runtime obligations are evidenced.
