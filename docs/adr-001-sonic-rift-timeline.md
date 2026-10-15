# ADR 001: Versioned Sonic Rift audio projects and layered Create timeline

**Status:** Accepted direction from owner in #71; **schema foundation proposed in this PR**, later rendering/UI decisions subject to acceptance.
**Date:** 2026-10-15
**Track:** #71 (project composer), #53 (sound production), #56 (application architecture), #61 (source-based Windows QA).

## Context and constraints

Sonic Rift currently supports Create/narration, saved voices, Sounds generation and a sound asset library, mastering/export, and Live Voice. None constitutes a saved layered arrangement. Adding a timeline directly to Qt generation callbacks would couple project state, media identity and rendering to a UI implementation we are still refactoring.

The owner's accepted product direction is one Create workspace with voice, sound and effect tracks, re-openable projects, fades/ducking, preview, WAV master and optional stems. An actual packaged Windows EXE, code signing and Microsoft Store publishing are **P4 deferred**. Existing source-launched workflows and user data must be preserved.

## Decision A: a Qt-free, versioned project document

The first implementation slice is `core/audio_project.py`:

- **AudioProject**: stable ID, title, integer sample rate (44.1/48 kHz), format version 1, edit revision, ordered tracks.
- **Track**: stable ID, voice/sound/effect capability kind, name, mute and gain, ordered clips.
- **Clip**: stable ID, kind, start and length in *integer PCM sample frames*, optional opaque asset ID, optional unrendered narration text/voice ID, gain, fades and loop flag.
- **Files**: explicit user-chosen `*.sonicrift.json` document. JSON stores edit intent and asset identifiers, **not** embedded PCM or absolute paths. Source assets remain in their respective libraries; a future resolver verifies hash/provenance and reports missing assets rather than resolving arbitrary paths from the project.
- **Compatibility**: `new_voice_project()` represents an existing Create text prompt as a single unrendered voice track. It does **not** modify existing settings, move recordings, change the Create UI, or automatically migrate saved user data.
- **Durability**: validate first, then write a temporary file in the target directory, flush/fsync and atomically replace the destination. Invalid or future-version projects fail closed, without attempting to rewrite them. No automatic downgrade.
- **Safety**: reject unknown schema versions, nonfinite gain, duplicate IDs, invalid frame lengths, unsafe asset identifiers and malformed nested structures. Allow unrendered narration to have zero frames until generated.

`revision` is a persisted edit counter only. This slice does **not** implement concurrent-write detection, an undo stack or automated migrations; subsequent edits must address them before UI-enabled saves. The project file is not a copy of the audio files and should not be advertised as a self-contained portable bundle.

## Decision B: deterministic mixing pipeline (next implementation slices)

1. **Source resolver**: map a clip's opaque `asset_id` to a known voice output or `AssetLibrary` entry. Verify existence, media checksum, licensing/provenance where applicable, and sample format. Never interpret the ID as a filesystem path supplied by the document.
2. **Timebase**: project frame indices are canonical. Resample media to the project sample rate exactly once per clip; align starts/fades/loops by frames, not floating-point seconds.
3. **Track render**: respect mute, gain, fades, silence, overlap and approved looping; render in bounded PCM chunks where memory warrants. A missing source blocks export with a clear error, not a silent substituted mix.
4. **Speech-aware ambience ducking**: compute envelope from actually rendered speech, not raw input text. Proposed adjustable attack/hold/release and max attenuation; duck **sound/ambience** tracks but not narration or global monitor paths. Persist parameters at project/track level in **schema v2 or a separately versioned extension**, rather than silently appending fields to v1.
5. **Mastering**: reuse `core/soundscape/mastering.py` for LUFS and peak limiting. Measure after summing and ensure output format does not clip. Export a single mixed WAV master, optional MP3/OGG, and optionally one stem per audible track plus a manifest.
6. **Undo/redo**: command-based reversible edit operations on an in-memory immutable/snapshotted project state; limit memory, validate before commit, and increment revision on accepted edits. No mutation of rendered source assets during timeline edits.

## Decision C: UI composition and non-destructive rollout

Keep the current Create, Voices, Sounds, Live and Models navigation intact. Introduce project mode behind an explicit action instead of silently replacing the existing single-text generation workflow. A loaded project shows transport/playhead, ordered voice/sound/effect tracks, clip blocks, in-place generation, asset browser, inspector (gain/fades/loop), undo/redo and mix/stem export.

Generation jobs use existing provider-neutral dispatch and existing cancellation/error contracts. Async result handling must verify project revision and clip ID before assigning a new asset, preventing a delayed job from overwriting another clip after the user changes selection.

Saved source settings, voice library, model cache, `sound_library`, audio outputs and old `models.json` remain where they are. The project adapter uses those existing libraries without moving them or making the UI dependent on a model install.

## Bounded acceptance sequence

| Slice | Scope | Exit evidence |
| --- | --- | --- |
| **1. Project document** (this PR) | Schema, strict validation, atomic persistence and opt-in legacy text conversion | Deterministic tests, malformed/untrusted input, no-touch source data, round-trip two tracks, save failure rollback |
| **2. Source resolver and timeline mix** | Library-backed PCM load, resampling, frame-accurate clip placement, overlap/fade/loop, stem export | Synthetic signals with exact sample timing, mismatched rates, missing asset, clipped peaks, multiple tracks; isolated outputs |
| **3. Speech ducking and mastering** | Speech envelope, bounded duck gain, attack/release, LUFS/true-peak master | Automated envelope and loudness tests, stereo null checks, human audition of voice+ocean demo |
| **4. Create project UI** | Explicit project create/open/save, track/clip editing, generation and cancellation, undo | Windows GUI regression, persistent settings/library, local representative engines; no test writes to live data |
| **5. End-to-end milestone** | Gentle Ocean Waves with calm narration: saved/reopened, mixed WAV and separate stems | Real audio clip playback, duration/sample-rate/loudness and provenance, reopen/edit/re-export parity; adversarial review |

No phase is considered shipped merely because the schema exists, a PR was opened, or generated data passes serialization. #71 stays open until the milestone works inside the real Sonic Rift application.

## Rejected approaches

- **All-in-one new Qt timeline before a project format:** impossible to validate durable edits independently, high risk to working Create.
- **Store absolute audio paths directly in project JSON:** unsafe, nonportable, easy to break through data moves and unrelated Windows accounts.
- **Treat generated assets as immutable snapshots embedded in JSON:** bloated documents and duplicate asset management; reuse the current library/provenance layer.
- **Block the composer on Windows EXE packaging/signing:** explicitly contrary to the owner's P4 distribution priority.

## Open implementation questions

Exact export folder user experience, stem naming and provenance contract, automation curves, media link migration for existing voice outputs, project conflict/backups, huge-session memory bounds, and audio-device preview scheduling require tested follow-up decisions. Record each in #71 rather than claiming schema v1 already provides those capabilities.
