# Third-party notices and provenance

Sonic Rift is a locally run creative-audio application. **The product name and branding are independent of its historical source ancestry.** This file records third-party relationships without turning those relationships into the application's public identity.

**Sonic Rift is licensed under the [Apache License 2.0](LICENSE)** (see [NOTICE](NOTICE)). This file lists the third-party code, engines and models it relates to.

> **Important:** This is an attribution index, **not** a source-code license, a legal-clearance opinion, a complete software bill of materials, or a substitute for any license text required when distributing the application, its dependencies, or model weights.

## Historical source code

Sonic Rift began as a fork of [AcTePuKc/Chatterbox-TTS-UI](https://github.com/AcTePuKc/Chatterbox-TTS-UI) (MIT). By version 0.9.0-alpha every part inherited from it had been rewritten or removed; the [completion record](docs/independence-2026-11-02.md) lists what was replaced and the similarity evidence, and a test keeps it that way. Commits up to that point in this repository's history contain the upstream code with its MIT license, as published.

GitHub's fork-network relationship is separate from authorship and licensing. Preserve issue, pull-request and review history before any irreversible network detachment.

## Engine packages and models

The application integrates or can install third-party speech and sound engines. **Source-code licenses, downloaded model-weight licenses, and rights relating to input/output media are separate.** Optional engines can have additional distribution, commercial-use, attribution or research-only restrictions.

| Component | Source or reference | Notice / release action |
| --- | --- | --- |
| Resemble AI Chatterbox TTS | [Engine repository](https://github.com/resemble-ai/chatterbox) | Check the installed package's MIT notice and model license. Chatterbox is an optional engine, not the Sonic Rift product identity. |
| Qwen3-TTS | [Engine repository](https://github.com/QwenLM/Qwen3-TTS) | Verify current package and selected model weight terms independently. |
| VoxCPM2 | [Engine repository](https://github.com/OpenBMB/VoxCPM) | Verify current package, extras, transitive dependencies, and weight terms. Do not reintroduce nonredistributable evaluation-only packages into release bundles. |
| OmniVoice | [Engine repository](https://github.com/k2-fsa/OmniVoice) | Check weights separately; existing project inventory flags noncommercial restrictions for the pretrained model. |
| VibeVoice | [Engine repository](https://github.com/microsoft/VibeVoice) | Check model-card use restrictions independently of any permissive code license; the existing inventory flags research-use conditions. |
| Kokoro and Misaki | [Model](https://huggingface.co/hexgrad/Kokoro-82M), [text frontend](https://github.com/hexgrad/misaki) | Retain relevant package and model notices; verify optional plugin dependencies in packaged builds. |
| MOSS-SoundEffect | [Model repository](https://huggingface.co/OpenMOSS-Team/MOSS-SoundEffect-v2.0) | Verify actual downloaded checkpoint and dependency licenses; do not assume a model license covers bundled libraries. |
| PySide6, PyTorch, FFmpeg and other libraries | Installed environment and their respective publishers | Generate a pinned runtime dependency inventory and collect the required distribution notices before release. DLL/binary redistribution can have additional requirements. |

This table is a **starting index**, not an assertion that every listed engine is installed, redistributable or commercially cleared. Do not automatically ship downloaded model weights inside a release package.

## Sonic Rift source license: Apache-2.0

On 2026-10-31 the owner relicensed Sonic Rift under the [Apache License 2.0](LICENSE). All post-fork commits are by the owner, Kevin Knapp. The change applies from that commit forward; earlier commits stay available under the MIT terms they were published with.

The [independence work](docs/independence-2026-11-02.md) (#55, #57) replaced all code inherited from Chatterbox-TTS-UI, so the upstream MIT notice no longer applies to the current tree.

The Apache-2.0 license covers Sonic Rift's own code only. It does not relicense optional engines, their dependencies or model weights, which keep their own terms (see above and [issue #60](https://github.com/Knapp-Kevin/sonic-rift/issues/60)). Clean-room status is **not** claimed.

## Source-based installed-environment checks

A [read-only dependency metadata inventory](docs/runtime-license-inventory.md) and [offline script](scripts/audit_runtime_licenses.py) allow the project's actual Windows app/engine Python environments to be inventoried without installing packages, importing speech models, or relying on a historical package snapshot. Package metadata alone **cannot** establish commercial-use clearance. Review actual package license files and model-weight terms before making rights claims.

## Distribution verification checklist

- [ ] Freeze the exact release commit and dependency lockfiles used for packaging.
- [ ] Generate the real installed-package and distributed-binary inventory, including engine-specific environments.
- [ ] Confirm licenses and attribution for distributed fonts, images, sound assets and model weights.
- [ ] Ship full required license/notice text for all components actually redistributed.
- [ ] Check noncommercial, research-only, conditional-use, and evaluation-only components against proposed distribution.
- [ ] Record the approved license scope for independently owned Sonic Rift source.
- [ ] Audit an actual build on Windows and record owner release approval.

Do not mark this checklist complete on the strength of a README edit or repository rename.
