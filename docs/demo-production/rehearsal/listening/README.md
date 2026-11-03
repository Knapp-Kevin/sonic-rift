# Music listening candidates: owner review

**Status: for owner listening only. Not approved, not for publication.** Pick one cue, or ask for another round, before
any final recording. The picked file is the cue: ACE-Step does not reproduce a take from its seed (two runs with
seed 1103 gave different audio), so a regeneration would be different music.

## Files
| File | What it is | Length / format | Integrated | LRA | True peak | SHA-256 |
|---|---|---|---|---|---|---|
| `music_candidate_A_seed2026.wav` | Take A, as generated | 30.0 s, 48 kHz stereo, 24-bit PCM | −16.1 LUFS | 5.1 LU | −1.1 dBFS | `13e7124db62bee83e56e11a031a8b57b15a241c5773ad93caed445871ddec732` |
| `music_candidate_B_seed2027.wav` | Take B, as generated | 30.0 s, 48 kHz stereo, 24-bit PCM | −16.1 LUFS | 13.0 LU | −1.1 dBFS | `2c540f66d81f46e04c214195a0f64a0d9687df42f73aad5d8d9fa821f8291b83` |
| `music_candidate_C_seed2028.wav` | Take C, as generated | 30.0 s, 48 kHz stereo, 24-bit PCM | −16.0 LUFS | 10.8 LU | −1.1 dBFS | `fff96a492f2601b9190b22d2a223e887b3bb97adb76683f698bdbb0a4d294c09` |
| `scene-rehearsal-master.wav` | Studio **Export mix** of candidate A under the approved Keeper (02), Traveler (04) and Keeper-clone (08) lines and procedural Ocean waves. Music track −14 dB with 2 s/4 s fades, waves −6 dB, automatic ducking on | 30.0 s, 48 kHz stereo, 24-bit PCM | −16.1 LUFS | 9.8 LU | −1.1 dBFS | `8715426de4db6e56a3c8d3767ca984875329b2e4b21894bba181b62c5f04d80e` |

All four come straight from the app, with no editing outside Sonic Rift. B and C have the widest dynamics (higher LRA), so check that they stay
under the dialogue. A is the steadiest.

## Provenance
- **App:** Sonic Rift v0.9.0-alpha, commit `f093ebd`, run from source in a disposable profile on 2026-11-03 (Windows 11 Pro
  10.0.26300, RTX 5070 Ti). The music path (Music page → takes → Keep) is the same in the fix build `bc84a4a`. That build only
  changes which Studio track a kept sound joins.
- **Engine:** ACE-Step 1.5 (2B turbo), `ACE-Step/Ace-Step1.5` weights revision `19671f406d603126926c1b7e2adc169acbcade22`,
  source `ace-step/ACE-Step-1.5@ca1e85fe9430179831e6bc6be790c332190a3866`. **MIT License** (code and weights), as shown by the app.
  The app's notice: the authors say the training data is licensed, royalty-free or synthetic. That is their claim, not a guarantee
  that an output resembles no existing song.
- **Request (all three):** prompt *"Understated original instrumental underscore for a quiet seaside night: soft felt piano, warm
  low strings, slow and calm, gentle, sparse, no percussion, no vocals"*. Instrumental on, Plan first on, 30 s, 3 takes, seed 2026
  (the app gives takes consecutive seeds: A 2026, B 2027, C 2028). Tempo, key and meter were left to the model. Output target −16 LUFS. CUDA.
- **What the planner chose:** recorded for the kept take A only: **115 BPM, A major, 4/4**. That is quicker than "slow and calm"
  suggests, so listen for it. B and C were not kept, so their planner choices were not recorded.
- **Kept-asset record for A** (from the app's Sound library): id `722bc8910f68`, name "Harbor light underscore", sha256 as above,
  metrics −16.11 LUFS, −1.1 dB true peak, 0 clipped samples.
- **Logs:** `../logs/scene_log.txt`, `../logs/scene_result.json`, and the harness `../logs/rehearse_scene.py`.

## Checks for the owner
1. **Any sung or spoken sounds?** Not machine-checked: there is no transcriber in this build's environment.
2. Mood and tempo fit under "Place every line where it belongs…" and the S07 scene.
3. Does it sit under the dialogue in `scene-rehearsal-master.wav`? (Measured: about 13 dB below the dialogue stem.)
4. Choose A, B or C, or ask for another round (e.g. Tempo on at 70 BPM).
