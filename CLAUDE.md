# Claude Code instructions

## Windows code signing

Windows binaries and installers this repository distributes **must be Authenticode-signed at release time** with the MythologIQ Labs Azure Artifact Signing profile. Signing is available and verified, so don't ship an unsigned public Windows release.

- Endpoint `https://eus.codesigning.azure.net/`, account `MythologIQ-Labs-Signing`, certificate profile `mythologiq-labs-public-release` (Public Trust). Publisher shown to users: `MythologIQ Labs, LLC`. Timestamp server: `http://timestamp.acs.microsoft.com`.
- Canonical procedure, verified tooling and framework integration: `MythologIQ-Labs-LLC/Myth-Tech-Forge` at `docs/WINDOWS_CODE_SIGNING_STANDARD.md`. Follow it; don't invent another signing path.
- Sign release builds only (release tag or manual release), never PR or routine CI builds. Windows runners bill at 2x Actions minutes.
- Signing requires the Artifact Signing Certificate Profile Signer role. The owner's local `az login` identity has it, and so does the GitHub OIDC app `github-sonic-rift-signing`, but only from this repository's `release` environment (owner approval, `v*` tags only). Creating any other identity, secret or role assignment needs owner approval. Never commit credentials.
- A release is signed only after `signtool verify /pa` passes, the signer is `MythologIQ Labs, LLC`, and the signature is timestamped. Record that output in the release evidence.

**This repository:** `packaging/windows/` builds the Inno Setup installer, and `.github/workflows/release-windows.yml` signs and verifies it for `v*` tags. The installer and its uninstaller are the signed files. Bundled third-party binaries (uv) keep their publishers' signatures. See `packaging/windows/README.md`.

## Issue tracker

The authoritative tracker is [GitHub Issues](https://github.com/Knapp-Kevin/sonic-rift/issues). Read [docs/agents/issue-tracker.md](docs/agents/issue-tracker.md), especially its **Wayfinding operations** section, before charting a large effort or editing the Wayfinder map. Keep decision tickets separate from executable delivery issues and do not claim native issue dependencies unless they have actually been set and verified.
