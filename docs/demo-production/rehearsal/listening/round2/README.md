# Music round 2: owner review

Owner notes on round 1: A was too fast (the model chose 115 BPM), B sounded minor and sad, and C sounded a bit synthetic.
The request for round 2 was A's warmth, slower, with **a stringed instrument instead of piano or woodwind**.

| Take | Lead instrument (prompt) | Alone | In the scene (Studio Export mix) |
|---|---|---|---|
| D | Solo cello + soft string ensemble | `music_candidate_D_seed3101.wav` | `scene_with_D.wav` |
| E | Fingerpicked nylon-string acoustic guitar | `music_candidate_E_seed3102.wav` | `scene_with_E.wav` |
| F | Concert harp + soft sustained strings | `music_candidate_F_seed3103.wav` | `scene_with_F.wav` |

All three: **Tempo 70 BPM, A major, 4 beats per bar** set on the Music page. The model's planner confirmed 70 / A major / 4 for each take.
Each is 30 s, 48 kHz stereo, 24-bit PCM, about −16 LUFS integrated, −1.1 dBFS true peak, 0 clipped samples.
Dynamic range: D 15.6 LU (swells the most), E 5.8 LU (steadiest), F 9.0 LU.
The prompt shared by all three followed the lead instrument: *"slow, gentle, warm original instrumental underscore for a quiet seaside night, hopeful and tender, unhurried and
sparse, purely acoustic, no piano, no woodwinds, no synthesizer, no electronic sounds, no percussion, no vocals"*. Instrumental on, Plan first on.

Scene files: the approved Keeper (02), Traveler (04) and Keeper-clone (08) lines and procedural Ocean waves (−6 dB), with one music
track (−14 dB, 2 s fade-in, 4 s fade-out). The other two music tracks were muted with Selection › Mute / unmute track. Automatic ducking was on.
Every music clip went in with **Keep and add to Studio** while the waves track was selected, and each got its own track (the fix).

## SHA-256
| File | SHA-256 |
|---|---|
| music_candidate_D_seed3101.wav | `e6ce1041192d427c26c2e53c0f60e45aacac9c9243188378e3564caf6a0b9b88` |
| music_candidate_E_seed3102.wav | `b2f9b08193b684f0ee57f9f97432217f496d0988e73bc5a356618e4c55832dc5` |
| music_candidate_F_seed3103.wav | `aa3e04fc532d98a1805b102687971d7568094cb398e12e192163448265d6b098` |
| scene_with_D.wav | `908b239bd26c582b85d39aee50b8b0f5c2f33b1b548c0fd6fb5f0fe97c580d6a` |
| scene_with_E.wav | `7349f2a283a1a959d3156b0ad31f23c175b587f098bd9b1903e7ae2d5b1325ee` |
| scene_with_F.wav | `45db16c1faa1e34aa53a26c490a8b2057001c5b1533a1b31afd1c4eb9963d631` |

## Provenance
Sonic Rift development build `bc84a4a` (post-0.9.0-alpha; the recording baseline), run from source in a disposable profile, 2026-11-03.
ACE-Step 1.5 (2B turbo), weights `19671f406d603126926c1b7e2adc169acbcade22`, source `ca1e85fe9430179831e6bc6be790c332190a3866`,
MIT License. Seeds 3101–3103 (one take per prompt). Takes are not reproducible from the seed, so the picked file is the cue.
Log: `round2_log.txt`. Harness: `round2_music.py` (uses `../../fix-verification/bc84a4a-rehearse_scene.py`).
No vocals check was automated; that is for the owner's ears.

## Owner pick (2026-11-03)
**Take D (solo cello + soft strings)** chosen by the owner for the film, with the note that the audio must be balanced.
Balance measured on the Studio export `scene_with_D.wav` (post-duck stems): dialogue −18.7 LUFS while the lines play; waves
−33.0; music D −35.5 (about 17 dB under the voices). After the lines, the music rises to −29.8 and the waves to −31.1. Planned for the
final cut: trim D to the scene length and keep the 4 s fade-out. If D feels too present after the last line, lower the music track to
about −16 dB. All of this happens in Studio. The creative treatment and script v0.3 still need approval before recording.
