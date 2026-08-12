# Evaluation

> Maturity: Draft intent

## Purpose

Evaluation determines whether the product hypotheses hold under controlled
conditions. It compares the same response policy with retrieval enabled and
disabled and preserves blinded human judgments instead of relying on anecdotal
demonstrations or an automated model judge.

## Desired outcomes

- The owner can test support, synthesis, abstention, guides, and attempts to
  elicit pretrained knowledge.
- Retrieval-enabled and retrieval-disabled outputs differ only in the intended
  condition.
- Reviewers cannot infer the condition assignment before recording a verdict.
- Failed evaluations remain evidence rather than disappearing through retries.
- Results inform whether to keep, change, or deepen the retrieval strategy.

## Boundaries

This capability owns case authoring, controlled response invocation, matched
condition outputs, randomized pairing, concealment, human verdicts, notes,
tags, and evaluation evidence retention.

It does not own response behavior, visitor conversation state, corpus release
contents, or automated product scoring.

## Durable invariants

- Evaluation invokes the same response policy as the live product without
  requiring a visitor conversation.
- Each comparison uses the same reviewed case, corpus release, model
  configuration, and non-retrieval settings.
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

### Start with a small reviewed suite

Approximately 12 to 20 cases provide enough variety to expose failure modes
while remaining practical for careful owner review. Breadth without reliable
human expectations would create a larger but weaker benchmark.

### Blind the retrieval ablation

Retrieval is a central product bet. Randomized concealment reduces the owner's
ability to reward the intended architecture merely because it is the intended
architecture.

### Preserve both-fail and tie verdicts

Forcing a preference can make equally weak or equivalent outputs look like
evidence for one condition. The verdict set preserves those important outcomes.

## Representative scenarios

- A supported factual case produces two eligible condition outputs whose
  identities are hidden behind a randomized pair.
- Retrieval accidentally remains available in the disabled condition; the
  comparison is invalidated rather than reviewed.
- One provider call fails; the failure is retained, but no misleading pair is
  formed from only one successful output.
- The owner submits `both fail` with optional notes; the verdict is stored
  atomically without revealing the condition early.
- A new retrieval strategy is proposed; it is compared through matched cases
  rather than admitted solely from architectural preference.

## Open questions

Success thresholds, case-version policy, randomization details, rerun rules,
review revision, concurrency, timeouts, and condition reveal policy remain open.
See [product outcomes](../outcomes.md) and
[open product questions](../open-questions.md).

