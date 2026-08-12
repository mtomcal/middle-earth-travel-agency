# 0005: Use a single-instance deployment

> Status: Accepted constraint

## Context

Middle-earth Travel Agency is a private, noncommercial fan experiment for a
small invited audience and one operator. Its initial data model favors local
SQLite state, immutable filesystem artifacts, and rebuildable retrieval
indexes. Demand and availability requirements do not yet justify distributed
coordination.

Exact AWS packaging, persistent-volume attachment, reverse proxy, and TLS
termination remain undecided.

## Decision

Target one application instance with instance-attached persistent storage. Do
not build high availability, autoscaling, distributed workers, a managed
database, or a distributed filesystem into the initial demo.

## Rationale

- One operator can understand and recover the complete system.
- SQLite and local immutable artifacts avoid premature service dependencies.
- The deployment remains proportional to the product evidence being sought.
- Backups and restart behavior can be exercised before distributed failure
  semantics are introduced.

## Consequences

- Instance failure causes downtime until recovery.
- Capacity is bounded by one host.
- Persistent storage, backup verification, and restore procedures are critical.
- Background or offline operations must coordinate with the same local state.
- Packaging and proxy choices must preserve streaming and cancellation.

## Alternatives considered

- High availability and autoscaling were rejected as disproportionate to the
  invited-demo audience.
- Managed relational persistence was deferred until concurrency, operational,
  or availability evidence requires it.
- Distributed corpus storage and worker queues were deferred because current
  operations are deliberate offline commands.

## Replacement triggers

Reconsider this constraint when observed traffic exceeds a single instance,
downtime becomes materially harmful, multiple operators require concurrent
work, or recovery objectives cannot be met with verified backup and restore.
