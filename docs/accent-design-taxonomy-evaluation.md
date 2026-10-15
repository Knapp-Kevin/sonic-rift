# Accent Design Studio: taxonomy, corpus and evaluation policy

> **Research snapshot:** Findings and model-license claims reflect the original October 10, 2026 assessment. Links were reconciled to the Sonic Rift repository on October 15. No inference, accent authenticity, updated dependency licensing, or hardware performance is newly certified by merging this document. The owner GO/NO-GO gate remains #44.

**Status:** research specification for review, not a shipped feature.  
**Checked:** 2026-10-10  
**Tracker:** [#42](https://github.com/Knapp-Kevin/sonic-rift/issues/42), [#40 epic](https://github.com/Knapp-Kevin/sonic-rift/issues/40).  
**Implementation gate:** [#44](https://github.com/Knapp-Kevin/sonic-rift/issues/44).

## 1. What an accent setting means

A named accent is a **claim about speech**, not a label on the nationality of a voice or the words in a script. Model and UI must keep the following separate:

| Dimension | Examples | Rule |
| --- | --- | --- |
| Spoken language | English, French | Language of output words and pronunciation system; not inferred from speaker origin |
| Accent target | Scottish English; French-accented English | Broad speech-variety intent |
| Regional target | Glasgow/Edinburgh; Parisian-/Quebec French-accented English | Research target with validation requirements, **not inherently supported** |
| Native language region | Metropolitan French in French, Quebec French in French | A different task from English spoken with French influence |
| Accent method | Prompt-derived, native model enum, consented reference clone | Record how the target was requested; no cross-method equivalence |
| Requested strength | Subtle, moderate, strong | Prompt guidance / **ordinal user intent**, not an audio percentage or promised phonetic transform |
| Speaker attributes | Register, pitch, age impression, timbre | May be manipulated but must not stand in for accent |
| Delivery | Speed, emotion, whisper, pace | Separate from accent; may affect perceived accent and must be controlled in tests |
| Verification | Untested, engine claim, listener-reviewed, region-reviewed | Required disclosure in evaluation and future model UI |

## 2. Draft semantic structure (specification, not implementation)

Example *candidate* metadata for the future architecture review:

~~~json
{
  "spoken_language": "en",
  "accent": {
    "family_id": "scottish_english",
    "region_id": "glasgow",
    "selection_kind": "free_text_target",
    "requested_intensity": "moderate",
    "calibrated_intensity": null,
    "validation_status": "untested",
    "region_claim": "research_only"
  },
  "voice_attributes": {"register": "low", "timbre": "warm"},
  "source": {
    "method": "designed",
    "model_repo_id": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    "model_revision": null,
    "prompt_recipe_version": null,
    "reference_audio_hash": null,
    "reference_transcript_hash": null
  }
}
~~~

**Schema principles:**
- Use neutral machine IDs; the labels and localization are UI concerns.
- Never infer a region from broad country/language strings. A British-English enum is **not** a verified Glasgow accent.
- Missing/unvalidated regions must remain selectable only in a clearly experimental test context (if approved) or visibly disabled in supported presets.
- A user-selected intensity is stored as **intent**, not a measured property of the audio.
- Distinguish the origin of a saved designed voice from a consented human-reference voice. Do not default 'consent verified' to true.
- Store model revision/hash when known; unknown is a valid state, not a reason to manufacture metadata.
- Acoustic similarity to a saved reference is not automatically equivalent to regional phonological authenticity.

## 3. Initial research inventory

| Speech task | UI-facing research target | Method candidate | Current confidence |
| --- | --- | --- | --- |
| English speech | Neutral/unspecified English | Standard engine generation | Comparator only, not a region certification |
| Scottish English | Broad Scottish | Qwen/VoxCPM descriptive design | Hypothesis, **unverified** |
| Scottish English | Glasgow | Qwen/VoxCPM descriptive design | Hypothesis, **unverified** |
| Scottish English | Edinburgh | Qwen/VoxCPM descriptive design | Hypothesis, **unverified** |
| English with French influence | Metropolitan French-accented English | Qwen/VoxCPM description; consented reference | Hypothesis, **unverified** |
| English with French influence | Quebec French-accented English | Qwen/VoxCPM description; consented reference | Hypothesis, **unverified** |
| French-language speech | French (region unspecified) | Model multilingual language selection | **Distinct task**; not equivalent to French-accented English |
| French-language speech | Metropolitan / Quebec French in French | Explicit variety research only | Hypothesis, **unverified** |
| English accent enum | British, American, etc. | OmniVoice supported structured attribute | API attribute **documented**; audio authenticity unverified |

Do not use exaggerated spelling, nationality jokes, stereotypes or forced regional slang in prompt templates. Such writing can fake an accent impression while the audio phonology remains wrong.

## 4. Test texts: proposed permission-safe, original micro-corpus

These are **newly authored sentences**, not samples taken from a book or speaker dataset. The corpus is designed to be understandable and moderately informative without guaranteeing a particular regional diagnostic. A qualified dialect reviewer should revise/approve these before claiming Glasgow-versus-Edinburgh discriminability.

| ID | Type | English passage |
| --- | --- | --- |
| EN-N0 | Neutral control | The meeting starts at eleven, and the report will be ready before lunch. |
| EN-V1 | Rhoticity, vowel observations | The car turned past the park before the rain began. |
| EN-V2 | Vowel range and rhythm | Mary brought a small glass of water into the garden. |
| EN-C1 | Consonants and connected speech | Would you carry the parcel to the station before breakfast? |
| EN-P1 | Prosody and lexical stress | I thought the new house would be close, but it was farther down the road. |
| EN-L1 | Generalization sentence | Please check the numbers, close the window, and call me when the train arrives. |

French-language smoke test (explicitly a **different task**): 
- FR-N0: La porte est ouverte et le train arrive à huit heures.
- FR-N1: Nous passerons près du jardin avant le déjeuner.

Long-form drift text should concatenate distinct, original neutral paragraphs, 60 to 120 seconds total, without phonetic hint tags or region-specific vocabulary. For blind comparison, use **the identical text per language across engines/intensities**. A/B evaluation should also include an unseen sentence not present in voice-design references.

## 5. Requested intensity: do not pretend this is a calibrated parameter

Three proposed instructions to investigate (not UI labels guaranteed to work):
- **Subtle:** Maintain clear international English with only lightly noticeable regional pronunciation traits.
- **Moderate:** Use audible regional pronunciation and conversational prosody while remaining clearly intelligible.
- **Strong:** Use a strongly recognizable regional pronunciation and rhythm, without caricature or replacing words with stereotypical expressions.

Keep the same non-accent speaker attributes and the same spoken text across these conditions. Do not turn accent into speed, pitch or volume. If user intent cannot be reliably distinguished by listeners, either remove the control or present it as experimental prompt guidance. Do **not** map these to 25/50/100% audio effect settings.

## 6. Blind evaluation rubric and claims ladder

Randomize audio IDs so evaluators cannot infer model, target or requested intensity. Collect their native/dialect familiarity and whether they listened with headphones.

For each anonymized take record separate 1–5 ordinal ratings:
1. **Intelligibility:** how reliably can the exact text be understood? Capture transcription errors where practical.
2. **Naturalness:** does the reading sound like unforced human speech rather than artificial phoneme edits?
3. **Perceived accent family:** open/forced-choice recognition plus 'uncertain' and 'none of these', **before** showing target.
4. **Perceived region (if competent):** whether the accent actually resembles the claimed region, with optional phonetic notes.
5. **Perceived accent strength:** separately judged degree, blind to requested setting.
6. **Speaker continuity:** short/long/ref-cloned take retains the same speaker qualities.
7. **Artifacts/drift:** clipped words, pronunciation errors, sudden accent switching and changes over time.

Analysis should report distributions and disagreements, not just one averaged 'accent score.' Record blind sample count and evaluator provenance without collecting unnecessary identities.

**Claim ladder:**
- *Tier 0:* prompt/model accepts instructions. May only advertise 'request an accent experiment.'
- *Tier 1:* a reproducible generated audio sample exists. May advertise 'sample available,' not accuracy.
- *Tier 2:* independent blinded listeners recognize **broad accent family** versus control. May advertise 'experimental broad accent support,' conditioned on benchmark quality.
- *Tier 3:* reviewers competent in the specific region confirm consistency on multiple unseen clips, with useful intelligibility and low drift. Only then contemplate named-region support.

**Proposed gate, not a statistical guarantee:** seek at least 2 competent regional reviewers, at least 2 separate texts and multiple random seeds before a region-specific public claim. If no competent reviewers are available, a detailed region remains **unvalidated**; do not replace them with a general accent classifier and call it authoritative.

## 7. Reference-audio provenance, consent and data controls

- Require documented permission to use **any identifiable real speaker** for cloning or research. Do not infer consent from public availability on a video, social network or podcast.
- Preserve source authority/permission, recording date where supplied, chosen allowed uses, permitted storage duration and deletion workflow. Do not ship reference audio/audio clips in the Git repository absent explicit redistribution rights.
- Prefer personally recorded consenting speakers or properly licensed research material whose terms clearly permit TTS voice cloning, derivative generation, reproduction and evaluation. A CC license alone may not settle publicity, privacy or impersonation permissions.
- Human datasets should be stored locally, access limited to authorized evaluators. Logs/results should use hashes, randomized sample IDs and permission-safe summaries; no personal voice samples attached to issues by default.
- Keep local generation local; network operations (e.g. Hugging Face downloads) require explicit user action. Respect per-model training and deployment licenses (notably OmniVoice non-commercial weights).
- Do not provide controls aimed at covert imitation of named real people; the purpose of accent work is fictional/designed voice qualities or permissioned samples.

## 8. UI/accessibility implications for the later ADR

- Spoken-language selector and accent selector need independent accessible labels and explanatory text.
- The control must reveal whether a region is **documented native**, **experimental prompt**, **reference-derived**, **unsupported**, or **not installed**.
- Family/region choices should update without silently changing script language, saved voice, model, or downloaded files.
- Include keyboard accessible select/filter, deterministic focus management, screen-reader clarity, high contrast and light/dark checks.
- If intensity is introduced, show 3 words (Subtle / Moderate / Strong) and a plain disclaimer 'best-effort instruction', not an unexplained percentage slider.
- Preserve existing free-form description and Clone/Remix. Never silently translate or normalize away requested accents.

## 9. Review / completion status

**Ready for protocol review, not field-verified**:
- [x] Candidate speech-language versus accent taxonomy written.
- [x] Initial original test corpus and blind-rating rubric drafted.
- [x] Disclosure, provenance, consent, accessibility and claims ladder recorded.
- [ ] Dialect-trained reviewer validates phonetic discriminability of proposed corpus.
- [ ] Competent regional judges recruited or evidence limitation recorded.
- [ ] Cross-engine listening experiments produce valid results in #43.
- [ ] ADR/owner approves exact supported tiers/controls in #44.

This is a research input, not implementation sign-off.
