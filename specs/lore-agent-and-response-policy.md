# Lore Agent and Response Policy

> **Spec Version**: 0.1.0
> **Last Updated**: 2026-07-18
> **Depends On**: [Corpus Retrieval and Agent Tools](corpus-retrieval-and-agent-tools.md)
> **Depended By**: [Evidence Presentation and Attribution](evidence-presentation-and-attribution.md), [Conversation and Attempt Lifecycle](conversation-and-attempt-lifecycle.md), [Evaluation and Review](evaluation-and-review.md)

---

## Overview

> **Authoring guidance:** Define the lore agent’s home and its lifecycle-independent response-execution contract. The system owns orchestration, context assembly, the allowed-tool boundary, retrieved-evidence-only reasoning, abstention, claim segmentation and passage bindings, and typed lore-answer and guide-message emission; it does not own live attempt concurrency, citation URL/license presentation, browser transport, or evaluation scheduling.

## Dependencies

### Technology dependencies

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | To be pinned | Application/service models and orchestration boundary |
| LangChain DeepAgent | To be pinned | Initial agent orchestration with later LangGraph descent only when demonstrated necessary |
| Model provider and model | `TBD` | Language generation selected against grounding, streaming, cancellation, quality, and cost requirements |

### Spec dependencies

- [Corpus Retrieval and Agent Tools](corpus-retrieval-and-agent-tools.md) — supplies the only allowed corpus-search, surrounding-context, and provenance-inspection operations.

## Parameters

> **Authoring guidance:** Define model limits, tool-call limits, generation timeouts, retry policy, and any guide-structure limits in [parameters.md](parameters.md) with evidence-based rationale.

| Parameter | Authoritative value | Rationale |
|-----------|---------------------|-----------|
| [`MODEL_PROVIDER`](parameters.md#unresolved-selections) | `TBD` | Requires matched evidence for grounding, streaming, cancellation, cost, and operations |
| [`MODEL_ID`](parameters.md#unresolved-selections) | `TBD` | Must be evaluated rather than selected from pretrained reputation |
| Maximum agent steps | `TBD` | Must control loops and latency without preventing necessary multi-source synthesis |
| Generation timeout | `TBD` | Must align with cancellation and incomplete-output semantics rather than be guessed |

## Data Structures

> **Authoring guidance:** Define typed, implementation-independent structures and preserve the distinction between successful messages and incomplete streamed output.

### Response invocation

Define visitor input, permitted prior context, explicit corpus release identity, invocation purpose, retrieval condition, cancellation signal, and allowed typed output variants without requiring a live conversation.

### Retrieved evidence set

Define stable passage identities, approved text, provenance references, and support status without assuming every retrieval hit supports a claim.

### Grounded claim binding

Define an exact claim span, one or more supporting passage identifiers, support relationship, and any inference marker; claim segmentation granularity remains an explicit authoring decision.

### Lore answer emission

Define successful grounded-claim content, abstention form, typed internal events, and final response data without user-facing citation URLs or HTML.

### Guide message emission

Define temporal frame, traveler perspective, structured sections, grounded claim bindings, visibly labelable itinerary inferences, and source identities.

## Behavior

> **Authoring guidance:** Author complete rules and decision tables for these concerns.

### Context assembly

Specify which successful prior messages may enter context, exclusion of failed/cancelled incomplete output, visitor-intent preservation, explicit release scoping, and resistance to instructions that seek pretrained Tolkien knowledge.

### Allowed-tool policy

Specify the approved corpus tools and typed response emission operations, with explicit denial of live web, arbitrary filesystem, shell, code execution, and unapproved external tools.

### Grounding and abstention

Specify that factual claims may use only retrieved approved passages, how support is assessed, when evidence is insufficient, and why pretrained Tolkien knowledge never fills evidence gaps.

### Claim segmentation and binding

Specify ownership of claim spans and passage bindings, compound-sentence treatment, multi-source synthesis, connective inference, conflicting accounts, uncertainty, and validation before emission.

### Ordinary lore answering

Specify newcomer-oriented explanation, citation-ready bindings, streamed internal events, final typed output, and prohibited unsupported details.

### Guide-message policy

Specify explicit request or confirmation, Age/date handling, traveler perspective, supported factual content, inference labeling, and prohibitions on invented distance, time, road, hazard, or accessibility details.

### Lifecycle-independent invocation

Specify the same response policy for live conversation and controlled evaluation callers while keeping active-attempt concurrency and evaluation-run scheduling outside this system.

### Generative UI emission

Specify that only typed block identities offered by the application contract may be emitted and that arbitrary agent HTML is forbidden.

## Error Handling

> **Authoring guidance:** Define trigger, detection, response, and recovery for each case.

### Insufficient retrieved evidence

Define conversion to abstention rather than failure or pretrained completion.

### Unsupported or unbound factual claim

Define pre-emission validation, rejection or repair limits, and prevention of unsupported final output.

### Tool failure or malformed tool result

Define safe retry eligibility, evidence invalidation, abstention, and caller-visible failure without widening the tool boundary.

### Invalid guide request or temporal frame

Cover missing confirmation, unsupported date precision, undefined traveler perspective, and inability to ground itinerary details.

### Cancellation during execution

Define responsiveness to the caller’s cancellation signal, terminal event behavior, and the limit of best-effort backend propagation.

### Invalid typed response or generative block

Cover schema violations, unknown block identities, arbitrary HTML, and safe failure before trusted rendering.

## Implementation Notes

> **Authoring guidance:** Address determinism where possible, model nondeterminism where unavoidable, tool-loop bounds, cancellation checkpoints, internal typed event ordering, prompt-injection resistance, and test seams. Do not expose orchestration-library objects as browser contracts, choose a provider prematurely, or make the agent responsible for URL and license rendering.

## Test Scenarios

> **Authoring guidance:** During full authoring, create the `TS-AGENT-{NUMBER}` scenario index. Cover supported single-source facts, multi-source synthesis, abstention, pretrained-knowledge elicitation, conflicting accounts, failed prior-output exclusion, guide confirmation, temporal uncertainty, itinerary inference, forbidden route details, tool failure, cancellation, invalid bindings, arbitrary HTML, and equivalent live/evaluation policy.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-07-18 | Initial skeleton |
