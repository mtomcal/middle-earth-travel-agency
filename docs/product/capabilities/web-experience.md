# Web experience

> Maturity: Draft intent

## Purpose

The web experience gives invited visitors a quiet, accessible way to ask lore
questions, follow streamed work, stop it, inspect evidence, and distinguish
ordinary answers from guides. It also provides a more restricted surface for
the owner's blinded evaluation review.

## Desired outcomes

- The primary visitor journey is usable without understanding corpus or agent
  internals.
- Streaming communicates progress without treating model text as trusted final
  markup.
- Cancellation, completion, failure, and retry are visibly and accessibly
  distinct.
- Citations, attribution, temporal framing, and inference labels are available
  where visitors need them.
- Keyboard and assistive-technology users can complete the same core journeys.

## Boundaries

This capability owns protected navigation, conversation presentation, browser
submission and cancellation controls, incremental response presentation,
trusted final rendering, guide presentation, accessibility, and blinded-review
interaction.

It does not own conversation truth, response grounding, evidence resolution,
evaluation verdict semantics, or credential storage.

## Durable invariants

- Protected content is unavailable until the visitor supplies the shared demo
  credential.
- A conversation has a stable URL and reloads from server authority.
- Incremental model text is escaped and cannot introduce trusted HTML.
- Completed messages and typed interactive content are rendered by trusted
  application code from validated data.
- The visitor can request cancellation while an attempt is cancellable and sees
  truthful cancelling, incomplete, failed, or completed state.
- Retry is available after a retryable failure or cancellation.
- Guide messages are visually distinguishable inside the conversation and make
  temporal frame, traveler perspective, inference, citations, and sources
  apparent.
- Unknown generated content types fail safely instead of becoming arbitrary
  markup.
- Dynamic status changes are conveyed semantically, without announcing every
  streamed fragment.
- Core controls are keyboard operable, focus changes are deliberate, and error
  messages are associated with the affected controls.
- Evaluation conditions remain concealed during blinded review, and ordinary
  visitors cannot access the review surface.

## Key decisions and rationale

### Favor an HTML-oriented experience

The current direction uses server-rendered HTML, incremental enhancement, and
small browser-owned interaction areas. It matches the stable-document nature of
conversation and review workflows while keeping server authority visible. The
choice and its replacement triggers live in
[ADR 0004](../../adr/0004-use-server-rendered-html-and-progressive-enhancement.md).

### Separate streamed text from trusted final rendering

Streaming makes latency legible, but generative text cannot be trusted as
application markup. Escaped incremental text followed by trusted rendering
preserves both responsiveness and the content boundary.

### Treat accessibility states as product behavior

Completion, failure, cancellation, review submission, and dynamic replacement
change meaning, not just appearance. Their semantic and focus behavior is part
of the user experience rather than optional polish.

## Representative scenarios

- A visitor submits a question, receives escaped incremental text, and then sees
  validated final content replace it without a layout or trust-boundary jump.
- The visitor cancels during streaming; the control responds immediately and
  the final state remains truthful after reload.
- A guide contains an itinerary inference; its distinction from sourced facts
  is understandable without relying on color alone.
- An unknown generated block type arrives; the page presents a safe failure and
  no model-supplied HTML executes.
- The owner reviews an output pair by keyboard without learning the hidden
  retrieval assignment before submitting a verdict.

## Open questions

Visual direction, guide treatment, source-panel placement, focus destinations,
and reviewer authorization remain open. See
[open product questions](../open-questions.md).

