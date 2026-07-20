# Conversation and Attempt Lifecycle

> **Spec Version**: 0.1.0
> **Last Updated**: 2026-07-18
> **Depends On**: [Corpus Curation and Releases](corpus-curation-and-releases.md), [Lore Agent and Response Policy](lore-agent-and-response-policy.md)
> **Depended By**: [Web Experience](web-experience.md)

---

## Overview

> **Authoring guidance:** Define the server-owned lifecycle for stable-URL conversations and their live generation attempts. This system owns authoritative attempt state, one-active-attempt concurrency, context eligibility, release selection, streaming state, cancellation, failure, retry replacement, retention, and manual deletion; it invokes but does not contain the lore agent.

## Dependencies

### Technology dependencies

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | To be pinned | Application lifecycle services and typed internal events |
| SQLite | Runtime-compatible version to be pinned | Durable conversations, messages, attempts, and retained metadata |

### Spec dependencies

- [Corpus Curation and Releases](corpus-curation-and-releases.md) — supplies validated release availability and active-release identity for selection.
- [Lore Agent and Response Policy](lore-agent-and-response-policy.md) — supplies lifecycle-independent response invocation and typed event contracts.

## Parameters

> **Authoring guidance:** Add timeouts, size limits, and deletion constraints to [parameters.md](parameters.md) with rationale before using them.

| Parameter | Authoritative value | Rationale |
|-----------|---------------------|-----------|
| [`MAX_ACTIVE_ATTEMPTS_PER_CONVERSATION`](parameters.md#conversation-lifecycle) | 1 | Prevents context, output, cancellation, and persistence races |
| [`CONVERSATION_RETENTION_POLICY`](parameters.md#conversation-lifecycle) | Until manual deletion | Preserves reloadable demo history without inventing expiry |
| [`ATTEMPT_RETENTION_POLICY`](parameters.md#conversation-lifecycle) | Until manual deletion | Retains failed, cancelled, retried, and successful metadata for debugging and evaluation |
| Release-pinning policy | `TBD` | Conversation-lifetime versus attempt-level active-release selection remains unresolved |

## Data Structures

> **Authoring guidance:** Define entities, states, cardinalities, and retention semantics without selecting database tables or URL syntax.

### Conversation

Define stable identity, creation/update timestamps, ordered visitor and assistant content, active-attempt reference, retention state, and release-pinning state if adopted.

### Generation attempt

Define identity, triggering visitor message, selected corpus release, lifecycle state, timing, cancellation request, internal events, failure details, retry lineage, and retained debugging/evaluation metadata.

### Assistant message

Define successful lore-answer or guide-message identity, generating attempt, corpus release association, final content/evidence references, and context eligibility.

### Incomplete output

Define visible streamed text, failed/cancelled terminal state, marker state, replacement linkage, and explicit exclusion from future agent context.

## Behavior

> **Authoring guidance:** Author complete state machines, pseudocode, and decision tables for these concerns.

### Conversation creation and reload

Specify stable identity and URL behavior, server authority, ordering, missing/deleted conversations, and exact reconstruction of visible state after reload.

### Attempt admission and release selection

Specify one-active-attempt enforcement, visitor-message association, active-release availability, the unresolved pinning choice, and explicit release identity passed into the agent.

### Context construction

Specify inclusion of successful prior messages and exclusion of failed/cancelled partial output, superseded visible output, debugging metadata, and unrelated attempts.

### Incremental event handling

Specify accepted internal event order, durable versus transient data, state transitions from admission through terminal outcome, and final assistant-message creation.

### Cancellation

Specify immediate request acceptance, idempotency, best-effort backend propagation, late completion races, and visible terminal state.

### Failure and incomplete output

Specify partial-text retention, visible marking, context exclusion, diagnostic retention, and distinction from an abstention.

### Retry replacement

Specify creation of a new attempt, linkage to the failed/cancelled predecessor, visible replacement semantics, retention of prior metadata, and behavior if retry also fails.

### Retention and deletion

Specify manual deletion scope, referential cleanup, active-attempt handling, corpus-release associations, and owner confirmation requirements.

## Error Handling

> **Authoring guidance:** Define trigger, detection, response, and recovery for each case.

### Concurrent attempt conflict

Cover competing submissions, retry races, cancellation races, and the observable response to the rejected operation.

### Selected release unavailable

Cover deactivation, rollback, missing assets, and a release becoming unavailable between admission and invocation.

### Invalid event sequence

Cover duplicate, late, out-of-order, or terminal-after-terminal agent events.

### Persistence failure

Cover failures before admission, during streaming, at finalization, and during retry replacement without exposing a successful message that was not durably recorded.

### Cancellation propagation failure

Cover best-effort backend failure, late output, timeout, and retained state.

### Manual deletion conflict

Cover active generation, concurrent reload, missing records, and partial referential deletion.

## Implementation Notes

> **Authoring guidance:** Address transaction boundaries, idempotency keys, per-conversation serialization, event ordering, cancellation checkpoints, crash recovery, and reload consistency without choosing an ORM or exposing persistence models as browser contracts. Evaluation invocations bypass this lifecycle and own their own scheduling.

## Test Scenarios

> **Authoring guidance:** During full authoring, create the `TS-LIFE-{NUMBER}` scenario index. Cover creation/reload, one active attempt, successful finalization, abstention as success, cancellation before/after output, late completion, failure with partial output, context exclusion, retry replacement, persistence failure, release rollback races, retention, and manual deletion.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-07-18 | Initial skeleton |
