# Listening review package

Every voice and sound in “A World in Sound: Evening Tide, The Beacon”, exactly as the app produced it (the Guide lines and the tagline were made before filming; everything else was made on camera). **Review candidates, not approved.**

Please listen for: does each character sound like the same person each time; are the emotions right (calm narrator, weathered keeper, hopeful traveler); any clicks, breaths or artefacts; does the sea sit under the voices; does the tagline land.

| File | Voice | Length | LUFS | Peak dBFS | Similarity to designed voices (1.0 = identical) | Whisper |
| --- | --- | --- | --- | --- | --- | --- |
| [`01-guide-a-world-can-begin.wav`](01-guide-a-world-can-begin.wav) | Guide | 2.49 s | -21.8 | -7.7 | guide 0.924, keeper 0.583, traveler 0.68 | all words heard |
| [`02-keeper-the-beacon.wav`](02-keeper-the-beacon.wav) | Keeper | 3.17 s | -21.1 | -2.1 | guide 0.608, keeper 0.962, traveler 0.549 | all words heard |
| [`03-guide-someone-answers.wav`](03-guide-someone-answers.wav) | Guide | 2.32 s | -21.1 | -6.7 | guide 0.876, keeper 0.524, traveler 0.639 | all words heard |
| [`04-traveler-i-see-it-now.wav`](04-traveler-i-see-it-now.wav) | Traveler | 2.19 s | -21.7 | -7.4 | guide 0.681, keeper 0.528, traveler 0.936 | all words heard |
| [`05-guide-a-shoreline.wav`](05-guide-a-shoreline.wav) | Guide | 1.93 s | -21.0 | -6.2 | guide 0.889, keeper 0.559, traveler 0.638 | all words heard |
| [`06-shoreline-waves.wav`](06-shoreline-waves.wav) | Ocean (procedural, Sounds) | 20.0 s | -24.0 | -7.8 |  |  |
| [`07-guide-a-character-can-return.wav`](07-guide-a-character-can-return.wav) | Guide | 2.72 s | -20.8 | -8.1 | guide 0.873, keeper 0.578, traveler 0.652 | all words heard |
| [`08-keeper-clone-ill-keep-it-burning.wav`](08-keeper-clone-ill-keep-it-burning.wav) | Keeper (cloned, VoxCPM2) | 2.04 s | -21.6 | -3.8 | guide 0.566, keeper 0.773, traveler 0.456 | all words heard |
| [`09-guide-place-every-line.wav`](09-guide-place-every-line.wav) | Guide | 3.86 s | -21.4 | -7.0 | guide 0.898, keeper 0.545, traveler 0.747 | all words heard |
| [`10-guide-together.wav`](10-guide-together.wav) | Guide | 4.96 s | -21.5 | -5.1 | guide 0.925, keeper 0.576, traveler 0.743 | all words heard |
| [`11-studio-preview-mix.wav`](11-studio-preview-mix.wav) | Studio Play mix | 14.5 s | -19.6 | -2.2 |  |  |
| [`12-brand-narrator-tagline.wav`](12-brand-narrator-tagline.wav) | Brand narrator | 3.44 s | -21.2 | -5.5 | guide 0.566, keeper 0.662, traveler 0.577 | all words heard |
| [`13-exported-master.wav`](13-exported-master.wav) | Studio Export master | 14.5 s | -16.1 | -1.1 |  |  |

- `06-shoreline-waves.wav` is the full 20-second take from Sounds (a seamless loop, so it ends at full level by design); in the Studio it is trimmed to 14.5 s with a 1.5 s fade-in and 3 s fade-out.
- `11-studio-preview-mix.wav` is the Studio's Play mix (not mastered); `13-exported-master.wav` is the real Export mix master (-16 LUFS target, peak limited).
- [`voice-designs/`](voice-designs) holds the three owner-picked Qwen3-TTS VoiceDesign clips the Guide, Keeper and Traveler voices were saved from.
- Similarity is the cosine between Chatterbox voice-encoder embeddings; it is a sanity check, not a substitute for listening. The VoxCPM2 clone is a different engine, so it is less close to the design (0.77) than the Qwen3 lines, but still clearly the Keeper.
