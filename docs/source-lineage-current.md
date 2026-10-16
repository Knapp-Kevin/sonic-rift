# Sonic Rift source lineage: current-main evidence

**Verified baseline:** Sonic Rift `main` at `9cdbfeadad11d2820435a72bdb528ab0d23a0e2b`, inspected October 16, 2026.  
**Historical upstream tree:** `AcTePuKc/Chatterbox-TTS-UI` commit `22460fd99ceb78c309f879b93878240241a0dc9b`.  
**Scope:** tracked Git objects and selected current code entry points, **not** copyright or trademark clearance, a runtime SBOM, legal advice, or a statement about what an installer redistributes.

The repository is still a GitHub fork of `AcTePuKc/Chatterbox-TTS-UI`. Fork-network membership is separate from attribution and code licenses; it must not be detached as a substitute for either.

## What the Git trees establish

The historical upstream tree contains **17 tracked blobs**. The current baseline contains **249 tracked blobs**. Of those 249 current paths, **two** contain byte-identical objects also found in the upstream tree:

| Current path | Upstream path | Git blob SHA-1 | Action |
| --- | --- | --- | --- |
| `LICENSE` | `LICENSE` | `c8178d4e9cca723e0f88be0208044d1d5dd256f7` | Retain upstream MIT permission and copyright notices |
| `docs/screenshots/upstream_original.png` | `screenshot_1.png` | `8be38900395eb296913e8b15dbe126a483991ad8` | Historical screenshot; do not promote as current Sonic Rift UI, preserve attribution while retained |

**Do not read “two exact blobs” as “only two files derived from upstream.”** Moving, formatting, splitting, adapting, renaming or partially replacing code changes blob IDs without necessarily changing its copyright provenance. These counts measure *identical object content*, not independent authorship or proportion of derived code. Historical October 9 and October 13 inventories in `docs/upstream-provenance-audit.md` and `docs/rebrand/` refer to earlier revisions and had different identical-object counts.

Contrary to the **historical** audit's older identical-dependency observation, the **current** `requirements.in` and `requirements.lock.txt` Git blobs differ from the upstream versions. This is a dependency-history finding, not a conclusion about installed package licenses, current environments or code originality.

## Current implementation review targets

| Boundary | Observed status at baseline | Remaining decision or evidence |
| --- | --- | --- |
| `this_voice_thing/engines/chatterbox_backend.py` | Thin compatibility facade delegating to `engines/chatterbox_provider.py`, replacing the original copied backend under #77 | Preserve the engine's actual identity and dependencies. Review new provider implementation and model rights independently |
| `this_voice_thing/ui/threads.py` | Still contains active `ModelLoaderThread` and `AudioGeneratorThread` with corresponding upstream-derived lifecycle structure | Function-level derivation review and real Windows model-load/generation regression before replacement (#57) |
| `this_voice_thing/ui/common.py` | Still installs an import-time, process-wide `torch.load` default-device monkeypatch and retains startup integration logic | #91 was **closed without merge**: moving the patch did not eliminate the global side effect. Only per-engine explicit behavior plus cross-engine Windows tests can close this gap |
| `this_voice_thing/ui/main_window.py` | Canonical `SonicRiftApp` and `ChatterboxApp` compatibility alias; redesigned navigation still carries evolved implementation | Original-method and class-body source review. Product rebranding is not clean-room provenance |
| `this_voice_thing/core/config_io.py`, `core/console_io.py` | Shared helper behavior extracted through #85/#86; `ui/common.py` retains compatibility interfaces | Verify callers, inherited expression and legacy import contracts independently; absence of a duplicate helper is not copyright clearance |
| `run.bat`, `setup_env.bat`, `scripts/install_torch.py` | Modified launch/dependency setup retaining legacy layout and paths | Source-based Windows invocation/data path correctness, line-level ancestry review and eventual P4 packaging check **if** distribution becomes a priority |
| `LICENSE`, `THIRD_PARTY_NOTICES.md` | Upstream MIT notice intact; separate index tracks engine/model obligations | Owned-source license decision, exact runtime dependency and weight rights review remain open (#55/#60) |

**Do not** perform a bulk rename of Chatterbox engine identifiers or the `chatterbox_outputs/` compatibility data directory. They may be legitimate engine/runtime paths, and removing them may orphan saved user files.

## Reproducing the object-level evidence locally

`scripts/audit_source_lineage.py` is a standard-library, **offline/read-only** tool. From a checkout with the historical upstream commit present:

```bash
python scripts/audit_source_lineage.py --current HEAD --upstream 22460fd99ceb78c309f879b93878240241a0dc9b > /tmp/sonic-rift-lineage.json
python -m unittest discover -s tests -p test_source_lineage_audit.py -v
```

The audit intentionally uses `git ls-tree`, Git object identity and explicit moved-path *review candidates*. It does not download an upstream repository, install dependencies, examine the owner's personal Windows environment, compare semantic function bodies, or assert that changed blobs are independent.

If the checkout is shallow and the historical commit is absent, the command fails with an actionable error instead of guessing or fetching. A verified provenance evaluation then requires fetching the relevant historical commit through an authorized workflow.

The `manual_review_areas` report section is a per-current-commit queue for the functional/licensing review; it is **not** a statement that all listed paths were copied. New report outputs may be attached to #55 as change evidence without committing ephemeral machine-specific data.

## Remaining gates

**#55:** Function-level current-source attribution and authored-code boundary; verify source and model/weight rights for actual installed environments; retain required historical notices.

**#57:** Replace surviving upstream-derived, runtime-sensitive worker/bootstrap/UI implementations with comparable behavior and real Windows evidence. Closing draft #91 did **not** complete this issue.

**#60:** Decide the license for source actually owned and licensable by Sonic Rift, update GitHub repository description/topics (currently still describe This Voice Thing), and reconcile contributor rights and accurate public copy. Frozen/signed Windows distributables and Store delivery remain deferred **P4**.

**#61:** Run whole-application source-based Windows acceptance in isolated profiles with actual installed engines. A clean static audit or passed isolated provenance tests is not sufficient.

**No changes in this audit authorize removing the root upstream MIT notice, automatically relicensing code, distributing model weights, or detaching GitHub's fork relationship.**
