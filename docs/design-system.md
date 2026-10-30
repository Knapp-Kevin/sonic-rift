# Sonic Rift design system

One small set of rules for every page and dialog. The tokens live in `this_voice_thing/ui/theme.py`;
the shared parts live in `this_voice_thing/ui/widgets.py`. Add to these instead of styling one page.

## Identity
Professional, restrained creative-audio studio. Night-navy surfaces, one cyan accent, the
cyan → blue → violet brand stroke appears sparingly on progress and the thin sidebar identity rail. Status colours (green, amber, red) mean status only.

## Layout
- **Page** = title (`PageTitle`), one-line subtitle (`PageSubtitle`), then cards. Every page sits in a
  scroll area (`main_window._make_pages_scroll`) except the embedded Studio timeline, which manages its own splitter and scroll regions. A page never sets the window's size.
- **Window minimum** is fixed at 960 × 560 (`SonicRiftApp.MIN_WINDOW`), so the app fits a 1366 × 768
  laptop at 100 % and 125 %, and 1920 × 1080 at 150 %. 1366 × 768 at 150 % (910 × 472 usable) is below
  what the layout supports. A saved size is clamped to the screen on start.
- **Card** = one job, a short bold title (`CardTitle`), its controls, and **one action row** at the bottom.
- **Studio** is a permanent page at the top of the navigation (not a popup). Speech/Sounds are generators; Add to Studio returns the user to their growing project. The embedded editor follows page-header and action-row rules.

## Actions (`widgets.set_role`)
| Role | Looks | Use for |
| --- | --- | --- |
| primary | filled accent | the one action a card exists for; at most one per card |
| secondary | outlined (default) | ordinary actions |
| tertiary | text link | quiet, low-stakes actions next to what they affect (e.g. *Refresh devices*) |
| destructive | outlined, red text | actions that remove something; prefer putting them last in a menu |

Rarely used or related actions go in a **`MenuButton`** ("Queue", "Board", "Pad", "Project", "Add",
"Selection"), with keyboard shortcuts shown in the menu, rather than another row of links.
A card should not need more than about five visible actions.

## Lists and empty states
Every list that can be empty gets `set_empty_text(view, "…")`; tile areas use their own `empty_message`. Say what will appear and how to make it appear. No blank boxes.
- Recent audio takes show recognizable timestamps. When two output files share a timestamp, present stable, distinct variation labels without exposing a model seed; keep the original name discoverable in a tooltip.
- Keep the user's selected take during list refresh; when none is selected, Add to Studio uses the newest visible result, not an earlier played file. An activated take works through both Enter and mouse double-click.

## Inputs
Inputs share one height, radius (7 px) and border. Spin boxes use the chevron up/down buttons;
combo boxes the chevron. Sliders show their value at the right.

## Wording
- Status bar messages are plain sentences; the bar adds no "Status:" prefix.
- Never show internal ids, hashes, revision numbers, repo paths or backend names in normal UI; keep them
  in tooltips or the Settings log.
- Errors say what happened and what to do next (see `project_editor.describe_error`).

## Acoustic background surfaces (draft #120)

- The old randomly speckled grain has been replaced with static, low-contrast **sound wave contours and resonance rings**. Never introduce television-static noise as a substitute for material texture.
- All scene profiles share the same navy/cyan/violet identity and semantic palette; the **shape**, not the application's control colors, varies slightly by context: Studio (layered mix), Speech (directional flow), Sounds (fluid bed), Voices library (quiet), Clone (mirrored), Design (harmonic), Remix (interference), Transcribe, Live and neutral setup.
- These are decorative background patterns, never audio meters and never evidence that audio is playing. No animation, playback-driven flicker, or independent renderer threads.
- Preserve high contrast and calm negative space behind editing controls. On screen resize the effect may scale but must not push page minimum sizes. Avoid adding opaque full-page panels that accidentally hide the shared background.
- Follow Windows light/dark switches using the existing theme tokens. Keep foreground text contrast at least 4.5:1 against common page/card backgrounds. Do not recolor status roles for decoration.
- **Release gate:** the generated owner-selected artwork is reference art. The Qt-painted approximation in #120 must be compared against real Windows captures at 1366×768, 1920×1080 and 100/125/150% scaling. No claim of visual acceptance from passing unit tests alone. Done 2026-10-30 (132 captures; see `docs/ui-audit/2026-10-30-acoustic-background-and-ui-refinement.md`); owner visual sign-off still pending.

## Marketing capture readiness

The website walkthrough should demonstrate a **Studio-first creative journey**: make a piece in Speech or Sounds, return to Studio and show a newly added clip, then hear the finished arrangement. Keep voice identities distinct and visual actions genuine. Captures, soundtrack approval, wordmark typography, captions and rights live under #118. Recaptured 2026-10-30 on the qualified #120 build as the film *A World in Sound* (`docs/marketing/`); the first pass is archived under `docs/marketing/archive/2026-10-30-v1/`. New media stays a review candidate until the owner signs off.
