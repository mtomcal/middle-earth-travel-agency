# Evidence Presentation and Attribution

> **Spec Version**: 0.1.0
> **Last Updated**: 2026-07-18
> **Depends On**: [Corpus Retrieval and Agent Tools](corpus-retrieval-and-agent-tools.md), [Lore Agent and Response Policy](lore-agent-and-response-policy.md)
> **Depended By**: [Web Experience](web-experience.md)

---

## Overview

> **Authoring guidance:** Define the downstream system that accepts already-segmented claim-to-passage bindings and resolves them into user-visible citations, guide source lists, exact-revision links, and conservative CC BY-SA attribution notices. Preserve the distinction between evidentiary citation and legal attribution, and forbid this system from re-segmenting or inventing claim support.

## Dependencies

### Technology dependencies

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | To be pinned | Typed evidence-resolution and presentation models |
| CC BY-SA | 4.0 | Conservative project-wide compliance path for displayed Wikipedia-derived answer text |
| Wikipedia permanent revision and history links | Current documented URL contracts to be verified | Stable provenance and contributor-attribution destinations |

### Spec dependencies

- [Corpus Retrieval and Agent Tools](corpus-retrieval-and-agent-tools.md) — resolves stable passage identities to exact article/revision provenance.
- [Lore Agent and Response Policy](lore-agent-and-response-policy.md) — supplies final claim spans, passage bindings, response type, and inference markers.

## Parameters

> **Authoring guidance:** Put display thresholds, citation grouping limits, notice variants, and placement selections in [parameters.md](parameters.md) with rationale rather than embedding unexplained constants.

| Parameter | Authoritative value | Rationale |
|-----------|---------------------|-----------|
| [`ATTRIBUTION_PANEL_PLACEMENT`](parameters.md#unresolved-selections) | `TBD` | Exact UI placement requires design and legal review |
| Attribution license path | CC BY-SA 4.0 | Provides one conservative reuse path instead of attempting per-output GFDL compliance |
| Guide source-list requirement | Consolidated list required | Makes the guide’s full source set reviewable in addition to claim-level support |

## Data Structures

> **Authoring guidance:** Define presentation-ready structures without HTML, CSS, or browser-component details.

### Citation

Define claim-span identity, supporting passage identities, page title, section/passage context, revision identifier and timestamp, permanent revision URL, and support relationship.

### Source list

Define unique source entries, ordering, consolidation rules, and relation back to guide claim-level citations.

### Attribution notice

Define article and contributor attribution route, exact revision link, license link, modification statement, generated-answer disclaimer, and any page-specific notices that must be retained.

### Evidence presentation

Define the resolved citations, source list when applicable, attribution notices, response identity, and validation status supplied to trusted renderers.

## Behavior

> **Authoring guidance:** Author complete prescriptive rules and decision tables for these concerns.

### Binding resolution

Specify exact release and stable-passage lookup, claim-span preservation, multi-passage support, duplicate handling, and rejection of unresolved or cross-release bindings.

### Citation construction

Specify revision-level links, article title and section context, relation to the grounded claim, ordering, and the rule that retrieval alone does not establish support.

### Guide source-list construction

Specify consolidated source inclusion, deduplication, stable ordering, and coexistence with claim-level citations.

### Attribution notice construction

Specify contributor attribution route, CC BY-SA link, modification notice, generated-output disclaimer, visible external notices, and conservative treatment for summarized Wikipedia-derived text.

### Abstention and claim-free responses

Specify whether and how provenance or attribution appears when no grounded claim binding exists without manufacturing citations.

### Legal-boundary preservation

Specify text-only scope, no endorsement implication, no Wikimedia marks or trade dress, and escalation rather than invented legal conclusions about Tolkien rights or output-specific adaptation status.

## Error Handling

> **Authoring guidance:** Define trigger, detection, response, and recovery for each case.

### Missing or stale passage identity

Cover unresolved IDs, release mismatch, missing article artifact, and refusal to construct a misleading citation.

### Claim span and binding mismatch

Cover invalid offsets or identities without re-segmenting the claim inside this system.

### Missing attribution evidence

Cover absent revision links, contributor-history route, license information, modification notice, or retained page-specific notice.

### Unsafe or misleading source consolidation

Cover duplicate revisions, same-title different-revision collisions, and source-list entries not used by any claim.

### Unsupported media or third-party notice

Cover non-text inputs and content whose rights treatment cannot follow the initial conservative path.

## Implementation Notes

> **Authoring guidance:** Address deterministic ordering, URL validation, deduplication identity, localization boundaries, legal-review hooks, takedown/reindex traceability, and separation between presentation models and trusted HTML. This research-backed contract is not legal advice.

## Test Scenarios

> **Authoring guidance:** During full authoring, create the `TS-EVID-{NUMBER}` scenario index. Cover one and multiple citations, multi-source claims, guide source consolidation, revision collisions, unresolved IDs, cross-release bindings, abstention, complete attribution notices, modification statements, non-text rejection, no endorsement, and preservation of claim spans.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-07-18 | Initial skeleton |
