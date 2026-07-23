# Parameters

> **Spec Version**: 0.3.0
> **Last Updated**: 2026-07-23
> **Depends On**: None (foundational specification)
> **Depended By**: Every system specification that references these values

---

## Overview

This specification is the single source of truth for tuning values, fixed source identifiers, limits, target ranges, and unresolved configuration selections in Halls of Knowledge. Every parameter includes a rationale explaining why the value exists; system specs MUST reference this file rather than duplicate constants without context.

A value marked `TBD` is intentionally unresolved and MUST be selected through the owning specification’s review rather than inferred during implementation.

## Corpus source and scope

| Parameter | Value | Unit | Rationale |
|-----------|-------|------|-----------|
| `SOURCE_WIKI_DATABASE` | `enwiki` | Wikimedia database identifier | Fixes the initial corpus language and source authority so it cannot silently drift to another wiki. |
| `INITIAL_SOURCE_DUMP_RUN` | `20260701` | Dated Wikimedia run identifier | Pins the initial source run and prevents `/latest/` from becoming provenance; the identifier is not treated as a transaction timestamp. |
| `INITIAL_SOURCE_DUMP_FILENAME` | `enwiki-20260701-pages-articles.xml.bz2` | Wikimedia artifact filename | Identifies the full non-multistream article dump selected for initial offline extraction. |
| `FIRST_DUMP_EXTRACTION_PROFILE` | Full non-multistream article dump | Acquisition profile | Favors one simple sequential offline scan over multistream range handling for the first demo. |
| `SOURCE_NAMESPACE` | 0 | MediaWiki namespace | Explicit filtering is required because the article-dump filename does not reliably guarantee namespace-zero-only content. |
| `ACQUISITION_CANONICAL_ARTICLE_TARGET` | 60–80 | Unique canonical articles after redirect resolution | Provides enough choice to assemble a strong 25–50-article first release without reviewing an unnecessarily broad corpus. |
| `INITIAL_APPROVED_ARTICLE_TARGET` | 25–50 | Manually approved pages | Keeps first-release curation practical while covering enough lore to exercise retrieval and synthesis; this is guidance, not a validation threshold. |
| `INITIAL_MEDIA_SCOPE` | Text only | Content policy | Avoids file-specific media licensing and Tolkien image, map, audio, video, and logo rights during the initial demo. |
| `SUPPORTED_PASSAGE_STRUCTURE` | Prose paragraphs | Structural content policy | Keeps extraction and review focused on readable answer evidence rather than tables, lists, quotations, references, or layout fragments. |
| `INITIAL_INDEXABLE_CLASSIFICATION` | Internal lore only | Passage classification | Prevents creation history, analysis, reception, adaptations, and administrative material from becoming answer evidence. |
| `MINIMUM_RELEASE_PASSAGE_COUNT` | 1 | Included lore passage | Prevents activation of an operationally useless empty corpus release without turning the target page range into a hard gate. |
| `CORPUS_RELEASE_RETENTION_POLICY` | Until manual deletion | Policy | Avoids automated cleanup complexity and preserves simple operator rollback for the small demo. |
| `EMITTED_PASSAGE_REVIEW_SAMPLE` | 20 | Percent per article, rounded up | Gives higher-risk emitted prose broad deterministic human inspection without requiring review of every passage before curation. |
| `STRUCTURAL_EXCLUSION_REVIEW_SAMPLE` | 10 | Percent per article, rounded up | Samples the more numerous exclusions for lost useful prose while keeping acquisition acceptance practical. |

## Corpus retrieval

| Parameter | Value | Unit | Rationale |
|-----------|-------|------|-----------|
| `INITIAL_RETRIEVAL_STRATEGY` | SQLite full-text keyword search | Retrieval policy | Provides a transparent lexical baseline without an embedding provider, score fusion, or another service. |
| `CORPUS_SEARCH_RESULT_LIMIT` | 8 | Extracted passages | Supplies enough evidence candidates for small synthesis while limiting agent-context noise. |
| `SURROUNDING_CONTEXT_RADIUS` | 1 | Eligible passage per direction | Adds immediate local meaning without crossing sections or skipping excluded material. |

## Conversation lifecycle

| Parameter | Value | Unit | Rationale |
|-----------|-------|------|-----------|
| `MAX_ACTIVE_ATTEMPTS_PER_CONVERSATION` | 1 | Generation attempt | Prevents concurrent attempts from racing conversation context, visible output replacement, cancellation, and persistence state. |
| `CONVERSATION_RETENTION_POLICY` | Until manual deletion | Policy | Preserves reloadable conversations for the private demo without inventing an unapproved automated expiry period. |
| `ATTEMPT_RETENTION_POLICY` | Until manual deletion | Policy | Retains failed, cancelled, retried, and successful attempt metadata for debugging and evaluation while leaving deletion under explicit owner control. |
| `EVALUATION_REVIEW_RETENTION_POLICY` | Until manual deletion | Policy | Matches the confirmed owner-controlled retention boundary and avoids silent loss of human evaluation evidence. |

## Evaluation

| Parameter | Value | Unit | Rationale |
|-----------|-------|------|-----------|
| `INITIAL_EVALUATION_CASE_TARGET` | 12–20 | Human-reviewed cases | Provides varied supported, synthesis, abstention, guide, and pretrained-knowledge probes while remaining feasible for careful manual review. |
| `INITIAL_RETRIEVAL_ABLATION_CONDITIONS` | Normal retrieval; retrieval disabled | 2 conditions | Isolates the value of retrieval in the smallest meaningful blinded comparison before adding judges or broader benchmarks. |
| `EVALUATION_VERDICT_SET` | Left better; tie; right better; both fail | 4 choices | Captures directional preference, equivalence, and shared failure without forcing a winner. |

## Access and deployment

| Parameter | Value | Unit | Rationale |
|-----------|-------|------|-----------|
| `SHARED_VISITOR_CREDENTIAL_COUNT` | 1 | Credential | Matches the small invited demo boundary without introducing public account management. |
| `APPLICATION_INSTANCE_TARGET` | 1 | Running instance | Keeps deployment and persistent local storage simple until demonstrated load or availability requirements justify distribution. |
| `HIGH_AVAILABILITY_MODE` | Disabled | Deployment policy | Avoids unneeded replication, coordination, and failover complexity in the private prototype. |
| `PERSISTENCE_LOCATION` | Instance-local persistent storage | Storage policy | Supports SQLite, corpus artifacts, and indexes across restarts without introducing a managed database or distributed filesystem. |

## Unresolved selections

| Parameter | Value | Owning specification | Rationale for remaining open |
|-----------|-------|----------------------|-----------------------------|
| `MODEL_PROVIDER` | `TBD` | Lore Agent and Response Policy | Provider choice requires evidence about grounding, streaming, cancellation, cost, and deployment constraints. |
| `MODEL_ID` | `TBD` | Lore Agent and Response Policy | The model must be evaluated against the initial cases rather than selected from pretrained reputation. |
| `ATTRIBUTION_PANEL_PLACEMENT` | `TBD` | Evidence Presentation and Attribution; Web Experience | Citation and license obligations are confirmed, but their exact UI placement requires design and legal review. |
| `AWS_PACKAGING` | `TBD` | Private Demo Access and Operations | The private single-instance constraint is fixed, but container, service, and image choices are not yet justified. |
| `REVERSE_PROXY` | `TBD` | Private Demo Access and Operations | A proxy should be selected only after TLS, streaming, cancellation, and packaging requirements are authored. |
