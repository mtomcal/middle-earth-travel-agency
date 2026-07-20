# Web Experience

> **Spec Version**: 0.1.0
> **Last Updated**: 2026-07-18
> **Depends On**: [Conversation and Attempt Lifecycle](conversation-and-attempt-lifecycle.md), [Evidence Presentation and Attribution](evidence-presentation-and-attribution.md), [Evaluation and Review](evaluation-and-review.md)
> **Depended By**: None

---

## Overview

> **Authoring guidance:** Define the HTML-oriented visitor and owner-review browser experience. This system owns server-rendered presentation, HTMX interactions, HTML-oriented SSE framing, browser cancellation initiation, escaped incremental text, trusted final rendering, baseline accessibility, and the generative-UI block catalog; it does not own conversation truth, claim support, attribution construction, or evaluation verdict semantics.

## Dependencies

### Technology dependencies

| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | To be pinned | Protected HTML endpoints and streaming transport |
| Jinja | To be pinned | Trusted server-rendered HTML and final response fragments |
| HTMX | To be pinned | Ordinary HTML-driven interactions and DOM swaps |
| Native Web Components | Web-platform baseline to be pinned | Narrow streaming and other stateful interactive islands |
| Server-Sent Events over streaming `POST` | Browser/server contract to be authored | HTML-oriented incremental framing without WebSockets |

### Spec dependencies

- [Conversation and Attempt Lifecycle](conversation-and-attempt-lifecycle.md) — supplies authoritative conversation, attempt, cancellation, retry, and terminal states.
- [Evidence Presentation and Attribution](evidence-presentation-and-attribution.md) — supplies presentation-ready citations, source lists, and attribution notices.
- [Evaluation and Review](evaluation-and-review.md) — supplies blinded pair, verdict, note, and tag behavior for the owner review surface.

## Parameters

> **Authoring guidance:** Define reconnect policy if any, buffering limits, announcement timing, DOM size limits, and responsive thresholds in [parameters.md](parameters.md) with rationale.

| Parameter | Authoritative value | Rationale |
|-----------|---------------------|-----------|
| [`ATTRIBUTION_PANEL_PLACEMENT`](parameters.md#unresolved-selections) | `TBD` | Requires UI and legal review rather than inferred placement |
| Stream framing detail | `TBD` | Must preserve incremental escaping, terminal-state detection, and trusted final replacement |
| Visual tokens | `TBD` | No visual direction is approved in [DESIGN_LANGUAGE.md](DESIGN_LANGUAGE.md) |

## Data Structures

> **Authoring guidance:** Define browser-facing HTML states and typed rendering inputs without creating a speculative public JSON API.

### Conversation page state

Define conversation identity, ordered visible messages, active-attempt controls, incomplete-output state, and reload behavior.

### Stream frame

Define HTML-oriented frame types for incremental escaped text, status changes, trusted final replacement, failure, and cancellation without exposing internal agent events directly.

### Guide presentation model

Define temporal frame, traveler perspective, structured sections, itinerary-inference labels, citations, source list, and attribution regions.

### Generative UI block catalog

Define allowlisted block identity, typed data contract, trusted renderer ownership, accessibility requirements, and unknown-type rejection.

### Blinded review page state

Define case context, randomized left/right outputs, hidden condition identities, verdict controls, notes, tags, and submission state.

## Behavior

> **Authoring guidance:** Author complete browser contracts, progressive-enhancement rules, state tables, and accessibility behavior for these concerns.

### Protected page navigation

Specify password-gate routing, stable conversation URLs, reload, missing/deleted resources, reviewer surface restriction, and return destinations without defining credential storage here.

### Message submission and streaming

Specify the light-DOM chat island’s streaming `POST`, HTML-oriented SSE handling, incremental escaping, duplicate-submission prevention, and terminal transition.

### Trusted final replacement

Specify replacement of incremental text with application-rendered final HTML, failure behavior, content trust boundary, and prohibition on arbitrary agent HTML.

### Cancellation and retry interaction

Specify immediate browser cancellation with `AbortController`, server request propagation, visible cancelling/incomplete states, retry availability, focus, and race handling.

### Guide presentation

Specify distinct but in-conversation rendering, confirmation interaction, temporal/traveler prominence, inference labels, claims, citations, and source/attribution treatment.

### Generative UI blocks

Specify catalog ownership, allowlist validation, trusted rendering, unknown-type rejection, lifecycle behavior under HTMX swaps, and accessibility.

### Blinded evaluation review

Specify random left/right presentation, condition concealment, verdict interaction, optional notes/tags, validation, submission confirmation, and keyboard behavior.

### Accessibility baseline

Specify semantic HTML, labels, keyboard operation, focus management, status and completion announcements, error association, and reduced-motion behavior if motion is introduced.

### Migration triggers

Specify the confirmed conditions that require reevaluating the server-rendered architecture, including sustained cross-surface state, predominantly bespoke components, deeply editable generative UI, offline/optimistic behavior, non-HTML clients, independent deployment/team needs, or recurring DOM-swap friction.

## Error Handling

> **Authoring guidance:** Define trigger, detection, response, and recovery for each case.

### Stream interruption

Cover network loss, malformed frames, server failure, reload during streaming, and distinction between reconnectable transport and a terminal failed attempt.

### Cancellation race

Cover final output arriving during cancellation, duplicate cancellation, browser abort before server receipt, and preserved authoritative state after reload.

### Trusted-render failure

Cover invalid evidence presentation, template failure, unknown block type, and safe fallback without arbitrary HTML.

### HTMX or component lifecycle failure

Cover detached components, repeated initialization, stale listeners, focus loss, and recovery through server navigation.

### Review submission failure

Cover missing verdict, expired or already-reviewed pair, persistence error, duplicate submission, and preservation of reviewer input.

### Accessibility-state failure

Cover missing labels, silent terminal transitions, trapped focus, and inaccessible dynamic content as release-blocking defects.

## Implementation Notes

> **Authoring guidance:** Address progressive enhancement, light-DOM ownership, browser lifecycle cleanup, safe escaping, trusted renderer boundaries, CSP compatibility, SSE proxy buffering, and real-server testability. Do not introduce WebSockets or a public JSON API without a reviewed specification change.

## Test Scenarios

> **Authoring guidance:** During full authoring, create the `TS-WEB-{NUMBER}` scenario index. Cover stable URLs, reload, streaming escape, trusted final replacement, cancel and retry races, incomplete markers, guide confirmation/presentation, citations/attribution, unknown blocks, keyboard use, focus, announcements, blinded review, duplicate submission, and real-server browser journeys.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-07-18 | Initial skeleton |
