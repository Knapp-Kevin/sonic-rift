# How Accent Development Actually Works: Speech Science, Architectures, and Engineering Choices

**Research snapshot:** 2026-10-10. **Status:** source-backed research, not implemented, trained, acoustically benchmarked, or independently peer reviewed here.  
**Work:** [#50](https://github.com/Knapp-Kevin/this-voice-thing/issues/50); parent [#40](https://github.com/Knapp-Kevin/this-voice-thing/issues/40); decision gate [#44](https://github.com/Knapp-Kevin/this-voice-thing/issues/44).

## Executive decision

The earlier research plan focused mostly on **voice-design prompt effectiveness**. That is useful but insufficient for the desired product: independent choices for *same voice*, *specific accent*, and *degree of accent*. Accent development is a combination of **linguistic specification, model conditioning, optional adaptation/training, and independent perceptual verification**. We need research on accent-specific architectures **before** finalizing the Accent Design Studio contract.

**Research recommendation (not integration authorization):** retain Qwen3 and VoxCPM2 as no-new-model baseline; add a separate **experimental DEFINE/F5-TTS feasibility track** because a documented released implementation already accepts *speaker reference* and *accent reference* independently and exposes an actual accent-guidance weight. However F5 base weights are **noncommercial** and DEFINE licensing is unresolved, so no production/business eligibility is established.

## 1. An accent is not one slider

Accent is a **pattern of realizations of linguistic units**, not a singular acoustic effect. Useful observables include:
- **Phoneme inventory and lexical sets:** variants of vowels/diphthongs, consonants, mergers/splits and distribution of phoneme categories.
- **Realization rules:** rhoticity for syllable-final /r/, variants of /t/, vowel length conditioned on following sounds, consonant lenition, connected-speech reductions, sound-to-sound coarticulation.
- **Suprasegmentals:** stress placement, timing/rhythm, phrase-level intonation and prosodic contours.
- **Variation:** lexical item, speaking style/register, age, class and individual histories affect realization; named geographical label is not a perfectly homogeneous target.
- **Separate quantities:** speaker identity/timbre, vocal pitch, emotional style, articulation clarity, speaking rate, language and accent. Treat these as related but independent intended controls. Do not simulate a regional accent merely by changing pitch, speed or spelling text phonetically.

The claim 'Glasgow' needs expert-selected diagnostic utterances and relevant human raters. Scottish Standard English rhoticity is **variable and socially/register conditioned** rather than a one-feature geographic stamp. Source: [Schützler, World Englishes 2024/2025](https://doi.org/10.1111/weng.12689); [Stuart-Smith et al., 2014](https://doi.org/10.1075/silv.15.03stu).

**Task partition examples:**
1. English with a Scottish-English regional accent (language English, target Scottish English).
2. English with French L1 influence (language English, target French-accented English).
3. Metropolitan French spoken as French (language French, different accent task).
4. Quebec French spoken as French (language French, different accent task).
No language dropdown should silently change a requested accent or vice versa.

## 2. Seven accent-development mechanisms

| Mechanism | What you actually change | Training needed by user? | Pros | Failure mode / limit |
| --- | --- | --- | --- | --- |
| **A. Instruction prompting** | Text instruction to an already trained TTS | None | Cheapest; available in Qwen3 VoiceDesign/VoxCPM2 | Learned associations opaque, 'strong Glasgow' may produce generic British or theatrical vowels |
| **B. Speaker-reference cloning** | Speaker embedding/audio + optionally paired transcript | None for inference | Strong voice continuity and some natural accent transfer | Speaker, accent, prosody, noise and emotion are entangled; changing reference changes multiple traits |
| **C. Independent accent exemplar conditioning** | Speaker sample **plus separate** regional-accent sample or prototype | Inference may require only pretrained model; *model author* trained accent encoder/adapters | Allows same speaker with multiple target accents; accent guidance may be real parameter | Needs trained disentangling model and appropriately sourced samples; may distort voice or phonemes |
| **D. Phonological / pronunciation rules** | Controlled phoneme sequence, text-to-phoneme dictionary, local rewrite rules | Not intrinsically | Target explicit sound changes; phoneme-shift measure possible | Current Qwen/Vox model adapters don't promise an arbitrary IPA/phoneme API. Rule constraints can conflict with latent speaker and accent |
| **E. Single-speaker supervised fine-tuning** | Adjust speech model weights/checkpoint to particular speaker + recordings | Yes | Improves that speaker's voice/accent match | May memorize speaker and pronunciation jointly; not a generalized accent selector or robust strength knob |
| **F. Multi-accent disentanglement training** | Multi-speaker/region data; separate accent and speaker embeddings / classifiers / adapters / contrastive or adversarial losses | Yes, substantial curated data | True portable accent control possible, accent embeddings can vary independent of speaker | Needs speaker-disjoint and language-controlled training, matched accent coverage, difficult tuning |
| **G. Post-TTS accent/voice conversion** | Convert audio from an existing TTS voice to target acoustic style | May use pretrained VC weights; training varies | Independent retrofit path, useful reference baseline | Two-stage latency, artifacting, timbre degradation and rights/license complexity; may not repair wrong phonology |

**Relevant primary evidence:**
- [DART (2024)](https://arxiv.org/abs/2410.13342): accent–speaker disentanglement via multi-level VAE/vector quantization to vary accent while preserving speaker identity.
- [Zhou et al., multi-scale accent modeling (published Feb 2026)](https://doi.org/10.1109/TASLPRO.2026.3657306): utterance-level + phoneme-level accent representations, speaker embedding separation and local accent prediction.
- [Lertpetchpun et al., ICASSP 2026](https://sail.usc.edu/publications/html/b2hd-11462045.html): phonological rules for flapping, rhoticity and vowel correspondences interacted with speaker embeddings; proposes a **phoneme shift rate** measurement and found embeddings can weaken/override the rules.
- [DEFINE, Sep 2026](https://arxiv.org/abs/2609.32777) and [open-source implementation](https://github.com/AMAAI-Lab/define): separately conditions on speaker and accent exemplar, with an inference-time weight.

## 3. How you actually *train* an accent-capable system

### Training pipeline

1. **Scope the linguistic phenomenon.** Define varieties, phonetic/dialect evidence, and minimum valid comparisons. Label the recorded output *language*, *region*, *speaker*, *register*, *recording conditions*, and *phonetic coverage* individually.
2. **Acquire data with actual rights.** Distinguish reusable recordings for ASR, TTS training, exemplar transfer, audio publication, and likeness cloning. Legal reuse of audio does **not automatically grant** consent to clone an identifiable speaker.
3. **Clean + transcribe + align.** Remove clipped/noisy and duplicate speech, check transcript correctness, annotate words/phones where applicable, speaker IDs, device and delivery style. Keep provenance and hashes. Avoid treating broad self-reported accent tags as precise phonetic labels.
4. **Build speaker-disjoint test data.** Hold out speakers, utterances, accent groups and/or unseen exemplar accents as appropriate. A model recognizing the person, recording room or microphone rather than an accent is a failure.
5. **Choose training objective.**
   - *Speaker adaptation*: supervised TTS fine-tuning on one speaker.
   - *Accent adapter*: parameter-efficient LoRA, learned accent embedding, accent encoder and loss terms that preserve speaker identity and linguistic content while changing accent traits.
   - *Disentangled multi-speaker model*: several speakers per accent and accents per speaker if available, plus explicit factor-separation losses/conditioning and evaluation.
   - *Rule-guided acoustic front end*: context-specific phoneme realization supervised/tested separately from identity.
6. **Train and evaluate without test leakage.** Track revision, optimizer/config, training loss and resource costs, but judge with **unseen text/voices/accent examples** rather than training clips.
7. **Assess voices independently.** Intelligibility/word error, naturalness, accent recognition with 'uncertain', phonetic feature checks, speaker identity retention and drift. Increasing accent score while destroying intelligibility is not a win.
8. **Package for deployment only if cleared.** Code, weights, training data, reference voices and output rights are distinct; validate hashes, model provenance and GPU budget before allowing downloads.

**Official accessible path:** [Qwen3 TTS single-speaker fine-tuning README](https://github.com/QwenLM/Qwen3-TTS/blob/main/finetuning/README.md) trains its **Base** (0.6B/1.7B) using `audio`, `text`, `ref_audio` JSONL and audio token preprocessing. This is **not** an official general multi-accent adapter or calibrated accent knob; no promised fit for RTX 5070 Ti 16 GB without actual profiling. Third-party forks claiming dialect-aware fine-tuning are independent, experimental codebases and require separate provenance/reproducibility audit.

A lone 10-second clip can provide *inference conditioning* but is not sufficient evidence that a generalized accent model can be trained from it. Published multi-accent methods rely on pretraining/curated multi-speaker audio even when inference needs only a few exemplar clips.

## 4. Why numeric 'accent strength' needs its own model contract

- A **prompt intensity** ('subtle/moderate/strong') is just instruction text: there is no calibrated signal in Qwen3/VoxCPM2 adapters that specifically adjusts accent phonetics.
- **DEFINE's `--w` is a genuine inference-time guidance weight** injected into its accent conditioning. The code documents `--w 0` as off and larger values as stronger, but `w=9` is not '90% Scottish.' It's model-specific, nonlinear and needs empirical calibration.
- **Acoustic evidence**: seek monotonic changes in context-relevant vowel/consonant/prosody probes where intended, with intelligibility and voice retention both within acceptable tolerances, then blinded perception.
- Do not expose fake 'thickness in percent' sliders for engines that only understand descriptions.
- Save `requested_strength` and `applied_engine_weight` separately; annotate measured effect and confidence if later verified.

The [DEFINE paper](https://arxiv.org/abs/2609.32777) reports that, on its test set, accent probe accuracy increased from roughly **6.5%** with accent off to **19.6%** using exemplars. This shows a measurable model effect, not reliable named-region authenticity for every voice. Its results also report tradeoffs against speaker similarity and intelligibility. Study not locally replicated.

## 5. Three different product experiences

**Voice design from words:** Pick a description and accent intention. Engine may produce an approximation. Supported by current Qwen/VoxCPM workflows; no need to download another model.

**Accent transfer from examples:** Select/record consenting *speaker voice* and separately choose a permitted *accent reference* (one or several clips); preview various strengths. Requires an actual disentangled model (DEFINE candidate), separate CPU/GPU/memory feasibility and licensing clearance. Do not claim any existing engine directly supports this contract.

**Accent lab / advanced:** Let a qualified operator compare phonetic contrasts on anonymized audio, inspect pronunciation dictionary/phoneme rules where supported, benchmark identity and accent drift, optionally fine-tune an adapter on proper dataset. This is separate from beginner-friendly Studio controls. No training or phoneme rewriting required for MVP unless justified by evidence.

The right UI may ultimately expose **mode/capability** rather than pretending the same slider works across all engines. An unavailable/experiment-only model choice must be labeled clearly.

## 6. Revised research order and hold points

1. **Current-engine baseline:** Existing [#43 protocol](accent-design-benchmark-protocol.md) can validate prompt outcomes on Qwen/VoxCPM2. Don't discard it, but it doesn't fully test controllable accents.
2. **DEFINE source/licensing feasibility:** [#51](https://github.com/Knapp-Kevin/this-voice-thing/issues/51) traces checkpoint, licensed weights and Windows feasibility *without installing first*. Experimental use requires explicit authorization; base F5 weights are noncommercial.
3. **Phonetic inventory and data rights:** [#52](https://github.com/Knapp-Kevin/this-voice-thing/issues/52) decides what Scotland and French-English examples mean, which data can be accessed, and who can validate.
4. **Controlled 3-way comparison:** prompt design vs reference clone vs separate-accent-exemplar (if feasible and authorized) on *the same target* with separately reported speaker similarity, accent fidelity, intelligibility, latency/VRAM and dataset/permission coverage.
5. **Decision #44:** GO / LIMITED GO / NO-GO only after technical, data/rights and human evidence. This is a **research expansion**, not authorization to expand implementation issues #45–#48.

## Open, important questions

- Can the same speaker preserve identity across changes of *phonology* and accent *prosody*, not just timbre?
- Can an ordinary end-user create a named regional accent without a speaker/dialect coach's curated samples?
- Are 'Scottish' and 'French' classifiers detecting true phonetic patterns or correlated speaker/recording properties?
- Can a noncommercial exploratory accent model guide an independently licensed and trained commercially permissible system? A clean implementation would still require independent permitted weights/data and is not a quick license workaround.
- What is the minimum effective corpus of *distinct speakers per accent* for adapter training rather than single-speaker cloning? No trustworthy universal minutes-to-quality figure should be invented.

**No audio runs, fine-tuning, phonetic review, or resource profiling were performed in this research-only update.**
