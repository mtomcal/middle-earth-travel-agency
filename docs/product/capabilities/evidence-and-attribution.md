# Evidence and attribution

> Maturity: Draft intent

## Purpose

Evidence and attribution turn validated claim-to-passage bindings into
understandable citations and conservative Wikimedia license treatment. They
help a visitor inspect why a claim was made while preserving the separate legal
purpose of attribution.

## Desired outcomes

- A visitor can connect a factual claim to supporting passage context and an
  exact source revision.
- Citation presentation does not imply support that the response did not bind.
- Wikipedia contributor and license treatment remains visible and accurate.
- Internal provenance detail does not overwhelm or leak into the visitor
  experience.

## Boundaries

This capability resolves existing evidence identities, validates bindings, and
constructs citations, guide source lists, and attribution notices.

It does not retrieve evidence, decide claim boundaries, invent claim support,
render arbitrary model HTML, or determine final page layout.

## Durable invariants

- Every citation resolves to material included in the response's immutable
  corpus release and to its exact Wikipedia revision.
- A citation is associated with a specific grounded claim; a general source
  list is not a substitute.
- A guide also provides a consolidated source list without implying that every
  source supports every statement.
- An abstention or claim-free conversational response does not need fabricated
  citations.
- Attribution identifies Wikipedia contributors, the applicable exact revision
  and license, and modifications made by Halls of Knowledge.
- Citation and attribution remain distinct even when presented in the same
  interface region.
- Missing, stale, or mismatched evidence fails safely rather than producing a
  misleading link.
- The initial product presents text only; unsupported third-party media and its
  separate rights do not enter the response surface.

## Key decisions and rationale

### Resolve presentation outside the agent

The agent supplies semantic claim bindings, while trusted application code
resolves source identity and creates links and notices. This keeps URLs, license
language, and trusted markup outside generative output.

### Preserve exact revision context

Linking a moving article page would weaken traceability and could show content
different from the material that supported the answer. Citations therefore
retain exact revision context, with article history available for contributor
attribution.

### Use conservative attribution

The private demo keeps citations and attribution explicit pending legal review.
This is risk containment, not a final legal conclusion for public or commercial
release.

## Representative scenarios

- A grounded claim references a valid passage; the visitor can reach the exact
  supporting revision and understand the article and section context.
- A binding references a passage outside the response's release; final
  presentation fails rather than silently linking a different source.
- Two claims use different passages from the same revision; both remain
  claim-linked while the guide source list consolidates the revision.
- A response contains only an abstention; it presents the abstention and
  attribution treatment appropriate to any quoted or transformed material
  without inventing evidentiary citations.

## Open questions

Minimum claim granularity, source-panel placement, persistent versus collapsed
attribution, and the broader legal boundary remain open. See
[open product questions](../open-questions.md).

