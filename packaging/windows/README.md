# Windows installer

`build-installer.ps1` builds `dist/SonicRift-Setup-<version>.exe` with [Inno Setup 6](https://jrsoftware.org/isinfo.php).

## What the installer contains

- The committed app files from `HEAD` (via `git archive`), without tests, docs or the macOS and Linux scripts.
- `launch-sonic-rift.cmd`, which the Start menu shortcut runs.
- uv, pinned by version and SHA-256 in `build-installer.ps1`, so users don't have to install Python or uv themselves.

Python 3.11, PyTorch and the other dependencies are **not** bundled. On first launch, `launch-sonic-rift.cmd` uses the bundled uv to find or install Python 3.11, then runs `run.bat` exactly as a source checkout does. Bundling PyTorch would push the installer past GitHub's 2 GB release-asset limit.

The installer is per-user (no admin prompt) and installs to `%LOCALAPPDATA%\Programs\Sonic Rift`, because the app writes its environments and logs next to itself. Uninstalling removes the app, `.venv`, `logs` and `__pycache__`. Engine environments under `engines\`, generated audio, settings and the model list (`models.json`) stay. Installing over an existing copy (an upgrade) replaces the app files but never resets `models.json`, which the Models page writes.

## Build locally

```powershell
powershell -ExecutionPolicy Bypass -File packaging/windows/build-installer.ps1 -Version 0.1.0
```

## Signing

Release installers are Authenticode-signed with the MythologIQ Labs Azure Artifact Signing profile, following [the Windows code signing standard](https://github.com/MythologIQ-Labs-LLC/Myth-Tech-Forge/blob/main/docs/WINDOWS_CODE_SIGNING_STANDARD.md). `-Sign` signs both the installer and its uninstaller through the Azure CLI sign-in. Locally, that means `az login` as an identity with the Signer role, plus a .NET 8 runtime:

```powershell
powershell -ExecutionPolicy Bypass -File packaging/windows/build-installer.ps1 -Version 0.1.0 -Sign -SigningClientDir <Microsoft.ArtifactSigning.Client package folder>
powershell -ExecutionPolicy Bypass -File packaging/windows/verify-signature.ps1 -Path dist/SonicRift-Setup-0.1.0.exe
```

## Releasing

Push a `vMAJOR.MINOR.PATCH` tag. `.github/workflows/release-windows.yml` waits for the owner to approve the `release` environment, signs in to Azure with GitHub OIDC (no secrets), builds, signs and verifies the installer, and attaches it with a SHA-256 file to a **draft** GitHub Release. Publish the draft after checking it.

Tag a commit whose message doesn't contain `[skip ci]`. GitHub skips push-triggered workflows, tag pushes included, when the tagged commit's message has it, and then no release run starts. Docs-only changes don't trigger the other workflows (they're path-scoped), so a docs commit without `[skip ci]` is a safe thing to tag.
