# Evaluation and Review

> **Spec Version**: 0.1.0
> **Last Updated**: 2026-07-18
> **Depends On**: [Lore Agent and Response Policy](lore-agent-and-response-policy.md)
> **Depended By**: [Web Experience](web-experience.md)

---

## Overview

> **Authoring guidance:** Define the owner-controlled evaluation system that runs hand-authored cases against controlled retrieval conditions and records randomized blinded human reviews. It invokes the lifecycle-independent lore agent directly, owns evaluation scheduling and condition concealment, and does not force evaluation outputs through a visitor conversation.

## Dependencies

### Technology dependencies

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | To be pinned | Evaluation-case execution, randomization, and review services |
| SQLite | Runtime-compatible version to be pinned | Durable cases, condition outputs, randomized pairs, reviews, notes, and tags |
| pytest | To be pinned | Deterministic service and contract verification distinct from human verdicts |

### Spec dependencies

- [Lore Agent and Response Policy](lore-agent-and-response-policy.md) — supplies a lifecycle-independent response invocation with controlled retrieval conditions.

## Parameters

> **Authoring guidance:** Add randomization, concurrency, timeout, and repeat-run values to [parameters.md](parameters.md) with rationale before using them.

| Parameter | Authoritative value | Rationale |
|-----------|---------------------|-----------|
| [`INITIAL_EVALUATION_CASE_TARGET`](parameters.md#evaluation) | 12–20 cases | Keeps initial human review broad enough to reveal failures but small enough for care |
| [`INITIAL_RETRIEVAL_ABLATION_CONDITIONS`](parameters.md#evaluation) | Normal retrieval; retrieval disabled | Provides the smallest controlled test of retrieval value |
| [`EVALUATION_VERDICT_SET`](parameters.md#evaluation) | Left better; tie; right better; both fail | Avoids forcing preference when outputs are equivalent or both unacceptable |
| [`EVALUATION_REVIEW_RETENTION_POLICY`](parameters.md#conversation-lifecycle) | Until manual deletion | Preserves human evidence under explicit owner control |
| Evaluation concurrency | `TBD` | Must reflect provider limits, cost, reproducibility, and independent scheduling rather than live-conversation rules |

## Data Structures

> **Authoring guidance:** Define evaluation-only concepts without silently adding “evaluation run” to the canonical glossary; route that term through the ubiquitous-language workflow before adoption.

### Evaluation case

Define prompt, category, human-reviewed expectations, required corpus release, guide-confirmation state when applicable, provenance, version, and active/retired status.

### Evaluation condition output

Define case identity, controlled retrieval condition, agent invocation configuration, corpus release, output, evidence bindings, timing, failure status, and reproducibility metadata.

### Output pair

Define two condition-output identities, randomized left/right assignment, concealed condition mapping, pair version, and review eligibility.

### Blinded evaluation review

Define reviewer authorization identity, verdict, optional notes and tags, timestamps, pair identity, and retained concealment/reveal state.

## Behavior

> **Authoring guidance:** Author complete rules and decision tables for these concerns.

### Case authoring and review

Specify the initial category coverage: supported facts, small multi-source synthesis, abstention, guide generation, and attempts to elicit pretrained knowledge; define human approval and versioning.

### Controlled invocation

Specify direct invocation of Lore Agent and Response Policy, explicit corpus release, normal versus disabled retrieval, equivalent non-retrieval configuration, scheduling, cancellation, and failure capture.

### Pair formation and randomization

Specify eligibility, exactly one output per condition, unbiased left/right assignment, concealment persistence, rerun handling, and prevention of metadata leakage.

### Blinded review

Specify owner-only access, verdict choices, optional notes/tags, atomic submission, whether revision is permitted, and when condition identities may be revealed.

### Retention and deletion

Specify manual deletion, links among cases, outputs, pairs, and reviews, and prevention of orphaned or misleading aggregate evidence.

### Strategy admission evidence

Specify how matched evaluations may justify GraphRAG or another retrieval strategy and why the initial system excludes an LLM judge and broad automated benchmark.

## Error Handling

> **Authoring guidance:** Define trigger, detection, response, and recovery for each case.

### Condition contamination

Cover retrieval being accidentally available in the disabled condition, prompt/config differences, release mismatch, and concealed metadata leakage.

### Missing or failed condition output

Cover pair ineligibility, both outputs failing, retry/rerun rules, and retention of failure evidence.

### Randomization or concealment failure

Cover biased assignment, duplicate pair formation, reviewer exposure to condition identity, and invalidation/re-review policy.

### Review conflict or duplicate submission

Cover concurrent reviewers if permitted, repeat submission, stale pair version, and retained notes.

### Agent/provider failure

Cover timeouts, cancellation, quota or provider errors, partial output, and distinction from an evaluated abstention.

## Implementation Notes

> **Authoring guidance:** Address reproducible case versions, seeded versus secure randomization, blinded metadata boundaries, evaluation scheduling independent of live-attempt concurrency, provider cost controls, and exportability of human evidence. Do not add automated judging or aggregate scores without a reviewed contract.

## Test Scenarios

> **Authoring guidance:** During full authoring, create the `TS-EVAL-{NUMBER}` scenario index. Cover every initial case category, retrieval-disabled isolation, release matching, pair randomization, concealment, each verdict, optional notes/tags, failed conditions, duplicate review, retention/deletion, lifecycle bypass, and strategy-admission evidence.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-07-18 | Initial skeleton |
