> **Release transition checkpoint (2026-11-03):** v0.9.1 tag is now at commit `9e5ded1fba5d0f9f19b5c1ed32253a74ac087696`. Signed Windows installer workflow run [41720271010](https://github.com/Knapp-Kevin/sonic-rift/actions/runs/41720271010) passed and attached `SonicRift-Setup-0.9.1.exe` (GitHub asset SHA-256 `f5f192c1da11b24e0b3d093efeecb0aaf2c15b30bc2ee395b2f4cecc2d968456`). **However the GitHub Release is still DRAFT at inspection time**, not a published download. Use the **v0.9.1 tagged commit** for the next rehearsal. Once the draft is published and the signed installed application passes acceptance, use that exact released installer/build for final capture. Do not call the older `06ff4c0` dev SHA the release baseline or update website download links before the GitHub Release is public. No recording starts solely because the tag or CI is green; creative approvals and exact installer verification remain required.

> **Release published (2026-11-03, follow-up to the note above):** the v0.9.1 GitHub Release is **public** as a **pre-release** (published 21:24 UTC): <https://github.com/Knapp-Kevin/sonic-rift/releases/tag/v0.9.1>. An anonymous download of `SonicRift-Setup-0.9.1.exe` has SHA-256 `f5f192c1da11b24e0b3d093efeecb0aaf2c15b30bc2ee395b2f4cecc2d968456` and a Valid, timestamped Authenticode signature by MythologIQ Labs, LLC. The signed installer passed a clean install, a first launch and a signed uninstall on Windows 11; its files match tag `v0.9.1` in content. The same commit passed 679 tests and the real-app acceptance from source. **Final capture uses this released installer** (see SCRIPT_LOCK.md "Recording baseline"). Recording still waits for the creative approvals and the logo check.

# Claude start here: Sonic Rift film revision
**Status:** PREPRODUCTION READY FOR LOCAL REHEARSAL; FINAL FILM NOT APPROVED.  
**Do not use the rejected image-generated storyboard sheets, ZIP, lighthouse art or alternate logo.**  
**Only permitted visual sources:** actual Sonic Rift recorded UI, approved Sonic Rift media at `docs/marketing/`, and the exact silver MythologIQ mark used by the website revamp. No image generation is delegated to Claude.

## One-time source checkout
- Sonic Rift repository: `Knapp-Kevin/sonic-rift`, production script branch `docs/demo-production-packs-20261103-no-ci`.
- Authoritative existing approved video and screenshots: **this repository's main branch** `docs/marketing/` and `docs/marketing/MANIFEST.md`, owner approved 2026-10-30.
- Silver brand mark is in **another already-published GitHub repository**, `Knapp-Kevin/MythologIQ`. At reviewed revamp branch `feature/sites-sonic-rift-reconciled-20261102-no-ci` commit `6b655b69c51d6d7e4dde4851e6433be8609305b5`, site header `src/studio/StudioHeader.tsx` displays `public/assets/studio-20261030-v76/mythologiq-silver-concept.webp` with separately rendered wordmark. Verify against the owner's supplied image (silver crescent, star and feather). **Use the exact file, not a generated imitation or the old `header-logo.webp`.** If it differs, STOP brand animation work and ask for the correct source asset. Do not pretend the website version is approved without visual comparison.
- Existing approved Sonic Rift end card: `docs/marketing/logo/sonic-rift-end-card.png`. Reuse it until a new end card is explicitly approved.

## Visual assets that Claude already has access to in GitHub
| Production purpose | Repository path | Status |
|---|---|---|
| Main source film, for timing review | `docs/marketing/video/sonic-rift-beacon.mp4` | Approved reference; never overwrite |
| Soundless version, for comparison | `docs/marketing/video/sonic-rift-beacon-silent.mp4` | Approved reference |
| Existing poster frame, no AI art required | `docs/marketing/video/sonic-rift-beacon-poster.jpg` | Approved real app image |
| Empty Studio opening image | `docs/marketing/screenshots/sonic-rift-studio-empty-dark.png` | Approved real app |
| Completed Studio screen | `docs/marketing/screenshots/sonic-rift-studio-dark.png` | Approved real app |
| Product logo end card | `docs/marketing/logo/sonic-rift-end-card.png` | Approved |
| Narration and synthetic character lines | `docs/marketing/audio/01-*.wav` through `13-*.wav` | Existing approved audio |
| Voice sources | `docs/marketing/audio/voice-designs/` | Approved, license-provenance in manifest |
| Captions and transcript | `docs/marketing/video/sonic-rift-beacon.en.vtt`, `docs/marketing/video/transcript.md` | Existing starting point |
| New studio-ident/logo master | `Knapp-Kevin/MythologIQ/public/assets/studio-20261030-v76/mythologiq-silver-concept.webp` at pinned website SHA | Requires reference visual match |

The existing film and its poster already depict *Evening Tide: The Beacon*. **Opening still decision:** use the real empty Studio frame instead of the rejected AI-generated lighthouse picture; cut immediately to actual app. Do not block this film on unapproved illustration. If the owner later provides a suitable cinematic lighthouse still, replace the intro only via a separate approved revision.

## What Claude is authorized to do
1. Read `SCRIPT_LOCK.md` (the explicit full scene-by-scene narration, captures and audio cues); then inspect the existing approved video/manifest.
2. Run Sonic Rift on Windows, capture genuine application footage and screenshots, verify actual music generation and playback path, generate original audio **inside Sonic Rift**, and keep stems. Do not synthesize pictures, logos, mock UI, or brand graphics.
3. Verify the existing installed alpha build's features and each script action before recording. If a capability fails, report the exact blocker and submit an explicit script correction. Never film a fake success.
4. If a brand ident cannot be rendered from a verified existing approved mark with available local tooling, use a static 2-second title card displaying the **exact** mark. Do not delegate illustrative asset creation or ask for an AI image.
5. Assemble revised footage **only using existing local capabilities that you actually have**; if you can record but cannot edit or encode the final movie, hand off raw recordings, WAV stems, timestamped edit decision list and timing notes; do not claim a final MP4 was produced.
6. Review output audio synchronization, silent gaps, narration intelligibility, rights, captions and screenshots. No publication, branch merge, CI, or Netlify deployment.

## Required starting checkpoint
Before any final capture, report: pinned application SHA/version; local asset resolution (file exists/hash); visually confirmed silver-logo match (or a BLOCKER); old-film dead-air timecodes; Sonic Rift music generation/import/export results; and proposed script edits. The owner must approve a changed script or creative identity before final recording.

This file supersedes any older instructions suggesting Claude should make opening illustrations or fabricate a new MythologIQ brand animation.
