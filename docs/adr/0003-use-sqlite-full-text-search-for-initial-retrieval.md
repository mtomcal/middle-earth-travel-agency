# 0003: Use SQLite full-text search for initial retrieval

> Status: Accepted

## Context

The product needs a retrieval baseline that can expose the value and failure
modes of grounding before introducing embedding providers, score fusion, graph
construction, or additional services. The first corpus contains a small set of
human-curated English prose passages on one application instance.

## Decision

Use SQLite full-text search as the initial retrieval strategy. Index approved
title, heading, and passage text from one immutable corpus release. Keep
tokenizer and ranking configuration with the rebuildable index so behavior can
be reproduced and compared.

Expose retrieval to the lore agent through narrow plain-text search and
immediate-context operations rather than raw SQLite queries.

## Rationale

- Lexical behavior is inspectable and easy to establish as a baseline.
- SQLite fits the existing single-instance persistence boundary.
- No embedding provider, vector service, or retrieval-side model is required.
- Disposable indexes can be rebuilt completely from immutable releases.

## Consequences

- Synonym, paraphrase, and concept-level recall may be weak.
- Query formulation matters and may require multiple searches.
- Ranking changes require explicit configuration and matched evaluation.
- Search failure cannot fall back to model memory or another release.

## Alternatives considered

- Vector search and embeddings were deferred until evaluation demonstrates a
  concrete lexical retrieval failure worth their cost and opacity.
- Hybrid and score-fusion approaches were deferred because they obscure the
  first baseline.
- GraphRAG was deferred until the product has evidence that relationship-heavy
  questions justify graph construction and maintenance.
- Live web search was rejected because it violates the curated corpus boundary.

## Replacement triggers

Reconsider the strategy when controlled cases show that approved evidence is
present but lexical retrieval repeatedly cannot surface it, and a candidate
strategy improves matched human evaluation without weakening provenance or the
agent tool boundary.

