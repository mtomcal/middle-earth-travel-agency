# 0004: Use server-rendered HTML and progressive enhancement

> Status: Proposed

## Context

The planned web product consists primarily of protected documents with stable
URLs: travel consultations, guide revisions, sources, and blinded review forms.
Server state is authoritative, while streaming, cancellation, and a small
catalog of typed generated content require focused browser lifecycle behavior.

The traveler experience has not yet been fully authored or implemented, so this
decision remains proposed.

## Decision

Use FastAPI and Jinja for server-rendered HTML, HTMX for ordinary incremental
interactions, HTML-oriented server-sent events for response streaming, and
native Web Components only for narrow interaction areas that need browser-owned
state or lifecycle control.

Do not introduce a speculative public JSON API, WebSockets, or a single-page
application for the initial demo.

## Rationale

- Stable consultation, guide, and review documents fit server rendering naturally.
- Server authority remains visible and reload behavior is straightforward.
- HTMX covers ordinary form and fragment workflows without creating a second
  client-side domain model.
- Narrow components can own cancellation and generated interaction without
  forcing the whole product into a frontend application architecture.
- Server-sent events match one-way response streaming.

## Consequences

- Component initialization, cleanup, focus, and HTMX swaps need careful browser
  tests.
- Stream proxies must avoid buffering and preserve cancellation behavior.
- Incremental model text must remain escaped until trusted application rendering
  replaces it.
- Non-HTML clients have no promised public interface.

## Alternatives considered

- A client-rendered SPA was deferred because the initial surfaces do not yet
  justify duplicated state and routing authority.
- WebSockets were deferred because the core stream is server-to-client and
  cancellation can use an ordinary request.
- Pure server rendering without focused browser components was considered too
  limited for reliable cancellation and richer typed response interactions.

## Replacement triggers

Reconsider this decision if the product develops sustained cross-surface client
state, predominantly bespoke interactive components, deeply editable generated
content, offline or optimistic workflows, required non-HTML clients,
independent frontend deployment, or recurring DOM-swap lifecycle failures.
