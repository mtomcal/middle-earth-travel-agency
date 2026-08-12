# Travel consultations

> Maturity: Draft intent

## Purpose

Travel consultations provide a persistent, reloadable workspace for traveler
intent, agency messages, trip-brief development, and guide generation while
keeping in-progress state truthful. They separate accepted planning context
from partial work produced by failure or cancellation.

## Desired outcomes

- A traveler can reload and continue a consultation at a stable location.
- The accepted trip brief and current guide remain apparent.
- Concurrent generation cannot race or corrupt consultation context.
- Cancellation feels immediate without falsely claiming backend work has
  already stopped.
- Failure and retry remain understandable and do not contaminate later work.
- Every completed message and guide revision remains traceable to its corpus
  release.

## Boundaries

This capability owns consultation identity, attempt admission, accepted
context, trip-brief state changes, corpus-release association, streaming
attempt state, cancellation, failure, retry replacement, retention, and
deletion.

It invokes travel planning and guide generation but does not define their
policies, guide artifact structure, browser rendering, citation construction,
or corpus operations.

## Durable invariants

- Consultation and attempt state is server-owned and survives page reloads.
- At most one generation attempt is active in a consultation.
- A traveler submission and its attempt are admitted consistently so duplicate
  work cannot create ambiguous history.
- Only completed agency messages, accepted trip-brief changes, and completed
  guide revisions enter future context.
- Failed or cancelled streamed text remains incomplete output, visibly
  distinct from accepted consultation history.
- Cancellation is an immediate request with best-effort backend propagation;
  it is not proof that work has already stopped.
- Retry creates a new attempt rather than resuming or rewriting the historical
  attempt.
- A successful agency message or guide revision records the exact corpus
  release used during generation.
- A consultation may contain multiple guide revisions and identifies at most
  one completed revision as current.
- Reloading derives visible state from persisted authority rather than durable
  browser-only state.
- Manual deletion does not silently race an active attempt or remove retained
  evidence still used by a guide revision.

## Key decisions and rationale

### Model attempts explicitly

Streaming, cancellation, provider failure, and retry all create states that a
message-only transcript cannot represent truthfully. Attempts preserve those
facts without treating partial model text as accepted planning context.

### Keep incomplete output visible but ineligible

Discarding partial text can be confusing after a visible stream, while treating
it as history can poison later planning. A marked incomplete state preserves
traveler understanding without granting it authority.

### Treat the trip brief as accepted consultation state

The guide should not depend on a fresh, implicit interpretation of the whole
transcript. Explicit brief changes keep traveler intent reviewable and provide
stable input to guide revisions.

### Make retry a replacement in the traveler experience

The traveler should recover from a failed response without accumulating
confusing duplicates, while retained attempt metadata can still support
debugging and evaluation.

## Representative scenarios

- A traveler reloads during streaming and sees the server's current attempt
  state rather than starting a second generation.
- A second submission arrives while an attempt is active; it is rejected
  without adding ambiguous consultation history.
- Cancellation races with successful finalization; one authoritative terminal
  state wins and remains stable after reload.
- A failed guide attempt leaves marked incomplete output; the current completed
  guide remains unchanged.
- A later attempt is constructed from traveler messages, completed agency
  messages, the accepted trip brief, and eligible guide revisions only.

## Open questions

Consultation-lifetime versus attempt-level release selection, trip-brief update
semantics, and the amount of traveler-visible prior attempt history remain
open. See [open product questions](../open-questions.md).
