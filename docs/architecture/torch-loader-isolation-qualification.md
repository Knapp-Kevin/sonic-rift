# PyTorch loader isolation: Windows acceptance gate

**Candidate status: HOLD / not merge-qualified**  
**Source:** `refactor/engine-scoped-torch-loading-20261030-no-ci`  
**Base:** `main` `d180f9aaf2bd24356586e309ce0c19ff5da77839` (October 30, 2026)  
**Related:** [#55](https://github.com/Knapp-Kevin/sonic-rift/issues/55), [#57](https://github.com/Knapp-Kevin/sonic-rift/issues/57), [#61](https://github.com/Knapp-Kevin/sonic-rift/issues/61)

## What this candidate actually does

Removes the historical Chatterbox UI import-time global `torch.load` wrapper from `this_voice_thing/ui/common.py`. It also removes the global CUDA/MPS/CPU selection performed only to support that wrapper. The independent engine registration and provider-selected device requests remain unchanged. No other engine implementation was altered.

**Risk:** Chatterbox or another library's internal checkpoint loading may have relied on automatic `map_location` injection, especially when testing CPU fallback with a GPU-authored weight file. The absence of a process-wide override is not evidence that device fallback works. Do not merge until the real provider matrix passes.

## Source checks supplied on this branch

`tests/test_torch_loader_isolation.py`:

1. Parse the source to detect direct assignment of `torch.load`.
2. Launch a clean Python process with Hugging Face offline, patch NLTK resource discovery to avoid network downloads, import the real shared application bootstrap, and verify that the callable identity of `torch.load` is unchanged.
3. Perform an in-memory tiny tensor `torch.save` / `torch.load(..., map_location="cpu", weights_only=True)` roundtrip.

These tests do **not** yet have a Windows execution receipt. They protect the module boundary, not third-party model loaders. No tests on this candidate have been reported as passing.

## Required Windows owner/Claude sequence

1. **Protect data.** Record exact source SHA and installed Python/PySide6/PyTorch/CUDA versions; use a fresh isolated worktree and disposable profile. Do not alter existing projects, model caches, personal voices or approved `docs/marketing` assets. Do not download new models or change drivers.
2. **Compare startup.** On unchanged main and on candidate, run `python -m unittest tests.test_torch_loader_isolation -v` (the baseline is expected to fail the new protection if the test is applied there); `python -m unittest discover -s tests` on candidate; independently test real app startup, exit and restart. Capture actual failures and time-to-load, not only return codes.
3. **Cached engine matrix.** Load and generate one original short line on each installed eligible engine: Chatterbox English, Chatterbox multilingual v2/v3, Qwen3, Kokoro, VoxCPM2. Run both CUDA and CPU paths where the engine and cached weights support them. An absent model is an explicit SKIP with reason, never a silent pass. No real-person cloning for the test.
4. **Cross-workflow checks.** Switch engines sequentially; exercise Speech generation, in-place Studio narration, save/reopen/mix/export, Voices > Make clip, local API when supported, and one local Live speech/pad route. Verify the existing model-busy interlocks still function. Exercise missing weights, device fallback and failed load recovery.
5. **If a regression appears**, trace the exact checkpoint read call and implement the smallest **provider-local explicit device mapping**. Do not reinstall a process-wide wrapper, mutate third-party site-packages, or replace the independent provider architecture. Add a failing-before regression test. Repeat the complete affected matrix.
6. **Evidence and disposition.** Run the full suite again on the final candidate SHA. Compare output correctness, error/fallback, teardown and user-data hashes. Report qualified engines, tested devices, skipped combinations, reproducer, result and GO / CONDITIONAL GO / NO-GO on #57/#55 and #61. Only then request merge review. Use `[skip ci]` and don't consume Actions budget.

## Adjacent follow-ups, not in this candidate

- The historical bootstrap also performs import-time NLTK resource installation attempts. Track and replace that side effect independently after loader parity is established; do not silently change it during this patch.
- Remaining lineage includes Qt model/generation workers, adapter/window helper bodies, launcher/setup scripts. A blob mismatch is **not** original-authorship evidence. Preserve historic MIT attribution and verify third-party engine/model licenses before any license change.
- #13 Live Voice underrun, first-line primary/monitor offset, actual acoustic latency and external routes are still P0 acceptance gates. This refactor does not close them.
- No website work or changes to the approved marketing film and screenshots.
