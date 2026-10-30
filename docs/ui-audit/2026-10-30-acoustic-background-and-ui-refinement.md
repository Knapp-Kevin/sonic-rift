# Sonic Rift UI refinement review, 2026-10-30

**Scope:** Studio-first desktop app and the new acoustic-wave backgrounds, draft #120 stacked on draft #119.
**Method:** source and regression-test review through the authenticated GitHub connector, plus inspection of the actual five October 30 promotional screenshots, prior audit `docs/ui-audit/2026-10-16-ui-cohesion-audit.md`, and the marketing transcript/manifest. **Not a live Windows visual or performance test.** No new public release or media sign-off.

## Disposition

**CONDITIONAL / HOLD for exact-head Windows UI acceptance.** Keep the PR draft. Implementation is in reviewable source, not merged to `main`. Do not replace #118's website assets with generated concept art or screenshots of unqualified code.

## What changed in this pass

| Area | Observed defect | Implemented on #120 | Qualification |
| --- | --- | --- | --- |
| Background | Former speckled texture reads as TV static | Procedural stable resonance-wave profiles; dark/light brand palette and clean sidebar, no random speckle tile | UI visual QA still needed; `_paint_sonic_waves` is **not** identical to approved concept bitmap |
| Navigation | Studio, Speech, Sounds and voice workflows should be related but visually distinct | Scene selection for Studio / Speech / Sounds / Live / Transcribe / Models and Settings, plus Library / Clone / Design / Remix | Test state changes and pixel-level distinctness on Windows |
| Speech history | Two generated files created in the same second are displayed with identical friendly labels | Deterministic readable `variation n/N` labels per colliding timestamp, original filenames preserved for discovery in tooltips | Added same-second, reversed-enumeration, history-refresh regressions |
| Result selection | With no highlighted row, Add to Studio could reuse an old played file instead of the latest visible output | Prefer the first (newest) history item; fall back to the current audio file only if the history is empty | Added isolated input selection regression |
| History refresh | Rebuilding the file list cleared the user-selected take | Selection persisted by stored underlying file path | Added selection persistence regression |
| Player | Raw `chatterbox_...` filename reappeared after playing a history item | Player status now uses the same human-visible label; original filename remains in tooltip | Visual truncation check at 960×600 |
| Keyboard | Recent take playback could require double-click | Use Qt's `itemActivated` (Enter and double-click) | Verify actual Qt keyboard behavior and screen-reader focus |
| Layout | Long document names could increase the Player's minimum width | Player status QLabel uses ignored horizontal size policy and zero minimum width | Verify readable truncation and tooltip on small windows |
| Design governance | Old design document described the project editor as a dialog and every page as scrollable, and omitted wave scenes | Updated `docs/design-system.md` to the current Studio page workflow and background/contrast/capture rules | Source-reviewed, not user/owner visual approval |

## Cross-page design evaluation

**Strong direction:** Studio as the place where generated assets become one project. Reusable card/button tokens, themed tabs and controls, readable empty states and restrained cyan accents are cohesive. New sound contours should stay underneath controls as low-contrast environmental identity, not a fake audio meter.

**Keep an eye on:** deep tab nesting in Voices > New voice > Clone/Design/Remix; one voice choice may still be represented in both the Speech header and delivery settings; Models' discover/loading visual balance; selected/disabled/focus states in light theme. These are **not closed by this pass**. Do not remove controls or reorganize the engine model without owner review and behavioral tests.

**Marketing truth:** the prior Studio screenshots show an unsaved project; the Speech screenshots show duplicate take labels; the first video uses a single seed voice and its clone rather than a distinct narrator and two distinct characters. #118 now holds a proposed narrative storyboard. Final media needs recapture with the qualified new backgrounds, all real application screenshots, accurate voice provenance, soundtrack/listening review, captions, rights and manifest hashes.

## Windows qualification, 2026-10-30 (follow-up)

Run by Claude in the real app on Windows 11 Pro 10.0.26300, Python 3.11.9, PySide6 6.9.0 (Qt 6.9.0), off-screen in disposable profiles, after merging `main` `1662d9d` (#115, #117) into this branch without conflicts.

- **Matrix:** 132 captures: Studio, Speech, Sounds, Voices Library, Clone, Design, Remix, Transcribe, Live, Models and Settings, in dark and light, at 1366x768 and 1920x1080, at 100/125/150%. Every page shows its own wave scene, behind the controls, with no crashes. 1366x768 at 150% (911x512 logical) is below the window minimum and is **not supported**; 125% now fits (`MIN_WINDOW` 960x560).
- **Take list (real window):** same-second takes get distinct names (“variation 1/2”, “2/2”); Enter and double-click both play the row; refreshing keeps the selection; Add to Studio adds the selected take, or the newest when none is selected, never a stale player path.
- **Defects found and fixed (each with tests):**
  - `tests/test_studio_page.py` had a syntax error (doubled line continuations), so 14 Studio tests never ran; fixed (`e83edd5`).
  - Closing while a Hugging Face model search ran destroyed a running thread at exit (exit code 127); the window now waits for it (`e83edd5`).
  - The wave backgrounds were invisible on cards and mesh-like; redrawn as long, spaced contours that also show faintly through cards (`b9c76b7`).
  - Access violations during voice renders traced to Python event filters running alongside engine threads; the empty-list hint and the wheel guard no longer use them (`a68a48d`, `0f59896`). Before: 2 crashes in 2 runs; after: none in every later session. The exact root cause inside PySide is not proven.
  - Speech's Model picker kept naming the last model picked there when a model was loaded another way (voice pick, Models, Voices); it now shows the loaded model (`d9e8179`).
- **Media:** the #118 set was recaptured on this build as the narrated film *A World in Sound: Evening Tide, The Beacon*; see `docs/marketing/MANIFEST.md`.

## Exact-head Windows acceptance checklist

Status after the follow-up above: items 1 to 5 and 7 done (see PR #120 for the exact-head suite run); item 6 done for Speech and Sounds import into the Studio with real media in disposable profiles.

- [ ] On the new exact PR head, run `python -m unittest discover -s tests -v`; record interpreter, PySide6 and Qt versions, pass/fail/skip counts.
- [ ] Verify no crashes on initial startup and successive navigation Studio → Speech → Sounds → Voices/Library → New voice/Clone → Design → Remix → Live → Models → Settings.
- [ ] Confirm scene changes are subtle, visible, static and behind editable UI; no lost mouse/keyboard focus; no splash/static effect.
- [ ] Compare against owner-selected reference art at 1366×768 and 1920×1080, 100/125/150% scaling, dark/light; inspect per-page cards, timeline, header/footer, scrollbars, focus and empty states.
- [ ] Verify audio output rows with two same-second takes have unique titles and remain clickable; Enter and double-click work; refresh keeps selection; Add to Studio imports the selected item or newest visible item.
- [ ] Confirm actual Studio narration and Sounds import remain correct after UI changes, with real media, no stale-path risks or user data mutation.
- [ ] Inspect for old unqualified media or technical strings resurfacing. Re-capture #118 only after this QA passes.

## Release controls

- #120 is stacked onto #119 and should not be merged directly into main without reviewing the base.
- #113 still needs a compatible rebase around project editor / model-ownership paths, independent of this styling work.
- #115 waveform math is independent but needs exact-head Windows waveform/trim checks.
- No hosted GitHub Actions, publication, user data mutation, studio refactor or owner media approval is part of this pass.
