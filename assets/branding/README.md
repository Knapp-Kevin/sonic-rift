# Sonic Rift visual identity

## Concept
A luminous circular rift around an audio waveform. The wave denotes voice and sound; the rift suggests creative worlds, whether fantasy, sci-fi, relaxation or live production. The art is illustrative, not a screenshot or evidence of a released capability.

## Naming and copy
- Product name: **Sonic Rift**
- Tagline: **Make worlds you can hear.**
- Category: **Local-first creative audio**
- Visual labels: **Voice · Soundscapes · Audio Studio**
- Do not suggest every planned layering and composition workflow is already release-tested.

## Brand tokens
| Role | Value |
| --- | --- |
| Night | `#0B1020` |
| Navy surface | `#111B35` |
| Cyan | `#22D3EE` |
| Electric blue | `#4F7BFF` |
| Violet | `#A78BFA` |
| White | `#F2F5FF` |
| Muted text | `#BFCBE5` |

Font: Inter Display and Inter where available, standard sans-serif fallback. Keep status/warning colors semantically distinct from decorative brand colors.

## Editable assets
- `sonic-rift-banner.svg`: 1600 × 500, intended as README hero.
- `sonic-rift-social-preview.svg`: 1280 × 640, source for a JPEG/PNG GitHub repository social preview.
- `sonic-rift-logo-lockup.svg`: 1200 × 340, horizontal wordmark + symbol.
- `sonic-rift-symbol-candidate.svg`: 512 × 512, **candidate only**, not the shipped app icon.

Render the SVG masters to PNG/JPEG at their original viewBox dimensions. Review exports at 100% and at thumbnail sizes.

## Migration guardrails
1. **Preserve the current application icon.** The runtime still references `assets/branding/this-voice-thing-app-icon.png`, and the fallback is `assets/logo.svg`. Only replace either after visual owner approval and desktop/taskbar integration tests.
2. **Preserve historical binary assets and compatibility paths.** Existing `this_voice_thing` imports, launch entrypoints, output folders and old filenames are not visual branding debt to solve in this PR. Do not rename them as a side effect.
3. The SVG masters are versioned here. **The repository's actual GitHub social preview is a Settings upload**, not controlled by tracked repository files. Use the JPEG/PNG export in GitHub Settings → General → Social preview.
4. Repository description, topics, distributions and executable names require a separate metadata/packaging transition under #60.
5. Preserve upstream copyright notices and provenance; this project has Chatterbox lineage.
