# Accent Design Studio: reproducible benchmark protocol (NOT YET RUN)

> **Research snapshot:** Findings and model-license claims reflect the original October 10, 2026 assessment. Links were reconciled to the Sonic Rift repository on October 15. No inference, accent authenticity, updated dependency licensing, or hardware performance is newly certified by merging this document. The owner GO/NO-GO gate remains #44.

**Status:** benchmark plan and result schema only; **zero audio samples generated or evaluated in this research pass**.  
**Date:** 2026-10-10  
**Owner issue:** [#43](https://github.com/Knapp-Kevin/sonic-rift/issues/43); inputs: [engine research #41](https://github.com/Knapp-Kevin/sonic-rift/issues/41) and [taxonomy #42](https://github.com/Knapp-Kevin/sonic-rift/issues/42).  
**Implementation authorization:** only after [#44 ADR](https://github.com/Knapp-Kevin/sonic-rift/issues/44) approval.

Reference documents:
- [Engine API, adapter, license audit](accent-design-engine-research.md)
- [Accent taxonomy, original corpus and listener policy](accent-design-taxonomy-evaluation.md)

## 0. Safety / execution rules

1. Do not automatically install models, download datasets, trigger cloud inference, change production settings or train checkpoints. If Qwen/VoxCPM are missing locally, log the blocker and obtain explicit resource approval.
2. Run locally/manual-first on the target Windows machine. Note all GPU memory/error data from actual runs; do not infer a 16 GB VRAM guarantee from model size.
3. Do not commit audio samples, identifiable human voices, generated clips, personal files, hidden tokens or local absolute paths. Commit only rights-safe summaries, anonymized metrics, hashes and protocol artifacts.
4. Treat a stable seed as a *request for repeatability*, not proof of exact deterministic output across GPU/runtime/mode changes.
5. Never count test harness success as evidence of regional authenticity.

## 1. Source and runtime manifest (fill before every run)

Store one manifest per session with:
- benchmark_schema_version; session_id; UTC time; git commit SHA (working tree dirty flag); host OS/build; GPU/driver/CUDA/PyTorch; Python version;
- engine backend, package version, model repository ID, exact weight revision SHA, license source, language, task mode, whether Base clone model is also loaded;
- audio sampling rate; cold/warm run flag; approximate peak GPU allocated/reserved VRAM; load time; first audio/total synthesis time; RTF if meaningful;
- text corpus version/hash and sample ID; target family/region; requested intensity; complete instructions; full user overrides; seed; decoding/inference parameters;
- reference-audio hash, transcription hash, consent/rights record ID (never speaker identity in public results); clip duration and quality summary;
- output local filename for operator only, output SHA-256 in committed summary, valid/failed flag, failure logs stripped of secrets.

Suggested manifest field types / example **illustrative only**:

~~~json
{
  "benchmark_schema_version": 1,
  "status": "NOT_RUN",
  "run_id": "REPLACE_WITH_RUN_IDENTIFIER",
  "git_revision": null,
  "engine": "qwen3",
  "model_revision": null,
  "task": "voice_design",
  "spoken_language": "en",
  "accent_target": "scottish_english",
  "region_target": null,
  "requested_intensity": "moderate",
  "prompt": "REPLACE_WITH_EXACT_INSTRUCTION",
  "seed": null,
  "test_text_id": "EN-V1",
  "reference_audio_sha256": null,
  "generated_audio_sha256": null,
  "human_evaluation_status": "NOT_EVALUATED",
  "runtime": {"gpu": null, "peak_vram_gb": null, "seconds": null},
  "failure": null
}
~~~

**Never treat the literal illustrative example as benchmark evidence.**

## 2. Pilot design: manageable, reproducible, and decision-oriented

Use only available configured Qwen3 VoiceDesign and VoxCPM2 Design initially, with consented reference-clone as a separate conditional trial. The pilot deliberately tests whether free-text prompts move audio perceptibly **before** investing in fine-grained regional presets.

For each engine:
- Baseline neutral English description (same voice traits as accent targets).
- Broad Scottish English with subtle / moderate / strong requested intensity.
- French-accented English (French influence on spoken English), subtle / moderate / strong.
- **2 disclosed seeds for each condition**, start with a single shared neutral sample text (EN-N0) and one diagnostic text (EN-V1).
- This is **14 conditions across two engines** (7 prompt conditions per engine), multiplied by 2 seeds × 2 texts = **56 generated examples** if both engines are installed. This is a **test plan, not an executed count**.

Keep voice age/register/timbre, output language and test text constant **within each engine**. Do not compare two engines' raw outputs as if they used an identical underlying speaker identity. When possible compare to a neutral sample using separate paired similarity judgments.

### Conditional expanded matrix (not automatic)

After pilot results and reviewer availability, consider Glasgow, Edinburgh, metropolitan French-accented English, Quebec French-accented English; **these remain prompt hypotheses, not certified supported regions**. Add 2 seeds and at least 2 unseen texts each, with consented reference-audio clone comparison if available.

Separately test *French-language synthesis* on FR-N0/FR-N1; do not score it as English-with-French-accent. OmniVoice is a useful British/American **fixed-enum** baseline, but its design vocabulary has no Scottish or French-accented English value; exclude fabricated enums from testing.

## 3. Prompt design / parameter control

Use a simple template with independent regions and voice attributes:

> An adult speaker with a warm, low midrange voice, reading natural English clearly and evenly. Use [TARGET_ACCENT] with [REQUESTED_STRENGTH_DESCRIPTION]. Keep consistent articulation and avoid comedic, exaggerated or stereotypical pronunciations.

Instantiate only the bracketed accent+strength descriptions; avoid hidden changes to speed, volume, pitch, emotion, verbosity or vocabulary. Also collect a manual description variant to test prompt sensitivity, but record it as a separate condition.

**VoxCPM2:** verify effect of parenthesized control text and whether use of an exact transcript switches to its continuation-based mode. Benchmark (a) Design, (b) reference+style and (c) reference+transcript separately; do not conflate.

**Qwen3:** design from a description, then create a reusable clone/reference; test handoff into Base mode and long-document chunk boundaries for drift and GPU pressure. A designed voice reused across chunks still needs listening confirmation.

**OmniVoice:** one documented accent enum per group. British is not a synonym for Scottish regional verification. Design attribute combinations may be ignored by model according to upstream caveat.

**Chatterbox:** only test permissioned reference voice; language tag and CFG behavior may affect accent carryover. Its expressiveness parameter is not strength.

## 4. Operator procedure (manual, no additional CI)

1. Record git SHA, model/adapter version, environment, existing model availability, license eligibility, free disk and safe GPU memory budget.
2. Confirm source recordings are either entirely synthetic or permissioned. Record no identifiable recordings or consent documents in public GitHub.
3. Select test corpus IDs and hash exact UTF-8 text. For each engine and condition record **exact** prompt, seed, synthesis settings and output SHA.
4. Generate pilot audio, store locally in a private experimental output directory, and capture elapsed time/VRAM. On missing model, VRAM failure or poor generation, preserve failure evidence and stop that condition without auto-downloading fallback.
5. Create a blind randomized listening set with IDs that disclose neither engine, region target, nor intensity. Keep a restricted map from ID to source condition.
6. Have evaluators rate blind audio using rubric in [taxonomy](accent-design-taxonomy-evaluation.md); collect familiarity with regions without personal identifiers.
7. Analyze per-condition recognizability, quality, confidence, failures, disagreement and requested-strength ranking. Do not cherry-pick the one successful seed.
8. Repeat same voices over at least 60s multi-section narration; compare first/last sections and clone from synthetic designed anchor.
9. Publish a redacted summary with method limits and **all failures**, not raw samples or private paths. Independent reviewer checks whether claims match the evidence.

## 5. Listening review

Ratings and decisions should follow the taxonomy rubric. Record blind 1–5 ordinal scales for intelligibility, naturalness, perceived strength, speaker continuity, artifact/drift; collect free-response perceived family and region where qualified.

**Do not force answers**: evaluators can choose 'uncertain' or 'none of the above'. To claim region, seek independent competent regional listeners, multiple unrelated texts and multiple seeds, and note any disagreements.

Do not combine these dimensions into one opaque score. Compare broad recognition against neutral controls, separately from readability and model failure rate. A higher perceived accent strength with degraded intelligibility is not automatically an improvement.

## 6. Results table to fill

| Run group | Model revision | Task | Language | Accent target | Requested strength | Seeds/texts completed | Intelligibility | Naturalness | Listener recognition | Drift | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen-neutral | NOT RUN | design | en | neutral | none | 0 | n/a | n/a | n/a | n/a | NOT RUN |
| Qwen-Scottish | NOT RUN | design | en | Scottish broad | 3 levels | 0 | n/a | n/a | n/a | n/a | NOT RUN |
| Qwen-French-English | NOT RUN | design | en | French-accented English | 3 levels | 0 | n/a | n/a | n/a | n/a | NOT RUN |
| Vox-neutral | NOT RUN | design | en | neutral | none | 0 | n/a | n/a | n/a | n/a | NOT RUN |
| Vox-Scottish | NOT RUN | design | en | Scottish broad | 3 levels | 0 | n/a | n/a | n/a | n/a | NOT RUN |
| Vox-French-English | NOT RUN | design | en | French-accented English | 3 levels | 0 | n/a | n/a | n/a | n/a | NOT RUN |

## 7. Go/limited-go/no-go recommendation rules

- **GO (broad experimental accents only):** at least one engine creates broadly recognizable accents in repeatable blind comparisons with acceptable intelligibility, no severe drift and legitimate license; disclose that requested strength is best-effort.
- **LIMITED GO:** broad accent description works inconsistently but reference cloning is a better documented path, or only certain engines/conditions pass; limit UI to evidenced modes and explicit experimental labels.
- **NO-GO:** poor recognizability or intelligibility, persistent failures, unacceptable latency/resources, inadequate evaluation population, or license/provenance constraints. Do not mask NO-GO by adding a polished slider.
- **Region-specific GO requires extra evidence** from qualified listeners and approval in #44; a good broad Scottish result never automatically certifies Glasgow or Edinburgh.
- **Training/fine-tuning discussion:** initiate a separate decision only if comparisons show a real gap and a supported training stack plus permissioned dataset exists. No training is included in this protocol.

## 8. Completion and live blockers

- [x] Protocol, manifest schema and pilot matrix drafted.
- [x] Engine-first, manual/local-first evaluation and license boundaries specified.
- [ ] Correct target Windows model availability, versions, resource budget and possible engine conflicts verified at runtime.
- [ ] Pilot generated: **0 / planned 56 audio examples**.
- [ ] Independent qualified regional listening evidence: **none**.
- [ ] Long-form and re-clone retention results: **none**.
- [ ] Result analysis/adversarial review and final ADR decision: **not done**.

**The next physical execution point is a local Windows inference session using available engines and permissioned samples. Until then, #43 remains open and #44 cannot grant implementation approval.**
