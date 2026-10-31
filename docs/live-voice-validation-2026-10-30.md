# Live Voice reliability baseline and fixes, 2026-10-30 (#13)

The real app ran off-screen in disposable profiles on `main` `d180f9a`, then on this branch (code head `019f5bc`).

| | |
| --- | --- |
| Windows | Windows 11 Pro 10.0.26300 |
| Stack | Python 3.11.9, PySide6 / Qt 6.9.0, PyTorch 2.8.0+cu128, RTX 5070 Ti |
| Outputs | VX2703 (HDMI, 44.1 kHz f32), the only one audible in the room; S34J55x (HDMI, 44.1 kHz); Realtek Digital Output (on-board, 48 kHz); HyperX QuadCast S speakers (headset, not used) |
| Recorder | HyperX QuadCast S microphone, 48 kHz, about 0.5 m from the VX2703 |
| Virtual audio driver | none installed |

## How things were measured

- **Acoustic numbers** are the trigger time (monotonic clock) compared with the onset in the mic recording. The mic timeline is anchored to read arrivals within ±3 s of each event, because the mic clock drifts against the system clock over minutes. Every figure includes the mic's own capture latency.
- **Floor:** to separate the app from the system, a raw `QAudioSink` (no Live code) plays the same signal; it gives the system floor.
- **Sink-side numbers** use each output's *played* position: bytes written minus what is still queued in the device (`bufferSize - bytesFree`).
- **`processedUSecs()` is not used.** On these devices it jumps to the full device-buffer length as soon as data is queued, so it cannot time playback. The earlier sink-side figures in #13 relied on it.

## Baseline on `d180f9a`

| Item | Result |
| --- | --- |
| First-line primary/monitor separation, Kokoro | Not reproduced. Played positions within 13–26 ms on every line, the first line after a model load included. Acoustically the VX2703 starts within about 40 ms whether it is primary or monitor (allowing for each line's TTFA). |
| First-line separation, VoxCPM2 native | Not reproduced. Within 13–31 ms on every line, first line included, 0 underruns. |
| Audio-pad trigger → heard | 38–50 ms, against a raw-sink floor of 22–48 ms. The app adds nothing measurable. |
| Stop all → silence | 72–82 ms, against a raw-sink `reset()` floor of 64–82 ms. The app adds nothing measurable. |
| Cached TTS pad trigger → heard | Median 205 ms, of which 165 ms is silence at the start of the cache file (see Fix 2). |
| 30-minute mixed soak (silent outputs) | 0 errors, **55 underruns**: 45 on VoxCPM2, 10 on Kokoro. Load: 232 lines, 103 cached pads, 61 audio pads, 63 stops, 6 model switches, 9 monitor toggles. |

### Soak underruns, by cause

- **VoxCPM2 (45):** every one occurred while the line was being generated slower than real time. Measured RTF was 1.15–1.39 on the first lines after a voice or model load, and 0.83–0.96 with **0 underruns** once warm. This is the documented re-buffer: one short pause rather than clicks. Six reloads in the soak repeat the warm-up each time.
- **Kokoro (10):** Kokoro renders about 30× faster than real time, so these should not happen. In isolation, 24 lines and 9 queued lines gave **0**. A 10-minute Kokoro-only mixed soak with full context gave 6, and in **6 of 6** none of the new line's audio had been written yet. That is Fix 1.

## Fixes (branch `fix/live-reliability-13`)

**Fix 1: a hand-over between items is not an underrun** (`b5faa61`, `ui/live_audio.py`)

- **Cause:** a line submitted as the previous item finished was configured onto the still-playing sink. If that item's tail drained before the new line's first audio arrived, the idle was counted as an underrun. The new line then waited for **twice** its start buffer: 0.30 s for Kokoro, **0.70 s instead of 0.35 s for VoxCPM2**.
- **Fix:** an idle before any of the current item's audio has been written now waits for the normal start buffer and is not counted. A real mid-item underrun still counts and re-buffers.
- **Tests:** two regressions; the first fails before the fix.

**Fix 2: cached pads start on the first sound** (`019f5bc`, `core/live_voice.py`)

- **Cause:** a cache holds the engine's whole render. Kokoro's starts with about 87 ms of true silence, then a quiet breath-like onset that is part of the word, at about -60 to -40 dBFS.
- **Fix:** playback starts 20 ms before the first sample above 0.5% of the clip's peak. Cache files and imported audio clips are unchanged.
- **Tests:** two regressions; they fail before the fix.

## After the fixes (same devices)

| Item | Before | After |
| --- | --- | --- |
| Cached pad trigger → loud part of the first word | median 205 ms (180–210) | **median 130 ms (115–145)** |
| Cached pad trigger → first audible sound | about 125 ms | **about 50 ms** |
| Kokoro underruns, 30-minute mixed soak | 10 | **0** |
| Hand-over underruns (0 bytes of the new line written) | 6 of 6 Kokoro underruns in the 10-minute soak | **0** |
| VoxCPM2 underruns, 30-minute mixed soak | 45 | 50, all genuine slower-than-real-time re-buffers |
| Errors in the soak | 0 | 0 |

The second 30-minute soak ran the same action mix: 230 lines, 100 cached pads, 59 audio pads, 62 stops, 6 model switches and 9 monitor toggles.

The #107 and #108 behaviours (monitor follows the primary through a re-buffer; format switch while audible) are unchanged, and their regression tests pass. Unit suite: 514 tests OK (`main`: 510).

## Not verified

- **Physical device loss and recovery.** No unpluggable audio device is attached: the Realtek output is the on-board codec. Switching the S34J55x monitor off with its power button did not remove its audio endpoint. Display sleep does remove both HDMI endpoints (seen once, while Live was idle), so that is the way to exercise this on this PC.
- **Virtual cable, Discord, Zoom and OBS routes.** No virtual audio driver is installed.
- **Owner listening review** of Live and Mic Effects.
- **VoxCPM2 warm-up.** The first few lines after loading a voice render slower than real time on this GPU. A silent warm-up render at load time would remove those pauses; that is a behaviour change left for review.
