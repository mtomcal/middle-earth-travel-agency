# Design Language

> **Version**: 0.2.0
> **Last Updated**: 2026-07-18
> **Purpose**: Shared UI/UX and operator-interface vocabulary for Halls of Knowledge; this preamble does not establish a finished visual system.

---

## Surface boundaries

The initial product has three user-facing surfaces:

1. the invited visitor’s protected web experience;
2. the owner-only blinded evaluation interface; and
3. the operator’s offline corpus command-line interface.

There is no initial public JSON API, WebSocket interface, native application, public account-management surface, or LOTRO-facing surface.

## Interface vocabulary

### Visitor web experience

| Element | Definition | When to use | When NOT to use |
|---------|------------|-------------|-----------------|
| **Password gate** | The entry surface that requests the shared demo credential before protected content is available. | Before an unauthenticated visitor enters the demo | As a public account registration or identity-management surface |
| **Conversation view** | The stable-URL page presenting one server-owned conversation and its visitor and assistant history. | For asking, reloading, and continuing lore conversations | As transient client-only chat state |
| **Message composer** | The visitor control for submitting the next message to the active conversation. | When no generation attempt prevents a new submission | As an arbitrary agent command console |
| **Streaming response region** | The live region in which escaped incremental text for the active attempt appears before trusted final HTML replaces it. | While one generation attempt is active | For inserting arbitrary agent-provided HTML |
| **Cancellation control** | The immediately available control that asks the server and backend work to stop the active generation attempt. | Only while an attempt can still be cancelled | As deletion of retained conversation or attempt records |
| **Incomplete-output marker** | The persistent visible state identifying text left by a failed or cancelled attempt as incomplete. | Whenever incomplete output remains visible | On a successfully finalized assistant message |
| **Retry control** | The action that starts a new attempt to replace failed or cancelled visible output. | After retryable failure or cancellation | To resume the same attempt or erase retained attempt metadata |
| **Guide presentation** | The distinct chat presentation for a guide message’s temporal frame, traveler perspective, structured content, inferences, citations, and sources. | After explicit guide request or confirmation | As a separate stable-URL guide artifact |
| **Citation marker** | The user-visible connection between a grounded claim and exact supporting revision context. | Adjacent to or clearly associated with its grounded claim | As a replacement for the attribution notice |
| **Source and attribution panel** | The presentation region containing consolidated sources when required and the persistent contributor, modification, and license treatment. | With guide sources and wherever the attribution contract requires | As evidence that every listed source supports every claim |
| **Completion announcement** | The assistive-technology notification that an active response has finalized, failed, or been cancelled. | At the terminal state of a streamed attempt | For announcing every streamed token or fragment |

### Evaluation interface

| Element | Definition | When to use | When NOT to use |
|---------|------------|-------------|-----------------|
| **Blinded output pair** | The randomized left/right presentation of two ablation outputs without condition labels. | During owner review of one evaluation case | When revealing the retrieval condition before verdict submission |
| **Verdict control** | The mutually exclusive choice among left better, tie, right better, and both fail. | Once the reviewer can compare both outputs | As a numeric score or automated judgment |
| **Review notes** | Optional owner-authored explanation attached to one evaluation verdict. | When rationale will aid later analysis | As required justification for every verdict |
| **Review tags** | Optional structured labels attached to an evaluation review. | For consistent later filtering of observed qualities or failures | As a substitute for the verdict |

### Operator CLI

| Element | Definition | When to use | When NOT to use |
|---------|------------|-------------|-----------------|
| **Offline corpus command** | A package-owned operator command that performs corpus acquisition, extraction, curation support, indexing, validation, activation, or rollback outside web requests. | For deliberate corpus lifecycle operations | During an HTTP request or as an agent-exposed tool |
| **Command result** | The deterministic operator-facing summary of an offline command’s outcome, affected release or artifact identities, and recoverable errors. | At command completion or failure | As user-facing lore provenance |
| **Curation cockpit** | The single-key terminal review surface that shows one passage and only its mission-critical progress, location, target scope, and classification state. | During rapid passage classification | As a dense dashboard of every available datum and command |
| **Expanded instruments** | The optional curation-cockpit panel containing neighboring context, raw wikitext, decision hierarchy, source identifiers, and bulk-scope controls. | When the operator asks for evidence or less-common controls | In the default rapid-review frame |
| **End-of-pass summary** | The visually distinct terminal state reporting classification totals and unresolved passages after the operator reaches the final passage. | At the end of every review pass | As a replacement for durable release validation |
| **Undo-and-return control** | The single-key action that reverses the latest curation decision and returns focus to its passage for immediate reclassification. | Immediately after a mistaken rapid classification | As rollback of a corpus release |

## Interaction-state vocabulary

| State | Meaning | Required distinction |
|-------|---------|----------------------|
| **Idle** | The conversation has no active generation attempt. | Does not mean the conversation is empty or deleted |
| **Submitting** | The visitor’s message has been sent but streaming has not yet begun. | Must remain distinguishable from an unsubmitted composer |
| **Streaming** | Incremental escaped response text is arriving for the active attempt. | Is not a finalized assistant message |
| **Cancelling** | Cancellation has been requested while backend termination remains best-effort. | Must not imply backend work has already stopped |
| **Complete** | Trusted final assistant-message HTML has replaced incremental text. | Only successful output may enter future agent context |
| **Incomplete** | Failure or cancellation left marked visible output that is excluded from future context. | Must remain distinguishable until retry replaces it |

## Interaction principles

- **Server authority** — conversation, attempt, release-association, and review state originate on the server rather than in durable browser-only state.
- **HTML-oriented contracts** — ordinary browser interactions exchange trusted application-rendered HTML rather than exposing a speculative public JSON API.
- **Progressive enhancement** — server-rendered semantics remain primary; HTMX and interactive islands add narrowly scoped behavior.
- **Trusted final rendering** — incremental agent text is escaped, while final HTML and generative UI blocks are produced by trusted application renderers.
- **Immediate control feedback** — cancellation, failure, completion, retry, and verdict actions expose visible and assistive state changes.
- **Keyboard and focus continuity** — interactive controls remain keyboard-operable and focus moves intentionally after swaps, completion, cancellation, and validation errors.
- **Operator progressive disclosure** — the curation cockpit shows only information needed for the current classification; context, raw source, provenance, hierarchy, and bulk controls appear on explicit request.
- **Reversible review momentum** — a classification key saves and advances without Enter, while one undo action reverses the decision and restores the reviewed passage.
- **Terminal-state distinction** — the end-of-pass summary MUST be visually and textually distinguishable from an ordinary passage-review frame and MUST NOT rely on color alone.

## Visual tokens

No color, spacing, typography, motion, iconography, or breakpoint tokens are approved yet. Implementers and spec authors MUST NOT infer a Tolkien-themed visual system, reproduce Wikipedia trade dress, or use Wikimedia marks from the product premise alone.

## Naming conventions

| Context | Convention | Example |
|---------|------------|---------|
| Visitor-facing corpus references | Use article titles and revision context, never internal file paths | “Gandalf, Wikipedia revision …” |
| Attempt state | Name the observable lifecycle state rather than a vague loading state | “Cancelling” rather than “Please wait” |
| Guide synthesis | Label unsupported direct-source synthesis as inference | “Itinerary inference” |
| Evaluation conditions | Hide condition names until blinded review no longer depends on concealment | “Left” and “Right” during review |
| Wikimedia attribution | Use plain textual attribution without endorsement or trade-dress implications | “Source: Wikipedia” within the full notice |
| Operator review controls | Use stable single-key classifications and explicit action labels | “1 Lore”, “U Undo + return”, “M More” |

## Flagged design ambiguities

- Exact source-panel placement and whether it remains expanded, collapsed, or globally persistent are unresolved.
- The distinct visual treatment and internal layout of a guide presentation are unresolved.
- Retry replacement does not yet establish whether prior attempt history is visitor-visible.
- The precise focus destination after completion, cancellation, retry, and HTMX swaps is unresolved.
- The authorization experience distinguishing invited visitors from evaluation reviewers is unresolved.
- No visual token values or brand direction are approved.
