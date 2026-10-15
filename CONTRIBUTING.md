# Contributing to Sonic Rift

Thanks for helping improve **Sonic Rift**, a local-first desktop studio for voice, soundscapes and audio production. Reports, documentation corrections, accessibility improvements and tested code are welcome.

## Reporting a defect or suggesting a feature

Use the [Sonic Rift issue tracker](https://github.com/Knapp-Kevin/sonic-rift/issues). Include a concise description, reproduction steps, expected and observed behavior, application commit/version, OS, Python/PySide6/PyTorch versions and selected engine. Logs and screenshots help, but **remove secrets, audio you cannot share, user names and private file paths**. For device problems include the relevant playback/recording format and whether the engine is installed.

For a significant change, check existing issues and open one before implementing. Please don't create a parallel PR for work already assigned or underway.

## Development workflow

1. Fork the [Sonic Rift repository](https://github.com/Knapp-Kevin/sonic-rift) into your own account and clone your fork:

   ```bash
   git clone https://github.com/YOUR-NAME/sonic-rift.git
   cd sonic-rift
   git remote add upstream https://github.com/Knapp-Kevin/sonic-rift.git
   ```

2. Install Python 3.11 and `uv`. On supported Windows development machines use `run.bat` for bootstrapping; `run.sh` exists for experimental macOS/Linux use. Model installations and weights may be large and have separate license conditions. Download only what your test requires.
3. Make changes on a focused branch. Do not rename the `this_voice_thing` Python package, storage paths, or Windows AppUserModelID casually; those names still support existing installations and shortcuts.
4. Run the applicable unit tests, then manually validate UI/audio changes on supported equipment. The full Python suite is:

   ```bash
   python -m unittest discover -s tests -v
   ```

   Use the project's `.venv` interpreter when dependencies are required. Document any blocked hardware/engine cases instead of claiming they passed.
5. Submit a focused pull request against `main`. Link its issue, describe behavior, tests executed, screenshots or measurements where relevant, provenance/permission changes and exact limitations. Fix blocking review findings before asking for merge.

**Important:** This repository conserves GitHub Actions usage. Avoid introducing or broadening hosted workflows and never trigger large model downloads in CI without maintainer approval. Prefer local deterministic tests where practical.

## Architecture and data safety

- `this_voice_thing/ui/` contains the desktop window, pages, dialogs, theme and Qt workers.
- `this_voice_thing/core/` contains provider-independent audio, model selection, project data and utility contracts.
- `this_voice_thing/engines/` contains adapters and isolated engine workers.
- `this_voice_thing/integrations/` contains the local API and optional document integrations.
- Saved recordings, model caches, settings, voices and sound assets belong to the user. Use scratch data, preserve compatibility and test rollback paths.

Feature work must preserve optional-provider isolation. An absent Chatterbox TTS installation must not prevent unrelated engines from starting.

## Source provenance and licensing

Sonic Rift has its own product identity but contains some adapted third-party source. The repository's [LICENSE](LICENSE), [third-party notice index](THIRD_PARTY_NOTICES.md), and [provenance audit](docs/upstream-provenance-audit.md) document current limitations and retained notices.

- Only submit code or assets you have permission to contribute. Document imported code, external snippets, model weights and third-party assets, including their licenses and source.
- Do not delete copyright headers or replace required notices as part of refactoring or rebranding.
- Do not assume changing a file name, rewriting a function superficially, or detaching GitHub's fork network grants new copyright ownership.
- Do not bundle models with noncommercial, research-only, conditional, or unclear terms into distributable packages without review.
- The license for independently owned future work remains subject to an explicit owner decision. A pull request does not by itself settle any relicensing or contributor-license arrangement.

## Community conduct

Be respectful, constructive and specific about technical disagreements. Report security concerns responsibly without publishing credentials or sensitive data.

Thank you for contributing to Sonic Rift.
