# Private Demo Access and Operations

> **Spec Version**: 0.1.0
> **Last Updated**: 2026-07-18
> **Depends On**: [Corpus Acquisition and Provenance](corpus-acquisition-and-provenance.md), [Corpus Curation and Releases](corpus-curation-and-releases.md), [Conversation and Attempt Lifecycle](conversation-and-attempt-lifecycle.md), [Web Experience](web-experience.md), [Evaluation and Review](evaluation-and-review.md)
> **Depended By**: None; this system provides orthogonal operational support

---

## Overview

> **Authoring guidance:** Define the private single-instance demo’s access and operational boundary: shared visitor credential, restricted evaluation-review access, secret handling, persistent local storage, deployment, startup/recovery, manual deletion, and execution of package-owned offline corpus commands. Keep corpus command semantics in their owning corpus specs and keep public accounts, high availability, and distributed infrastructure out of scope.

## Dependencies

### Technology dependencies

| Technology | Version | Purpose |
|------------|---------|---------|
| AWS single-instance compute | Packaging `TBD` | Private application hosting without high-availability requirements |
| SQLite | Runtime-compatible version to be pinned | Instance-local durable application records |
| Persistent local storage | AWS storage choice `TBD` | Corpus artifacts, indexes, SQLite data, and rollback assets across restarts |
| Reverse proxy and TLS termination | `TBD` | Protected HTTPS access and streaming behavior when required by final packaging |

### Spec dependencies

- [Corpus Acquisition and Provenance](corpus-acquisition-and-provenance.md) — defines offline acquisition/extraction command semantics and source artifacts.
- [Corpus Curation and Releases](corpus-curation-and-releases.md) — defines validation, activation, rollback, and release integrity.
- [Conversation and Attempt Lifecycle](conversation-and-attempt-lifecycle.md) — defines retained records and manual-deletion semantics.
- [Web Experience](web-experience.md) — defines protected visitor and reviewer surfaces plus streaming constraints.
- [Evaluation and Review](evaluation-and-review.md) — defines owner-only review data and access scope.

## Parameters

> **Authoring guidance:** Define session duration, credential rotation, backup, resource, restart, logging, and deletion-confirmation values in [parameters.md](parameters.md) with rationale.

| Parameter | Authoritative value | Rationale |
|-----------|---------------------|-----------|
| [`SHARED_VISITOR_CREDENTIAL_COUNT`](parameters.md#access-and-deployment) | 1 | Matches the small invited demo without public identity management |
| [`APPLICATION_INSTANCE_TARGET`](parameters.md#access-and-deployment) | 1 | Avoids distributed coordination before demand justifies it |
| [`HIGH_AVAILABILITY_MODE`](parameters.md#access-and-deployment) | Disabled | Keeps prototype operations proportional to its private audience |
| [`PERSISTENCE_LOCATION`](parameters.md#access-and-deployment) | Instance-local persistent storage | Supports local SQLite, artifacts, and indexes across restarts |
| [`AWS_PACKAGING`](parameters.md#unresolved-selections) | `TBD` | Packaging requires authored streaming, TLS, and persistence constraints |
| [`REVERSE_PROXY`](parameters.md#unresolved-selections) | `TBD` | Proxy selection must preserve streaming and cancellation behavior |

## Data Structures

> **Authoring guidance:** Define access and operational records without selecting a secrets service, session mechanism, process manager, or infrastructure-as-code tool.

### Visitor access session

Define authentication state, creation and expiry if any, credential-version association, revocation, and protected-surface scope without implying individual visitor identity.

### Reviewer authorization

Define the unresolved owner/reviewer role, allowed evaluation operations, separation from visitor access, and audit expectations.

### Deployment configuration

Define application identity, secret references, storage attachments, network exposure, active corpus release, process health, and version evidence without embedding secret values.

### Operational action record

Define actor/authorization, command or deletion type, target release or retained record, start/terminal state, timestamps, outcome, and recoverability.

### Backup and recovery set

Define the consistent identities and integrity evidence required to recover SQLite state, corpus artifacts, release manifests, and rebuildable indexes.

## Behavior

> **Authoring guidance:** Author complete access, deployment, recovery, and operational decision tables for these concerns.

### Shared visitor access

Specify credential verification, protected routes, session behavior, invalid attempts, credential rotation, and the absence of registration, profiles, or anonymous public access.

### Reviewer access

Specify how evaluation review is more restricted than visitor chat without inventing whether “owner” means one person, a role, or a separate credential.

### Secret handling

Specify that secrets remain outside deployable images and logs, required startup validation, rotation behavior, and failure-safe handling.

### Single-instance deployment

Specify network exposure, HTTPS, process startup, health, graceful shutdown, streaming compatibility, persistent volume attachment, and explicit absence of autoscaling or distributed workers.

### Persistent data and recovery

Specify durability across restarts, backup consistency, restore validation, local storage exhaustion, index rebuildability, and preservation of immutable release evidence.

### Offline corpus command execution

Specify authorized operator invocation, no execution inside web requests, command outcome recording, and delegation of acquisition/curation/index semantics to the owning specs.

### Manual deletion and takedown operations

Specify authorization, preview/confirmation, active-operation conflicts, scope, audit evidence, and propagation to derived indexes without claiming impossible erasure from external providers.

### Release activation and rollback operations

Specify operational execution of the curation system’s validated state transition, asset readiness, process coordination, and recovery from partial host failure without redefining release rules.

## Error Handling

> **Authoring guidance:** Define trigger, detection, response, and recovery for each case.

### Invalid or unavailable credential

Cover rejected access, credential-store failure, rotation races, session revocation, and safe operator recovery.

### Unauthorized reviewer access

Cover visitor attempts to reach review data, ambiguous role configuration, and audit behavior without leaking evaluation content.

### Missing secret or invalid startup configuration

Cover fail-closed startup, diagnostic redaction, health reporting, and corrected restart.

### Persistent storage exhaustion or loss

Cover write failure, stream/finalization impact, corpus unavailability, read-only safety, restore, and prevention of false success.

### Process or instance restart

Cover active attempts, incomplete output, database recovery, corpus-release availability, and resumed service without claiming backend generation continuation.

### Backup or restore inconsistency

Cover mismatched SQLite, manifests, artifacts, and indexes; require validation or rebuild before service.

### Offline operation failure

Cover partial acquisition, index build, activation, rollback, deletion, and retained operational evidence.

## Implementation Notes

> **Authoring guidance:** Address least privilege, network restriction, session security, secret redaction, streaming proxy behavior, SQLite backup consistency, volume monitoring, restart recovery, and low-complexity observability. Do not add managed databases, distributed workers, autoscaling, public accounts, or high availability without a reviewed specification change.

## Test Scenarios

> **Authoring guidance:** During full authoring, create the `TS-OPS-{NUMBER}` scenario index. Cover valid/invalid visitor access, reviewer isolation, secret absence/rotation, HTTPS and stream proxying, restart during generation, persistent-volume recovery, storage exhaustion, backup/restore validation, offline-command authorization, deletion, release rollback, and rejection of public anonymous access.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-07-18 | Initial skeleton |
