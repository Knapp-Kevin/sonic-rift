# Sonic Rift UI cohesion audit — 2026-10-16

**Method:** I drove the running Windows app from a scratch profile with Kokoro loaded. Every page was captured in light and dark themes, at 1366 × 768 and 1920 × 1080, and at Qt scale factors 1.0, 1.25 and 1.5. Windows display scaling itself was not changed.

**Measurements:**
- Each page's minimum size, read from the live widgets.
- The number of visible controls per page, and how each button is styled.

**Screenshots:** `docs/ui-audit/*-before.jpg` and `*-after.jpg`. The "before" captures were requested at 1366 × 768 but came out at 1740 × 1515, because the window would not shrink. That is finding 1.

**Code commit:** the pass that addresses findings 1–7 is `6508142` + `f298c58` (PR #101, stacked on #99).

## Findings, ranked by impact

Each finding records:
- the user-visible problem;
- where it occurs and how often;
- why it hurts;
- the Qt cause;
- the fix and its cost;
- whether it is systemic or isolated.

### 1. The window can't fit the screen. Systemic. Fixed.
- **Problem:** the app opens taller than the screen and can't be resized smaller. The owner reported this.
- **Where:** every page, all the time. The minimum window size was **1740 × 1515 px**. The owner's work area is 3440 × 1392, and a 1366 × 768 laptop can't show the window at all.
- **Why:** the bottom of every page is off-screen, including the status bar and the soundboard.
- **Qt cause:**
  - `main_window.update_minimum_size()` grew the window to `minimumSizeHint()`. This was a deliberate inherited rule: "so nothing ever clips or scrolls".
  - All pages share one `QStackedWidget`, so the largest page sets the minimum.
  - Live alone needed 1560 × 1489.
- **Fix:** every page sits in a `QScrollArea`, the window minimum is a fixed 960 × 600, and a saved size is clamped to the screen.
- **Cost:** about 60 lines.

### 2. No action hierarchy. Systemic. Fixed on Live and the project editor.
- **Problem:** pages are rows of equally weighted buttons and blue text links. Nothing says which action matters.
- **Where:** every page. Visible controls and button styles measured per page:

  | Page | Visible controls | Primary | Outlined | Text links |
  |---|---|---|---|---|
  | Live | **58** | 3 | 12 | **24** |
  | Sounds | 28 | 2 | 8 | 2 |
  | Create | 20 | 1 | 5 | 3 |
  | Models | 12 | 0 | 3 | 7 |
- **Why:** this is the main reason the app reads as "several developer utilities sharing a sidebar". Whether an action is a link or a button is arbitrary: "New…" is a button but "Delete board" is a link, and "Use current voice" is a button but "Clear voice" is a link.
- **Qt cause:** the only roles were the `_accent()` property and `_link()` (`setFlat`). Each page chose per button.
- **Fix:**
  - `widgets.set_role` (primary / secondary / tertiary / destructive) and `widgets.MenuButton`.
  - Rule: one primary per card, about five visible actions, and the rest in a menu.
  - Live drops from 24 text links to 2, through Queue, Board, Pad and Favorites menus that show the keyboard shortcuts.
  - The project editor drops from 15 equal buttons to 5 controls with one primary "Export mix…".
- **Cost:** medium. A shared part plus one page at a time; Create, Sounds and Voices remain.

### 3. Progressive disclosure is missing on Live. Isolated. Fixed.
- **Problem:** the Mic Effects card (microphone, gain, tone, compressor) is always shown, even when typing speech. Engineering labels ("Segmented streaming · Origin: default / current · Provenance: idle") share the voice row.
- **Where:** Live.
- **Why:** the most-used task, typing a line, is buried under controls for another mode.
- **Qt cause:** cards were built unconditionally; visibility didn't follow the Source combo.
- **Fix:** the Mic Effects card shows only in Mic Effects mode, and the details sit on one muted line.
- **Cost:** small.

### 4. Native controls broke the theme. Systemic. Fixed.
- **Problem:**
  - Spin-box up/down arrows rendered as a stray "┤" glyph.
  - Page scrollbars were plain Windows grey; only the model tiles had themed ones.
  - The project editor's tree view was unstyled.
- **Where:** Sounds (5 spin boxes), Voices › New voice, Live, Settings, the project editor.
- **Why:** this is what makes it look "assembled". These controls fall back to native Windows rendering inside a custom-styled app.
- **Qt cause:** the stylesheet styled `QSpinBox` borders but not `::up-button`/`::down-button`. When part of a complex control is styled, Qt stops drawing its native sub-controls.
- **Fix:**
  - Chevron sub-controls, using new `chevron_up_*.svg` assets.
  - One `QScrollBar` rule for the whole app.
  - `QTreeWidget` joins the list and input rules.
- **Cost:** small.

### 5. Empty states are blank boxes. Systemic. Fixed for lists.
- **Problem:** large empty rectangles: Sounds › Takes, Voices › New voice › Takes, Live › Queue and Soundboard, the Create player list, the project.
- **Why:** the user can't tell whether something failed or what to do next.
- **Fix:** `widgets.set_empty_text`, a one-sentence hint inside the list that disappears on the first row.
- **Cost:** small. The Voices library and the Models discovery area still need it.

### 6. Engineering vocabulary in normal UI. Systemic. Partly fixed.
- **Problem:**
  - The status bar read "Status: Model loaded from hexgrad/Kokoro-82M using kokoro on cuda. Ready."
  - The project editor showed "revision 15", "Clip b7c01071", asset hashes, and "post-duck premaster WAV stems".
  - Errors appeared raw: "Expecting value: line 1 column 34".
- **Why:** it exposes implementation detail instead of creative workflow.
- **Fix:**
  - `set_status_message` drops the "Status:" prefix in one place (94 call sites).
  - Model-ready now reads "Kokoro voices is ready on the GPU."
  - Editor wording and error mapping changed in PR #99.
- **Still to do:** generated files are named `chatterbox_YYYYMMDD_…_full_stitched.wav` in the Create player list. This is also leftover Chatterbox-era branding.

### 7. The project editor looked like a different product. Isolated. Fixed.
- **Problem:** a plain label for a heading, no page title, 15 identical buttons, "↑"/"↓" stretched across full-width buttons, and no primary action.
- **Fix:** the same page header (`PageTitle` / `PageSubtitle`), Add / Selection / Project menus, and a primary Export. It is non-modal, so Create stays usable (PR #99).

### 8. Information architecture. Open.
- **Duplicated controls:** Create has **two voice selectors**, the header chip "Preset: Heart · Change" and Delivery › Voice "Heart (US English, female)". They are the same setting in two places.
- **Too much nesting:** Voices › New voice nests three levels of tabs (sidebar → Library / New voice → Start: Clone / Design / Remix).
- **Empty space:** Models shows mostly empty space while "Searching Hugging Face…", plus an orphan "Fine-tuning defaults" card.
- **Discoverability:** the project editor is reached from a small text link ("Project…") under Create's header. If projects become the main way to work (#71), Create should open into the project.
- **Cost:** medium. These are workflow decisions for the owner and Quinn (#56), not styling.

### 9. Things that are already consistent
- The colour tokens and both themes: contrast is tested, and the semantic colours are kept separate from brand colours.
- Card, typography and sidebar treatment.
- Light/dark switching.

The stylesheet was not the problem. Layout policy, missing shared parts and wording were.

## Framework assessment: keep PySide6 Qt Widgets

**Question:** is PySide6 responsible for the lack of cohesion?

**Evidence: every top defect was caused by app code and fixed inside Qt Widgets.**

| Finding | Root cause | Fixed in Widgets? |
|---|---|---|
| 1. Window size | A grow-to-content policy in our code | Yes: scroll areas, about 60 lines |
| 2. Action hierarchy | No shared roles | Yes: `set_role` and `MenuButton` |
| 3. Disclosure | Page structure | Yes |
| 4. Native fallbacks | Incomplete QSS (a Qt rule, but well documented) | Yes: about 30 QSS lines |
| 5. Empty states | Missing shared part | Yes: an overlay helper |
| 6–7. Wording and editor | Content and structure | Yes |

**Prototype:** the visual project timeline for #71 (PR on `feat/project-timeline`) has lanes, clip blocks with real waveforms, fades, loop tiling, a ruler, a playhead synced to playback, and click-to-select/seek. It is about 250 lines of `QPainter` on one `QWidget`, themed from the same tokens. This is the most demanding "creative studio" surface the roadmap needs, and Widgets handles it without strain.

**Real Qt Widgets limitations, and their impact here:**
- **QSS:** no transitions or animations, no `box-shadow` or blur, and partial styling disables native drawing of sub-controls. Impact is low: shadows are already painted (`CardFrame`), and motion isn't central to an audio tool.
- **Custom rendering:** anything beyond standard controls is hand-painted, as the timeline was. Impact is moderate: it costs effort but has no ceiling.
- **High DPI:** fine at 1.0, 1.25 and 1.5 in the captures. Fonts are Segoe UI Variable through the stylesheet.

**Three paths compared:**

| | Refine Widgets (recommended) | Add QML for one surface | Replace the toolkit |
|---|---|---|---|
| Visual ceiling | High enough, as the timeline shows | Higher for animated or touch surfaces | Depends on the stack |
| Fit with the Python audio backend | Direct: same thread model, signals, QThread workers | A Python↔QML bridge (properties and models) for every bound value | A rewrite of 30+ page mixins and the worker plumbing |
| Accessibility | Native widgets with accessible names | QtQuick Controls are weaker on Windows UIA | Unknown |
| Risk | Low; incremental, tested per PR | Medium; two UI paradigms to maintain | High |
| Cost | Weeks of incremental passes | Months for the editor alone | Many months |

**Recommendation:** keep Qt Widgets and continue the design-system passes (Create, Sounds, Voices next, then the IA items in 8). Revisit QML only for one isolated surface, and only if we hit a demonstrated limit, such as smooth zoom and pan with hundreds of clips on the timeline. The current prototype shows no such limit.
