# Accent Exemplars, DEFINE/F5 Feasibility, and Regional Speech Data

> **Research snapshot:** Findings and model-license claims reflect the original October 10, 2026 assessment. Links were reconciled to the Sonic Rift repository on October 15. No inference, accent authenticity, updated dependency licensing, or hardware performance is newly certified by merging this document. The owner GO/NO-GO gate remains #44.

**Research snapshot:** 2026-10-10. **Status:** public-source technical reconnaissance; **no checkpoints installed, clips downloaded, training or speech synthesis performed**.  
**Issues:** [#51 DEFINE](https://github.com/Knapp-Kevin/sonic-rift/issues/51), [#52 accent corpus](https://github.com/Knapp-Kevin/sonic-rift/issues/52), [#43 benchmarking](https://github.com/Knapp-Kevin/sonic-rift/issues/43).  
**Decision:** [#44](https://github.com/Knapp-Kevin/sonic-rift/issues/44) remains a required owner approval gate.

## 1. DEFINE is a materially different technical option

[DEFINE paper (submitted Sep 26, 2026)](https://arxiv.org/abs/2609.32777) | [authors' code](https://github.com/AMAAI-Lab/define) | [README](https://github.com/AMAAI-Lab/define/blob/main/README.md).

The repo implements an accent-conditioned F5-TTS system with **two input roles**:
- `--ref-wav` + `--ref-text`: short reference for **speaker identity and textual speech conditioning**.
- Exactly one of `--accent <label>` (lookup mode) or `--exemplars <file(s)>` (accent-exemplar mode): **target accent** independent of target speaker.
- `--w <float>`: accent guidance weight. README states `w=0` switches off accent conditioning, higher `w` increases its effect, not percentage/guaranteed accuracy.
- `--text`: new utterance to generate; `--seed`, `--nfe`, `--cfg`, `--speed` for inference reproducibility/configuration.

**Verified in code:** [infer.py](https://github.com/AMAAI-Lab/define/blob/main/infer.py) mutually excludes accent label vs exemplars; [accentbridge/synth.py](https://github.com/AMAAI-Lab/define/blob/main/accentbridge/synth.py) pools multiple accent-exemplar crops (`k=2`, `win_s=4.0`) into one accent embedding and injects `accent_weight=w` during flow-matching synthesis; output sample rate 24kHz. This is not an arbitrary style tag.

Published README lists named categories: `canada`, `england`, `hong_kong`, `india`, `malaysia`, `new_zealand`, `scotland`, `singapore`, `southern_africa`, `us`, `spanish`, `turkish`, `chinese`, `nigerian`, `dutch`, `russian`, `polish`, `arabic`, `french`, `german`, `japanese`, `swedish`, `italian`. **Interpretation:** broad Scotland and French-influenced English are named model classes. The author README does **not** establish independent Glasgow vs Edinburgh controls, nor Quebec vs metropolitan French-accent English, nor French-language voice variety output.

**Dependencies/reproducibility from source:**
- [requirements](https://github.com/AMAAI-Lab/define/blob/main/requirements.txt): `f5-tts==1.1.22`, PEFT, transformers, torchdiffeq, torch/torchaudio, soxr, librosa, SpeechBrain, faster-whisper, jiwer etc.
- [config](https://github.com/AMAAI-Lab/define/blob/main/config.yaml): `F5TTS_v1_Base/model_1250000.safetensors`, `vocos-mel-24khz`, `wav2vec2-xls-r-300m`, `accentbridge.pt`; model might fetch any missing weights automatically into `hf_cache`.
- [README](https://github.com/AMAAI-Lab/define/blob/main/README.md): `accentbridge.pt` distributed from **Google Drive zip**, not verified immutably/version pinned here; inspect source release/weight checksums and ensure no untrusted checkpoint is blindly loaded.
- [train.py](https://github.com/AMAAI-Lab/define/blob/main/train.py): staged lookup/prototype training; upstream examples use 20k lookup + 30k prototype steps using accent table, LoRA, accent exemplar encoder, self-supervised XLS-R. Training pipeline can incorporate Common Voice, optional in-house sample bank and optional Seed-VC augmentation. This is **not** feasible simply by recording ten seconds of one speaker; authors already did substantial preparation and training.
- [evaluate.py](https://github.com/AMAAI-Lab/define/blob/main/evaluate.py) uses accent-probe score, speaker similarity, WER, UTMOS and guidance conditions; defaults to weights `0,9,15`. These are research-scale numerical weights, not human-meaningful 0%-100%.

**Results interpretation:** Paper reports **accent-probe accuracy 6.5% to 19.6%** on seen accents when using exemplar guidance (model conditions and other metrics matter). This shows learned transfer but is **not** '19.6% Scottish' and is not adequate alone for Scottish/French regional correctness. It reports tradeoffs involving speaker similarity and intelligibility, and different transfer behavior on seen, held-out and out-of-domain accents. Independent human evaluation on intended varieties is still required.

## 2. Licensing is a hard blocker for any commercial path

| Component | Public finding | Consequence |
| --- | --- | --- |
| F5-TTS implementation | **MIT source code** [official repo](https://github.com/SWivid/F5-TTS#license) | Its code can be inspected/used consistent with MIT |
| F5-TTS pretrained base weights | **CC BY-NC** according to its maintainers; trained on Emilia | No assumption of commercial product/model-output eligibility |
| DEFINE project's own repository | Root directory checked Oct 10 contains **no standalone LICENSE file**; verify with upstream authors and individual source headers | Cannot assume an open-source commercial license because repo is public |
| DEFINE accent adapter checkpoint | External Google Drive distribution; license and exact immutable provenance not confirmed in README | **Unknown rights and checksum**: block integration, packaging, commercial claims |
| Dataset/audio exemplars | May each have distinct copyright, publicity/voice-cloning and access terms | Human speech recordings cannot be bundled from random social/media sources |
| Resulting AI-generated audio | Use rights depend on model and dataset terms, plus voice sample consent where applicable | Legal assessment before deployment/distribution |

**Research can proceed by reading source.** Even a noncommercial prototype or model download must be separately authorized, comply with those license terms, and avoid hidden cache auto-downloads. A commercial offering cannot merely replace its code while redistributing the same noncommercial checkpoint. Seek an explicitly commercially cleared model/weights path if long-term enterprise viability matters.

**Security:** Inspect checkpoint serialization and transitive dependencies before loading external archives; [train.py](https://github.com/AMAAI-Lab/define/blob/main/train.py) uses a `torch.load(..., weights_only=False)` route for an initialization checkpoint, which may execute untrusted pickle data. Do not treat unknown-source files as safe. Avoid privileged execution and verify hashes.

## 3. Proposed verification of DEFINE, only if authorized

**Phase A: feasibility without downloads**
- Inspect all package/weight licenses and checkpoint publication; request upstream license clarification for missing parts.
- Inspect command-line contract and source revision; record concrete dependency and expected CUDA versions.
- Confirm checkpoint hashes and whether all weights may be retrieved without hidden side effects. Validate local available disk and VRAM budget before any attempt.
- Determine whether the existing RTX 5070 Ti 16 GB can load base F5 + vocoder + XLS-R + accent encoder concurrently, based on **measured evidence**, not only parameter counts. Isolated environment, no modification to this-voice-thing's main interpreter.

**Phase B: isolated experimental only, with owner consent**
- Reference voice: consenting or owned speaker sample; distinct accent exemplars: permissioned Scottish/French-English examples, separate from speaker.
- Create paired samples using same text/speaker exemplar/accent exemplar at `w=0,9,15`; include unrelated accent/control and several seeds.
- Measure actual memory, cold/warm latency, failure rate and time per utterance.
- Blind-test accent family recognition, intelligibility and voice similarity. For named regions, require qualified raters; broad `scotland` is **not** automatically Glasgow/Edinburgh.
- Compare Qwen/Vox instructions and simple accent-copy reference cloning with DEFINE's two-input path as separate conditions.
- Do not change GitHub `models.json`, advertise commercial support, distribute weights, or enable external routing.

**Decision outcomes:** (1) research-only due to license; (2) feasible restricted sidecar; (3) resource/provenance/quality NO-GO; (4) a distinct fully licensed accent model would be required for commercialization.

## 4. Candidate corpora: not all voice recordings are freely reusable for cloning

| Candidate | Source and reported contents | Published terms | Accent/data caveats | Next evidence |
| --- | --- | --- | --- | --- |
| **VCTK v0.92** | [Edinburgh DataShare](https://datashare.ed.ac.uk/items/30e7453c-9ea8-48b4-8e18-f96d0dc62928/full), **110 English speakers** with various accents, ~400 read utterances per speaker | **CC BY 4.0** on original dataset landing page | Need **per-speaker region labels and sample review**; don't infer Glasgow/Edinburgh from institution name; clone likeness permissions require separate consideration | Confirm accent metadata coverage, speaker split, usage/consent and sample-level provenance, 10.94 GB download cost |
| **EdAcc** | [Edinburgh International Accents of English Corpus](https://datashare.ed.ac.uk/items/355c07b4-500d-4e80-8f12-225e646293c9/full), ~40h conversational audio, speaker language/accent annotations | **CC BY-SA 4.0** | ASR evaluation corpus; varied international accents, not guaranteed regional Scottish and French-English matched examples; recordings from conversations raise privacy/derivative questions | Check speaker-level labels, modality/access/derivative obligations, speech suitability, ~5.51GB |
| **Mozilla Common Voice** | [Mozilla Data Collective](https://commonvoice.mozilla.org/dav/terms), multilingual submitted read speech, self-reported accent tags where available | Usually **CC0**, but **access conditions and dataset-specific restrictions differ**. Redistribution through MDC requested, not casual mirroring | Some MDC derivative packages explicitly restrict creating/publishing voice-cloning systems; verifying the exact distribution's terms is mandatory. Labels often self-reported, weak at specific regional granularity | Confirm selected release, conditions, accent label sample sizes, speaker sampling/splits and whether reference cloning is allowed |
| **L2-ARCTIC** | [TAMU PSI Lab](https://psi.engr.tamu.edu/l2-arctic-corpus/), non-native English with phonetic annotations, 24 speakers and ~27h current documentation | **CC BY-NC 4.0** | Useful illustration of phonetic substitutions/deletions, but its represented L1s are not a direct Scottish/Quebec English accent solution; narrow speaker pool | Evaluate concept/method only unless license and target accent actually fit |
| **Permissioned opt-in speakers** | Recordings from consented regional volunteers with known, appropriate dialect competence | Rights negotiated per speaker/source | Better control over sampling and evaluation, but creates collection/privacy responsibility | Define minimal rights/retention, role separation, phonetically rich script and withdrawal path before collecting |

Sources: [VCTK rights](https://datashare.ed.ac.uk/items/30e7453c-9ea8-48b4-8e18-f96d0dc62928/full), [EdAcc rights](https://datashare.ed.ac.uk/items/355c07b4-500d-4e80-8f12-225e646293c9/full), [Common Voice legal terms](https://commonvoice.mozilla.org/dav/terms), [MDC example with explicit voice-cloning restriction](https://mozilladatacollective.com/datasets/cmryvrc6i014vo90786kriix5), [L2-ARCTIC license/documentation](https://psi.engr.tamu.edu/l2-arctic-corpus/).

**Data trap:** Corpus names like 'Edinburgh' refer to the collector/university, not necessarily the accent of every recorded voice. Scottish English is not a uniform timeless bundle of pronunciation rules: [variable rhoticity investigation](https://doi.org/10.1111/weng.12689). French-accented English must not be assessed with samples of native French only.

## 5. Research-specific evaluation additions

Add to the current [#43 baseline protocol](accent-design-benchmark-protocol.md), **without silently changing its original 56-sample scope**:

| Question | Trial | Fail/uncertainty condition |
| --- | --- | --- |
| Is accent distinct from voice? | Same speaker reference + 2 distinct authorized accent exemplars | Timbre/identity noticeably changes, accent remains indistinguishable |
| Does guidance strength work? | Same two references, text and seed; `w=0,9,15` | Listeners cannot rank perceptible strength, phonetics get less accurate, audio degrades |
| Is region real, not generic? | Native/competent regional blind evaluation, unseen diagnostic text | No qualified raters or evidence for region; may only claim generic family at best |
| Does donor speaker leak? | Multiple distinct accent exemplar speakers for one region; preserve target identity | Output begins imitating exemplar speaker rather than transferring shared accent |
| Does target corpus coverage matter? | Compare known trained/held-out/OOD accent categories; verify exact paper splits | Confuse trained category with extrapolation, sample leakage or overfitting |
| Is it deployable? | Cold/warm time, peak VRAM on 5070 Ti, offline weights, dependency conflicts | Exceeds 16GB, silently fetches large weights, unsafe checkpoint, license missing |
| What if multilingual? | English with French accent separate from French spoken natively | Switch language instead of accent or unsupported accent labels concealed |

## 6. Immediate deliverables / unresolved blockers

**Completed here (source-level only)**
- [x] Discovered and inspected DEFINE GitHub code, inference controls, training stages and evaluation.
- [x] Identified F5 pretrained **noncommercial** licensing, DEFINE license uncertainty and external checkpoint risk.
- [x] Mapped credible accent data sources to distinct licenses and rights questions.
- [x] Proposed separate-exemplar and phonetic/perceptual tests.

**Unresolved**
- [ ] Contact/verify upstream DEFINE code and adapter checkpoint license, published weight revision and secure source/hash.
- [ ] Validate available Scottish/French-accent English speaker clips and rights without downloads.
- [ ] Get phonetic/dialect expert review for regional contrasts; verify region-specific corpus sampling.
- [ ] Measure local inference, correctness, intensity monotonicity and identity retention with real samples.
- [ ] Independent adversarial/source review and owner #44 decision.

**No permission to train, download, add model integration, expose controls, certify a region or merge to main is implied by this document.**
