---
title: Synthetic Transcript Generation Research
tags:
  - research
  - transcripts
  - ai-judging
status: reference
updated: 2026-07-10
---

# Synthetic Transcript Generation Research

> [!note] Part of [[Orochi PRD]] · fed the [[Transcripts]] demo feature (batch call judging + coaching/insight/compliance actions)

Research synthesis on what else to improve in a synthetic dental call transcript design, beyond schema/persona/edge-case/label/versioning/validation basics.

---

## 1. Inject Disfluencies, ASR Noise, and Realistic Speech Artifacts

This is the single biggest gap in a naive plan. Recent research from Observe.AI (the leading contact-center AI platform) published a diagnostic framework that benchmarks synthetic transcripts against real ones across 18 behavioral and linguistic metrics. Their core finding: **no generation strategy excels at disfluency, sentiment, and behavioral realism simultaneously** — these are the hardest traits to reproduce.

For dental transcripts, this means:

- **Disfluencies**: fillers ("um," "uh," "I mean"), false starts, self-corrections, stutters. Real dental calls are full of these.
- **ASR noise**: plausible transcription errors (e.g., "crown" → "clown," dropped words, timestamp artifacts from real speech-to-text systems).
- **Interruptions and overlapping speech**.
- **Non-talk segments**: on-hold periods, keyboard typing sounds while receptionist checks schedule.

The Observe.AI pipeline uses a **dual-stage approach**: generate a clean base transcript first, then segment it into chunks and enhance each with disfluency injection + ASR noise simulation. This consistently outperforms single-pass generation.

---

## 2. Adopt a Multi-Stage Generation Pipeline

Single-pass "prompt-and-done" generation is known to produce clean but unrealistic transcripts. The DiaSynth framework (from NTU Singapore) demonstrates the value of a **three-stage pipeline**:

1. **Subtopic expansion**: Take broad topics (e.g., "dental appointment") and generate focused subtopics (e.g., "insurance verification for wisdom tooth extraction").
2. **Conditioned persona generation**: Generate personas *conditioned on specific subtopics* — much richer than generic persona assignment.
3. **Chain-of-Thought dialogue generation**: Use CoT reasoning to set characteristics (emotional state, formality, familiarity, communication medium) before generating each dialogue.

This multi-stage approach captures ~90% of the performance of training on real in-domain data, far better than direct prompting.

---

## 3. Build Explicit Diversity Control Mechanisms

A persona × scenario matrix gives combinatorial coverage, but diversity can still collapse. Research on LLM-agent conversation diversity shows:

- **Adaptive Prompt Pruning (APP)** can control output diversity with a single parameter by varying how much prompt content is retained.
- **Temperature scaling per call** prevents mode collapse (some calls at 0.3, some at 1.0).
- Measure diversity with **distinct-n** scores, entropy, and cluster analysis — don't just assume coverage from the matrix.

Without explicit controls, LLMs tend to converge on similar phrasing, similar politeness levels, and similar turn structures even with different persona inputs.

---

## 4. Add a Distributional Fidelity Evaluation (Not Just Spot-Checking)

Manual review of a handful of calls is necessary but insufficient. The Observe.AI framework provides a principled approach:

- **Behavioral metrics**: sentiment shift frequency, agent proactivity, question-type distributions.
- **Linguistic metrics**: disfluency density, repetition rate, turn-length distributions, ASR error rate.
- **Distributional comparison**: Compare histograms of these metrics between synthetic and real (or expected) distributions.

Additionally, the DiaSynth team evaluates via a **downstream task benchmark**: train a summarization (or intent classification) model on synthetic data and test on real held-out data — measuring the gap in F1/ROUGE scores.

---

## 5. Add Turn-Level Dialog Act Annotations

"Intent labels per turn" should be a first-class requirement, not optional.

Using a standard taxonomy like **ISO 24617-2** or a simplified dental-specific scheme:

`GREETING`, `IDENTIFICATION`, `ASK_REASON`, `PROVIDE_INFO`, `PROPOSE_TIME`, `NEGOTIATE_TIME`, `CONFIRM_APPOINTMENT`, `CLOSE_CALL`, `REQUEST_CLARIFICATION`, `HOLD_PLACED`, `TRANSFER`

This is especially important if the transcripts will train a dental scheduling agent — dialog act labeling is the bedrock of dialog state tracking (DST), and even partial labeling dramatically improves few-shot DST performance, as Apple's SynthDST framework demonstrates. Compare to Orochi's own fixed-vocabulary intent classification in `nlu.py` (`INTENTS = [book, reschedule, cancel, hours, insurance, emergency, other]`) — same pattern, applied per-turn instead of per-call.

---

## 6. Model Agent Behavior Beyond "Friendly vs. Efficient"

Two receptionist personas is a start, but real receptionists vary along more dimensions:

- **Compliance/script adherence**: Does the receptionist follow a script or go off-book?
- **Proactivity**: Do they suggest alternatives when slots are full, or just say "we're booked"?
- **Knowledge depth**: Can they answer clinical questions or do they defer everything?
- **Fatigue modeling**: How does behavior change if this is the 50th call of the day?

The Observe.AI framework conditions generation on **QA-form scores** — structured behavioral annotations like "Did the agent demonstrate empathy?" and "Did the agent propose a solution without prompting?" — to induce realistic behavioral variation.

---

## 7. Model Language and Accent Variation Systematically

Beyond "US English vs Japan-based callers," go deeper for dental practices specifically:

- **Non-native English speaker patterns**: grammatical simplifications, word-search pauses, circumlocution for unfamiliar dental terms.
- **Regional US dialects**: Southern politeness markers, Northeast directness, AAVE features.
- **Age-related speech patterns**: older callers with hearing difficulty, younger callers comfortable with SMS-style shorthand.
- **Dental literacy spectrum**: callers who use clinical terms ("prophylaxis") vs. lay terms ("cleaning").

These don't need to be exhaustive, but coding 2–3 caller dimensions beyond demographics significantly improves representativeness, as DiaSynth's characteristic-conditioned generation shows.

---

## 8. Add Prompt Engineering as a Documented Artifact

Rather than a one-line "exact prompt template" mention, make this more deliberate:

- **Few-shot examples**: Curate 1–3 seed transcripts (hand-crafted or real-anonymized) and include them in the generation prompt. Few-shot dramatically outperforms zero-shot.
- **Structured output format**: Use JSON schema enforcement in the prompt. Specifying a JSON output schema (vs. free text) improves field completeness and reduces hallucinations.
- **Self-consistency**: Generate 2–3 variants per call and select the best using a quality rubric (or LLM judge).
- **Prompt versioning alongside data versioning**: The prompt is part of the dataset's provenance.

---

## 9. Plan for Iterative Refinement via Self-Feedback

Rather than generating all transcripts in one batch and then reviewing, use an iterative approach:

- **Roundtrip filtering**: Generate → validate → identify issues → regenerate with targeted fixes.
- **LLM-as-judge**: Use a second LLM (different model or higher temperature) to score each transcript on realism, coherence, and persona fidelity.
- **Targeted regeneration**: If a call's sentiment trajectory is flat, regenerate with explicit sentiment guidance.

This is how the DiaSynth and Synthetic-Persona-Chat frameworks achieve high quality — not from a single perfect prompt, but from feedback loops.

---

## 10. Add HIPAA/Compliance-Aware Content Patterns

For dental calls specifically, transcripts should include:

- **Consent language**: "I need to let you know this call may be recorded for quality purposes."
- **PHI verification patterns**: "Can you confirm your date of birth?" — standard in real dental calls.
- **Insurance disclaimer language**: "Your insurance may not cover the full amount; you'll be responsible for any remaining balance."
- **Cancellation policy mentions**: "We require 24 hours' notice for cancellations."

These aren't just nice-to-have — if the transcripts train a real scheduling agent, it must learn to produce these compliance utterances. Orochi's [[Transcripts]] feature uses a simplified version of this as **compliance flags** (missing insurance disclaimer, missing minor-consent confirmation) on seeded demo calls.

---

## Summary: What to Add to a Generation Plan

| # | Enhancement | Priority |
| --- | --- | --- |
| 1 | Disfluency + ASR noise injection (dual-stage pipeline) | **Critical** |
| 2 | Multi-stage generation (subtopic → persona → CoT dialogue) | **Critical** |
| 3 | Diversity control mechanisms (APP, temperature scaling, metrics) | High |
| 4 | Distributional fidelity evaluation (18-metric framework) | High |
| 5 | Turn-level dialog act annotations (ISO 24617-2 or dental-specific) | High |
| 6 | Richer agent behavior modeling (compliance, proactivity, fatigue) | Medium |
| 7 | Language/accent variation matrix | Medium |
| 8 | Prompt engineering as documented artifact (few-shot, self-consistency) | Medium |
| 9 | Iterative self-feedback refinement loop | Medium |
| 10 | HIPAA/compliance content patterns | High for dental |

## Decision: what Orochi actually built (2026-07-10)

Downstream target chosen: **(c) prototyping a demo UX** for prospects, not agent training or production QA analytics. Given that, most of the above rigor (1–5, 7–9) was intentionally **not** applied — disfluencies/ASR noise, multi-stage generation, diversity metrics, and iterative self-feedback are overkill for a sales demo. What was kept:

- Simplified per-call **compliance flags** (from #10) on a handful of the 25 seeded transcripts.
- A fixed small vocabulary for judgment output (coaching notes / insights / flags / quality score), matching the taxonomy discipline of #5 but applied at judgment-time rather than as dialog-act labels.
- Judgments are **precomputed/mocked**, not live LLM calls — consistent with `nlu.py`'s offline-first pattern elsewhere in Orochi.

See [[Transcripts]] for the resulting feature (batch overview + per-call drill-down at `/transcripts`).
