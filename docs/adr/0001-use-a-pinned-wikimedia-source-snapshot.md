# 0001: Use a pinned Wikimedia source snapshot

> Status: Accepted

## Context

The product needs an inspectable evidence base whose contents and revision
identity do not change between extraction, curation, evaluation, and traveler
answers. Live Wikipedia requests and `/latest/` dump URLs would make the source
move during that chain.

The initial operator and corpus are small enough to favor a simple, complete
offline scan over distributed acquisition machinery.

## Decision

Use the dated English Wikipedia `20260701` full non-multistream article dump as
the initial source snapshot. Process it offline and treat the revision contained
in that snapshot as authority for acquired artifacts.

Live Wikimedia APIs may discover candidates but do not supply answer evidence
or replace the pinned revision.

## Rationale

- Fixed revisions make displayed claims reproducible and attributable.
- One sequential source is easier for a single operator to inspect and recover.
- Offline acquisition keeps live network state outside traveler requests and
  agent tools.
- A full dump avoids early complexity around multistream ranges and per-page
  consistency.

## Consequences

- Initial acquisition is storage- and time-intensive.
- The corpus is intentionally stale relative to live Wikipedia.
- Source upgrades require a new acquisition and new immutable artifacts.
- Candidate discovery may observe titles or revisions that differ from the
  pinned snapshot and must defer to dump authority.
- The full dump may be deleted after successful artifact validation because raw
  wikitext and exact revision identity remain in article artifacts.

## Alternatives considered

- Live per-page API fetches were rejected because they weaken snapshot
  consistency and reproducibility.
- The moving `/latest/` dump was rejected because it is not stable provenance.
- Multistream range extraction was deferred because its operational complexity
  is unnecessary for the first candidate pool.
- Permanent archival of complete XML and published checksums was not selected;
  the demo retains the smaller provenance chain it actually needs.

## Replacement triggers

Reconsider this decision when corpus refresh frequency, corpus size, download
cost, or multiple source authorities make a full sequential snapshot materially
impractical.
