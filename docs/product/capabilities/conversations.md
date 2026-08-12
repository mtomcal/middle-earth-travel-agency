# Conversations

> Maturity: Draft intent

## Purpose

Conversations provide a persistent, reloadable home for visitor questions and
assistant messages while keeping in-progress generation state truthful. They
separate accepted conversation history from partial work produced by failure or
cancellation.

## Desired outcomes

- A visitor can reload and continue a conversation at a stable location.
- Concurrent generation cannot race or corrupt conversation context.
- Cancellation feels immediate without falsely claiming backend work has
  already stopped.
- Failure and retry remain understandable and do not contaminate future answers.
- Every completed answer remains traceable to the corpus release that grounded
  it.

## Boundaries

This capability owns conversation identity, attempt admission, context
eligibility, corpus-release association, streaming attempt state, cancellation,
failure, retry replacement, retention, and deletion.

It invokes lore-response generation but does not define response policy,
browser rendering, citation construction, or corpus operations.

## Durable invariants

- Conversation and attempt state is server-owned and survives page reloads.
- At most one generation attempt is active in a conversation.
- A visitor submission and its attempt are admitted consistently so duplicate
  work cannot create ambiguous history.
- Only completed assistant messages enter future response context.
- Failed or cancelled streamed text remains incomplete output, visibly distinct
  from an assistant message.
- Cancellation is an immediate request with best-effort backend propagation; it
  is not proof that work has already stopped.
- Retry creates a new attempt rather than resuming or rewriting the historical
  attempt.
- A successful assistant message records the exact corpus release used during
  its generation.
- Reloading derives visible state from persisted authority rather than durable
  browser-only state.
- Manual deletion does not silently race an active attempt.

## Key decisions and rationale

### Model attempts explicitly

Streaming, cancellation, provider failure, and retry all create states that a
simple message-only transcript cannot represent truthfully. Attempts preserve
those facts without treating partial model text as accepted conversation.

### Keep incomplete output visible but ineligible

Discarding partial text can be confusing after a visible stream, while treating
it as history can poison later context. A marked incomplete state preserves
visitor understanding without granting it assistant-message authority.

### Make retry a replacement in the visitor experience

The visitor should recover from a failed answer without accumulating confusing
duplicates, while retained attempt metadata can still support debugging and
evaluation.

## Representative scenarios

- A visitor reloads during streaming and sees the server's current attempt
  state rather than a second local generation.
- A second submission arrives while an attempt is active; it is rejected
  without adding ambiguous conversation history.
- Cancellation races with successful finalization; one authoritative terminal
  state wins and remains stable after reload.
- A failed attempt leaves marked incomplete output; a later retry replaces that
  visible slot but does not erase the failed attempt record.
- A later response is constructed from visitor messages and completed assistant
  messages only.

## Open questions

Conversation-lifetime versus attempt-level release selection and the amount of
visitor-visible prior attempt history remain open. See
[open product questions](../open-questions.md).

