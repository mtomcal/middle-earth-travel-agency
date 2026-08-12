# 0002: Use immutable curated corpus releases

> Status: Accepted

## Context

Visitor claims must remain traceable after extraction and curation improve. A
mutable set of approved passages would make an old answer appear to have used
whatever evidence happens to be current later.

The operator also needs to roll back corpus changes without rewriting or
reconstructing historical state.

## Decision

Publish curated lore as immutable corpus releases. Each release has one
authoritative manifest that identifies all included article artifacts and lore
passages. Later source, extraction, rubric, classification, or selection changes
produce a new release.

One valid retained release is selected as active for runtime retrieval. Rollback
uses the same selection mechanism to reactivate an older release.

## Rationale

- Historical answers retain a stable evidence association.
- Release validation is separate from mutable working curation state.
- Activation and rollback become explicit and reversible.
- Search indexes can remain disposable projections instead of content
  authority.

## Consequences

- Supporting artifacts, rubric versions, decisions, and review audit evidence
  must be retained while a release depends on them.
- Existing releases cannot be patched in place, even to reflect improved
  curation.
- Storage grows with retained source and review history, although indexes may be
  rebuilt or removed.
- An active release may temporarily lack a compatible ready index; runtime must
  report that state rather than fall back silently.

## Alternatives considered

- A mutable approved-passage table was rejected because it weakens historical
  traceability and rollback.
- Snapshotting only the current search index was rejected because an index is a
  derived technical representation rather than source authority.
- Automatic cleanup was deferred because the small demo benefits more from
  simple manual retention and rollback.

## Replacement triggers

Reconsider the storage and publication mechanism if retained release volume
becomes operationally significant. Historical immutability and answer
traceability should remain requirements even if their representation changes.

