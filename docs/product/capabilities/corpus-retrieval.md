# Corpus retrieval

> Maturity: Established intent

## Purpose

Corpus retrieval gives the lore agent a narrow way to find approved evidence
without exposing corpus administration, arbitrary storage access, or a choice
among releases. It establishes a transparent baseline against which more
complex retrieval can be evaluated.

## Desired outcomes

- The agent can find relevant approved prose and immediate local context.
- Retrieval results remain traceable to one immutable corpus release.
- Index failures are visible and cannot silently change the corpus being used.
- The value of retrieval can be tested under a genuinely disabled condition.

## Boundaries

This capability owns rebuildable search projections, active-release resolution,
plain-text search, immediate surrounding context, and the controlled
retrieval-disabled condition.

It does not curate content, select the active release, write an answer, decide
whether a result supports a claim, or construct visitor-facing citations.

## Durable invariants

- A retrieval index is disposable and completely derivable from one immutable
  corpus release.
- Runtime calls resolve the sole active corpus release internally. The caller
  and agent cannot select, enumerate, or override releases.
- Search returns every and only passages admitted to the indexed release as
  internal lore.
- Results expose approved passage text and stable evidence identity, not raw
  wikitext, internal paths, curation history, or license presentation.
- Agent query input is plain text and cannot alter fields, filters, ranking
  configuration, release scope, or result limits.
- Immediate context never crosses an article or section and never skips excluded
  material to manufacture continuity.
- An unavailable or incompatible index is an explicit failure. Runtime
  retrieval cannot fall back to a prior release, repair the index, or interpret
  failure as empty evidence.
- A retrieval call admitted against one release completes against that release
  even if the operator activates another release concurrently.
- The disabled evaluation condition returns no evidence and cannot be bypassed
  through the surrounding-context operation.

## Key decisions and rationale

### Begin with lexical retrieval

SQLite full-text search is the initial transparent, dependency-light baseline.
It is intentionally not a claim that lexical search is the final best strategy.
Tokenizer, weights, and exact ranking implementation belong to code and
rebuildable index metadata. See
[ADR 0003](../../adr/0003-use-sqlite-full-text-search-for-initial-retrieval.md).

### Expose two narrow agent operations

The agent may search approved passages and request immediate context for a
passage it found. Keeping release selection and provenance inspection outside
the tool surface limits accidental authority and prompt-driven control.

### Do not force artificial source diversity

Ranking should reflect the configured lexical evidence rather than imposing a
per-article quota. Whether a result actually supports a response claim remains
the response capability's responsibility.

## Representative scenarios

- A plain query matches title, section, and passage text; the system returns a
  deterministic bounded result set from the active release.
- The active release has no compatible ready index; the call reports index
  unavailability rather than searching an older release.
- The agent requests context around a passage next to an excluded paragraph;
  the system does not jump over the exclusion to return a more distant passage.
- Retrieval is disabled for evaluation; search and context both return no
  evidence without revealing the disabled condition to the agent.
- Activation changes while a call is running; that call remains internally
  consistent and the next call resolves the newly active release.

## Open questions

The lexical baseline should be replaced or supplemented only when evaluation
shows a specific failure that a more complex strategy can address.

