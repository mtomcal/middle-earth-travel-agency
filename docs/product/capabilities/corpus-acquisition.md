# Corpus acquisition

> Maturity: Established intent

## Purpose

Corpus acquisition turns a fixed Wikimedia source snapshot into inspectable,
immutable article artifacts and conservative prose passages. It provides the
source identity and extraction evidence needed for later human curation without
allowing live Wikipedia or category membership to become answer authority.

## Desired outcomes

- The operator can reproduce which source revision and extraction policy
  produced a passage.
- Extraction failures are visible instead of being normalized into plausible
  prose.
- A defect in one candidate does not erase valid results from unrelated
  candidates.
- Human sampling catches structural extraction problems before material enters
  curation.

## Boundaries

This capability owns candidate discovery, source selection, redirect
resolution, revision selection, conservative prose extraction, immutable
article artifacts, extraction review, and acquisition acceptance.

It does not decide whether prose is Tolkien lore, publish corpus releases, build
search indexes, or expose material to the lore agent.

## Durable invariants

- Discovery is advisory. Category membership, API results, and nomination do
  not approve an article.
- The initial source is namespace-zero English Wikipedia from the dated
  `20260701` dump, never the moving `/latest/` endpoint.
- The revision serialized in the source snapshot is authoritative even when a
  live API reports newer content.
- One article artifact represents one source revision and one complete
  behavior-affecting extraction configuration and never changes in place.
- Raw wikitext and exact page/revision identity remain available after the full
  dump is deleted.
- Only prose paragraphs are eligible for the initial extracted-passage set.
  Tables, lists, quotations, references, administrative sections, media, and
  meaning-dependent unresolved markup are excluded conservatively.
- Passage identity distinguishes identical text at different structural
  locations.
- Identical source and extraction inputs produce equivalent passages and stable
  identities; changed extraction behavior produces new artifacts.
- A complete source scan is required before successful artifacts are published,
  while a failure in one candidate does not stop unrelated candidates.
- Acquisition acceptance requires automated checks, an approved canonical
  target preview, deterministic sampled human review, and an auditable final
  operator decision.
- Acquisition and review are offline operator activities, never web-request or
  agent-tool behavior.

## Key decisions and rationale

### Use a fixed full Wikimedia dump

The first acquisition favors one understandable sequential source over live
page fetches or multistream range handling. This makes revision authority and
reproduction easier to reason about for a one-operator experiment. See
[ADR 0001](../../adr/0001-use-a-pinned-wikimedia-source-snapshot.md).

### Preserve lightweight provenance

Exact source, revision, raw text, extraction configuration, and structural
coordinates are retained. Whole-file checksums, permanent dump retention, full
XML records, and source byte offsets are not product requirements. This keeps
the evidence chain useful without turning the demo into an archival system.

### Review extraction separately from curation

An extraction finding answers whether the pipeline preserved or excluded the
source correctly. It does not answer whether a passage is eligible lore. Keeping
these judgments separate avoids using semantic classification to hide an
extraction defect.

### Keep the candidate pool practical

The first corrected acquisition aims for roughly 60 to 80 unique canonical
articles so the operator can produce a useful 25 to 50 article release while
retaining room to reject weak candidates. These are planning targets, not
validity thresholds.

## Representative scenarios

- A proposed alias resolves through redirects to one namespace-zero article;
  the final article is materialized once and the redirect chain remains
  inspectable.
- A paragraph contains meaning-dependent markup; that paragraph is excluded
  while unaffected prose from the article remains available.
- A source scan is truncated; no apparently successful artifact set is
  published from the incomplete document.
- The same revision is processed after extraction behavior changes; the new
  result receives a distinct artifact identity and the old result remains
  unchanged.
- A sampled passage is flagged during extraction review; the acquisition cannot
  be accepted until the defect is corrected and reviewed.

## Open questions

The response to a late extraction defect in an already accepted acquisition is
not yet settled. See [open product questions](../open-questions.md).

