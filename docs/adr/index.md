# Architecture decision records

Architecture decision records explain consequential technical choices whose
rationale cannot be recovered reliably from code. They do not restate the
implementation.

## Decisions

| ADR | Status | Decision |
|---|---|---|
| [0001](0001-use-a-pinned-wikimedia-source-snapshot.md) | Accepted | Use a pinned Wikimedia source snapshot |
| [0002](0002-use-immutable-curated-corpus-releases.md) | Accepted | Use immutable curated corpus releases |
| [0003](0003-use-sqlite-full-text-search-for-initial-retrieval.md) | Accepted | Use SQLite full-text search for initial retrieval |
| [0004](0004-use-server-rendered-html-and-progressive-enhancement.md) | Proposed | Use server-rendered HTML and progressive enhancement |
| [0005](0005-use-a-single-instance-deployment.md) | Accepted constraint | Use a single-instance deployment |
| [0006](0006-use-a-python-modular-monolith.md) | Accepted | Use a Python modular monolith |

## Status meanings

- **Proposed**: the direction is under review and is not yet implementation
  authority.
- **Accepted**: the decision should guide implementation until superseded.
- **Accepted constraint**: the boundary is accepted while some implementation
  choices inside it remain open.
- **Superseded**: a later ADR replaces the decision; the record remains for
  history.
- **Rejected**: the alternative was considered and deliberately not selected.

## ADR shape

New ADRs should use lowercase kebab-case with a four-digit sequence and contain:

```markdown
# NNNN: Decision title

> Status: Proposed

## Context
## Decision
## Rationale
## Consequences
## Alternatives considered
## Replacement triggers
```

Edit an ADR to clarify its meaning or update its status. When an accepted
decision changes materially, add a new ADR and mark the old one superseded
instead of rewriting history.

