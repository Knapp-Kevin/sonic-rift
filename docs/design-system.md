# Sonic Rift design system

One small set of rules for every page and dialog. The tokens live in `this_voice_thing/ui/theme.py`;
the shared parts live in `this_voice_thing/ui/widgets.py`. Add to these instead of styling one page.

## Identity
Professional, restrained creative-audio studio. Night-navy surfaces, one cyan accent, the
cyan → blue → violet brand stroke only on progress. Status colours (green, amber, red) mean status only.

## Layout
- **Page** = title (`PageTitle`), one-line subtitle (`PageSubtitle`), then cards. Every page sits in a
  scroll area (`main_window._make_pages_scroll`); a page never sets the window's size.
- **Window minimum** is fixed at 960 × 600 (`SonicRiftApp.MIN_WINDOW`), so the app fits a 1366 × 768
  laptop and 1920 × 1080 at 150 %. A saved size is clamped to the screen on start.
- **Card** = one job, a short bold title (`CardTitle`), its controls, and **one action row** at the bottom.
- Dialogs that are workspaces (the project editor) use the same page header and action-row rules.

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
Every list that can be empty gets `set_empty_text(view, "…")`: one sentence saying what will appear
and how to make it appear. No blank boxes.

## Inputs
Inputs share one height, radius (7 px) and border. Spin boxes use the chevron up/down buttons;
combo boxes the chevron. Sliders show their value at the right.

## Wording
- Status bar messages are plain sentences; the bar adds no "Status:" prefix.
- Never show internal ids, hashes, revision numbers, repo paths or backend names in normal UI; keep them
  in tooltips or the Settings log.
- Errors say what happened and what to do next (see `project_editor.describe_error`).
