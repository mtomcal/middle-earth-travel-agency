# Web experience

> Maturity: Draft intent

## Purpose

The web experience gives invited travelers a quiet, accessible workspace in
which to develop a trip brief with the agency and read, inspect, and revise the
resulting travel guide. It also provides a more restricted surface for the
owner's blinded evaluation review.

## Desired outcomes

- The journey from initial idea to generated guide is usable without
  understanding corpus or agent internals.
- Consultation, accepted trip brief, and current guide have distinct roles
  without feeling like unrelated applications.
- Streaming communicates progress without treating model text as trusted final
  markup.
- Cancellation, completion, failure, retry, and guide revision are visibly and
  accessibly distinct.
- Temporal framing, traveler perspective, inference, citations, sources, and
  attribution are available where they matter.
- Keyboard and assistive-technology users can complete the same core journeys.

## Boundaries

This capability owns protected navigation, consultation and trip-brief
presentation, browser submission and cancellation controls, incremental
response presentation, trusted guide rendering, revision navigation,
accessibility, and blinded-review interaction.

It does not own consultation truth, planning policy, guide structure, evidence
resolution, evaluation verdict semantics, or credential storage.

## Durable invariants

- Protected content is unavailable until the traveler supplies the shared demo
  credential.
- A consultation has a stable URL and reloads from server authority.
- The accepted trip brief and current completed guide revision are
  distinguishable from exploratory conversation and partial generation.
- Incremental model text is escaped and cannot introduce trusted HTML.
- Completed messages, guides, and typed interactive content are rendered by
  trusted application code from validated data.
- The traveler can request cancellation while an attempt is cancellable and
  sees truthful cancelling, incomplete, failed, or completed state.
- Retry is available after a retryable failure or cancellation.
- Every guide makes its temporal frame and traveler perspective apparent.
- The distinction between in-world guidance, travel inference, uncertainty,
  citations, sources, and attribution does not rely on color alone.
- Guide revision controls cannot imply that an earlier revision was rewritten
  or deleted.
- Unknown generated content types fail safely instead of becoming arbitrary
  markup.
- Dynamic status changes are conveyed semantically, without announcing every
  streamed fragment.
- Core controls are keyboard operable, focus changes are deliberate, and error
  messages are associated with the affected controls.
- Evaluation conditions remain concealed during blinded review, and ordinary
  travelers cannot access the review surface.

## Key decisions and rationale

### Center the artifact without hiding the consultation

The guide is the product, but the consultation explains how traveler choices
and agency research shaped it. The interface should make the current guide
prominent while keeping the brief and relevant conversation available for
revision.

### Favor an HTML-oriented experience

The current direction uses server-rendered HTML, incremental enhancement, and
small browser-owned interaction areas. It matches the stable-document nature
of consultation, guide, and review workflows while keeping server authority
visible. The choice and its replacement triggers live in
[ADR 0004](../../adr/0004-use-server-rendered-html-and-progressive-enhancement.md).

### Separate streamed text from trusted final rendering

Streaming makes latency legible, but generative text cannot be trusted as
application markup. Escaped incremental text followed by trusted rendering
preserves both responsiveness and the content boundary.

### Treat accessibility states as product behavior

Completion, failure, cancellation, guide creation, revision selection, and
dynamic replacement change meaning, not just appearance. Their semantic and
focus behavior is part of the experience rather than optional polish.

## Representative scenarios

- A traveler begins with a vague request, sees the trip brief become ready, and
  deliberately asks the agency to generate the first guide.
- The traveler receives escaped incremental text and then sees a validated
  guide artifact replace it without a layout or trust-boundary jump.
- The traveler cancels a guide revision; the previous current guide remains
  prominent and the cancelled work is marked incomplete.
- A guide contains a travel inference; its distinction from sourced facts is
  understandable without relying on color alone.
- An unknown generated block type arrives; the page presents a safe failure and
  no model-supplied HTML executes.
- The owner reviews an output pair by keyboard without learning the hidden
  retrieval assignment before submitting a verdict.

## Open questions

Consultation, brief, and guide layout; source-panel placement; revision
navigation; focus destinations; export; and reviewer authorization remain
open. See [open product questions](../open-questions.md).
