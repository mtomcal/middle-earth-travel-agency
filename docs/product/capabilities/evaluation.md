# Evaluation

> Maturity: Draft intent

## Purpose

Evaluation determines whether agentic consultation and retrieval-grounded
guide generation produce useful, coherent, and trustworthy travel guides. It
compares the same product policy with retrieval enabled and disabled and
preserves blinded human judgments instead of relying on demonstrations or an
automated model judge.

## Desired outcomes

- The owner can test clarification, trip-brief development, support,
  synthesis, abstention, temporal consistency, inference labeling, and guide
  usefulness.
- Retrieval-enabled and retrieval-disabled outputs differ only in the intended
  condition.
- Reviewers cannot infer the condition assignment before recording a verdict.
- Failed evaluations remain evidence rather than disappearing through retries.
- Results inform whether to keep, change, or deepen the retrieval and planning
  strategies.

## Boundaries

This capability owns case authoring, controlled planning and guide invocation,
matched condition outputs, randomized pairing, concealment, human verdicts,
notes, tags, and evaluation evidence retention.

It does not own planning behavior, live consultation state, guide persistence,
corpus release contents, or automated product scoring.

## Durable invariants

- Evaluation invokes the same planning and guide-generation policies as the
  live product without requiring a traveler consultation.
- Each comparison uses the same reviewed case, trip brief where supplied,
  corpus release, model configuration, and non-retrieval settings.
- The initial conditions are normal retrieval and retrieval disabled.
- The disabled condition cannot reach corpus evidence through another tool or
  hidden context.
- Left/right assignment is randomized and remains concealed until the review
  no longer depends on blindness.
- A verdict is one of `left better`, `tie`, `right better`, or `both fail`;
  review does not force a winner.
- Notes and tags are optional supporting evidence, not substitutes for a
  verdict.
- Missing, failed, contaminated, or exposed condition outputs cannot form a
  valid blinded comparison.
- Case versions, outputs, failures, pair assignments, and reviews remain
  traceable until deliberate deletion.
- Strategy decisions use matched human evidence; an LLM judge is outside the
  initial evaluation.

## Key decisions and rationale

### Test both consultation and artifact quality

A strong guide can result from an unrealistic prefilled brief, while a pleasant
conversation can still yield a weak artifact. The suite therefore needs both
multi-turn consultation cases and fixed-brief generation cases.

### Start with a small reviewed suite

Approximately 12 to 20 cases provide enough variety to expose failure modes
while remaining practical for careful owner review. Breadth without reliable
human expectations would create a larger but weaker benchmark.

### Blind the retrieval ablation

Retrieval is a central product bet. Randomized concealment reduces the owner's
ability to reward the intended architecture merely because it is intended.

### Preserve both-fail and tie verdicts

Forcing a preference can make equally weak or equivalent guides look like
evidence for one condition. The verdict set preserves those outcomes.

## Representative scenarios

- A vague journey case tests whether both conditions ask consequential
  questions and produce coherent trip briefs.
- A fixed supported brief produces two eligible guides whose identities are
  hidden behind a randomized pair.
- Retrieval accidentally remains available in the disabled condition; the
  comparison is invalidated rather than reviewed.
- One provider call fails; the failure is retained, but no misleading pair is
  formed from only one successful output.
- The owner submits `both fail` because both guides invent route precision; the
  verdict and optional notes are stored without revealing the condition early.
- A new retrieval strategy is proposed; it is compared through matched cases
  rather than admitted solely from architectural preference.

## Open questions

Success thresholds, multi-turn case representation, case-version policy,
randomization details, rerun rules, review revision, concurrency, timeouts, and
condition reveal policy remain open. See [product outcomes](../outcomes.md) and
[open product questions](../open-questions.md).
