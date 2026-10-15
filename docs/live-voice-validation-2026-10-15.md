# Live Voice validation record — 2026-10-15

Follows [the QA runbook](live-voice-qa.md). Real devices, real models, driven in-process through the
Live page's own controls (Speak, Stop, pads, shortcuts, route arm) by a scripted harness; dialogs were
answered automatically and the local API server was not started. Audio was processed in memory only.

| | |
| --- | --- |
| Date | 2026-10-15 |
| Commit | `integrate/live-voice` (Live Voice #24 merged with main through #89), validated on 695ac66–4287dd0 |
| Windows | Windows 11 Pro 10.0.26300 (Smart App Control on) |
| GPU | NVIDIA GeForce RTX 5070 Ti, 16 GB |
| Python / PySide6 | 3.11.9 / 6.9.0 |
| Playback devices | S34J55x (HDMI, 44.1 kHz), Realtek Digital Output (USB, 48 kHz), HyperX QuadCast S (not used) |
| Recording device | HyperX QuadCast S microphone (48 kHz stereo) |
| Virtual audio driver | **none installed** |

## Results

| Runbook section | Result |
| --- | --- |
| 1. Unit suite | 288 tests OK |
| 2. Endpoints | 3 playback, 1 recording; names match the Live page |
| 4. Virtual microphone routing | **Not run — no virtual cable installed** |
| 5. VoxCPM2 native, 6 steps (default) | 8 warm runs: TTFA median 0.20 s, RTF median 0.86 (max 0.99), **0 underruns** |
| 5. VoxCPM2 native, 8 steps | 5 runs: RTF median 1.06; underruns on every run (slower than real time, as documented; status line warns) |
| 5. VoxCPM2 native, 10 steps | 5 runs: RTF median 1.19; underruns on every run (as documented) |
| 6. Kokoro segmented | 10 warm runs: TTFA median 0.27 s, RTF median 0.03, **0 underruns** |
| 7. Buffered fallback | Not run separately (Chatterbox/Qwen/OmniVoice) |
| 8. Cached soundboard | Pad builds in ~2.8 s; cached replays reach the sink in < 20 ms and play with the model unloaded; Clear cache → "rebuild needed" → re-trigger rebuilds; provenance survives caching. Audible latency adds the 150 ms start buffer on a drained sink, so the ≤ 100 ms target is **not demonstrated** |
| 9. Queue and shortcuts | Queue holds at 25 outstanding items ("Queue limit reached"); 40 rapid triggers cost ≤ 16 ms UI each; Alt+1 fires on Live and not on Create; 5 rapid typed lines drain in order |
| 10. Stop latency | Stop current / Stop all stop the sink inside the click handler (< 1 ms measured; device buffer not measured); generation released in 0.19–0.20 s (VoxCPM2), 0.02 s (Kokoro); the next line plays normally |
| 11. External route fail-closed | Disarmed route refuses to speak; armed route speaks; a saved device that disappears is shown unavailable, the route disarms and nothing falls back to the speakers; after restart an armed Discord route is **DISARMED**. Physical unplug of a virtual cable **not run** (none installed) |
| 12. Monitor | Monitor on a second device plays alongside the primary with 0 underruns; monitor = primary is not duplicated. Physical monitor disconnect **not run** |
| 13–15. Discord / Zoom / OBS | **Not run — no virtual cable** |
| Mic Effects | 15 s with effects (gain, compressor) and 15 s pass-through: 0 dropped bytes, 0 discontinuities, 0 underruns, full 15 s reached the output, no memory growth; typed speech works afterwards; provenance says "not recorded" |
| Global hotkey | Real Ctrl+Alt+Shift+F11 keypress (Stop All) reached the app and silenced playback; unregistered afterwards |
| Model switching | Switching while Live speaks is refused ("Stop Live Voice before switching models"); 23 switches during the soak without error |
| Closing during audio | Window closes in ~1.0–1.4 s while speaking |
| 16. 30-minute soak | 170 utterances, 87 cached triggers, 28 stops, 23 model switches, board switching, monitor on/off: **0 errors**, TTFA median 0.16 s (Kokoro) / 0.20 s (VoxCPM2), max 0.34 s; app memory flat (2.92–2.94 GB); GPU memory returns to baseline after each switch. **64 underruns in two clusters** (59 around minute 11 during a Kokoro cycle, 5 around minute 21) — cause not isolated |

## Defects found and fixed during validation

- VoxCPM2 cloning (and so native Live streaming) failed on this machine: Smart App Control blocks Numba, which `librosa.load` imports. Fixed on main in #88.
- `models.json` saves dropped the `live_audio` capability (Live streaming silently off for Kokoro/VoxCPM2).
- Mic Effects frames were all dropped by the stale-frame guard added from code review.
- Diagnostics reported a running total of underruns across utterances instead of per utterance.
- Rebuilding a soundboard pad used whatever Kokoro/Qwen built-in voice was current; pads now remember it.
- From code review: close could hang before saving settings; Live wasn't counted as "model busy"; stale frames after Stop cleared the queue; API socket timeout, error keep-alive and temp folders; corrupt `boards.json` was overwritten; VoxCPM2 pad caches ignored the step setting.

## Open items

- Virtual cable, Discord, Zoom, OBS, and physical device-loss tests need a machine with a virtual audio cable.
- Soak underrun clusters: investigate (likely UI-thread stalls starving playback, since Kokoro generation is ~30× real time).
- Cached-pad audible latency vs the 100 ms target (start buffer is 150 ms on a drained sink).
- Buffered fallback with a non-streaming engine not exercised; headphone output not exercised.

Final disposition: **PASS for local outputs, Mic Effects and soundboard; virtual-microphone routes UNVERIFIED.**
