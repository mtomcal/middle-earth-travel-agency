# Corpus Retrieval and Agent Tools

> **Spec Version**: 1.0.0
> **Last Updated**: 2026-07-18
> **Depends On**: [Corpus Curation and Releases](corpus-curation-and-releases.md)
> **Depended By**: [Lore Agent and Response Policy](lore-agent-and-response-policy.md), [Evidence Presentation and Attribution](evidence-presentation-and-attribution.md)

---

## Overview

Corpus Retrieval and Agent Tools builds one disposable SQLite full-text index from one immutable corpus release and exposes the active corpus through two narrow lore-agent tools: lexical search and immediate surrounding context. It owns index construction, compatibility, active-release resolution, plain-text ranking behavior, passage lookup, retrieval-disabled behavior, and the agent-safe retrieval boundary.

The runtime tool surface treats the lore corpus as singular. The lore agent cannot choose, enumerate, or fall back among corpus releases. Release selection remains an operator concern in [Corpus Curation and Releases](corpus-curation-and-releases.md#activation); every tool result still carries the internally selected release identity for downstream message and citation traceability.

The initial strategy is keyword retrieval only. Vector search, embeddings, score fusion, GraphRAG, live web search, arbitrary filesystem access, and agent-visible provenance inspection are outside this contract.

## Dependencies

### Technology dependencies

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | To be pinned | Offline index commands and runtime tool boundary |
| SQLite full-text search | Version supplied by pinned Python/SQLite runtime | Single-instance lexical passage index |

### Spec dependencies

- [Corpus Curation and Releases](corpus-curation-and-releases.md) — supplies valid immutable release manifests and the sole active-release identity.

## Parameters

| Parameter | Authoritative value | Rationale |
|-----------|---------------------|-----------|
| [`INITIAL_INDEXABLE_CLASSIFICATION`](parameters.md#corpus-source-and-scope) | Internal lore only | Prevents excluded classifications from becoming answer evidence |
| [`INITIAL_RETRIEVAL_STRATEGY`](parameters.md#corpus-retrieval) | SQLite full-text keyword search | Establishes the simple initial projection |
| [`CORPUS_SEARCH_RESULT_LIMIT`](parameters.md#corpus-retrieval) | 8 passages | Limits context noise while supporting synthesis |
| [`SURROUNDING_CONTEXT_RADIUS`](parameters.md#corpus-retrieval) | 1 passage per direction | Defines the immediate local-context boundary |

## Data Structures

### Retrieval index descriptor

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| corpus release ID | string | Required; exactly one valid release | Authoritative index source |
| strategy | enum | SQLite full-text keyword search | Projection type |
| index schema version | string | Required | Compatibility identity for indexed fields and ranking behavior |
| tokenizer configuration | map | Required | Complete behavior-affecting lexical configuration |
| ranking configuration | map | Required | Field priority and tie-break behavior |
| build timestamp | timestamp | Required after successful build | Operator information |
| indexed passage count | integer | Required; equals included manifest passage count | Completeness evidence |
| state | enum | building, ready, or failed | Build lifecycle |

An index descriptor contains no content authority. The immutable corpus release manifest and article artifacts remain authoritative.

### Corpus query

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| query text | string | Required; must yield at least one lexical token | Agent-supplied plain text |
| retrieval condition | enum | normal or disabled | Controlled evaluation state; not agent-selected in visitor use |

The query has no corpus-release selector, field selector, path, raw SQLite syntax, requested result count, or score threshold.

### Retrieval result

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| corpus release ID | string | Required; internally selected active release | Traceability without release selection |
| passage ID | string | Required; included in active release | Stable evidence binding |
| article artifact ID | string | Required | Source artifact identity |
| canonical title | string | Required | Agent-readable article context |
| heading path | list | Required | Agent-readable section context |
| normalized passage text | string | Required | Exact approved lore prose |
| relevance order | integer | Required; 1 through returned result count | Deterministic ranked position |

Internal filesystem paths, raw wikitext, non-lore passages, revision URLs, attribution notices, and curation history MUST NOT appear in lore-agent search results.

### Surrounding context result

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| corpus release ID | string | Required | Same active release used for lookup |
| selected passage | Retrieval result | Required | Exact requested included passage |
| previous passage | Retrieval result | Optional; immediate eligible predecessor only | Local context |
| next passage | Retrieval result | Optional; immediate eligible successor only | Local context |

### Evidence resolution record

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| corpus release ID | string | Required | Release that supplied the passage |
| passage ID | string | Required | Grounded-claim binding |
| page and revision identity | map | Required | Exact title, page ID, revision ID and timestamp |
| heading path and paragraph ordinal | map | Required | Source context |
| permanent revision URL | string | Required | Citation destination |
| history URL | string | Required | Contributor-attribution destination |

Evidence resolution is an internal application contract consumed by [Evidence Presentation and Attribution](evidence-presentation-and-attribution.md), not a lore-agent tool.

## Behavior

### Index construction

1. The operator MUST explicitly start index construction through a package-owned offline command.
2. The command MUST accept one valid corpus release manifest, whether active or inactive.
3. It MUST index every and only included lore passage in that manifest.
4. Each indexed document MUST contain canonical title, heading path, normalized passage text, passage ID, article artifact ID, and release ID.
5. The build MUST reject missing, duplicate, or non-lore passage references.
6. A failed build MUST leave any existing ready index for that release unchanged.
7. A successful build MUST replace the prior index for that release atomically.
8. The index MUST be disposable and rebuildable from retained release and article artifacts.
9. Web requests and lore-agent tools MUST NOT initiate, wait for, or repair index construction.

### Index compatibility

An index is compatible only when all of these match the active release and runtime contract:

- corpus release ID;
- retrieval strategy;
- index schema version;
- tokenizer configuration; and
- ranking configuration.

Because corpus releases are immutable, compatibility does not require content hashes or digests. A mismatched descriptor MUST be treated as unavailable rather than queried.

### Active-release resolution

1. Each runtime tool call MUST resolve the sole active corpus release at admission.
2. It MUST use only a ready compatible index for that release.
3. The caller MUST NOT supply or override a release ID.
4. A tool call admitted against one active release MUST return that release identity even if operator activation changes concurrently.
5. A subsequent call MUST resolve the newly active release.
6. When the active release has no compatible ready index, the tool MUST return `index unavailable`.
7. It MUST NOT fall back to a prior release, use an incompatible index, interpret the condition as empty evidence, or build an index in the request path.

### Lexical indexing and ranking

1. Search MUST operate across canonical article title, heading path, and normalized passage text.
2. A match in either title or heading MUST contribute more relevance than the same match appearing only in passage text.
3. The relative weight of title versus heading is an implementation choice recorded in the ranking configuration.
4. Combined matches MAY outrank a single-field match according to the recorded ranking configuration.
5. Results MUST be ordered deterministically; equal relevance MUST use canonical title, heading path, paragraph ordinal, and passage ID as stable tie-breakers in that order.
6. The system MUST NOT enforce a per-article result quota or artificial source-diversity rule.
7. The system MUST return at most `CORPUS_SEARCH_RESULT_LIMIT` matching passages.
8. No minimum relevance threshold is required beyond at least one lexical match.

Exact numeric field weights and SQLite tokenizer selection are implementation choices recorded in the index descriptor and covered by acceptance behavior.

### Plain-text query handling

1. Agent input MUST be treated as plain text.
2. The system MUST normalize punctuation according to the index tokenizer without interpreting caller-provided field names, Boolean operators, wildcards, quoting syntax, or raw SQLite expressions as control syntax.
3. The caller MUST NOT alter classification filters, release scope, indexed fields, ranking configuration, or result limit.
4. Empty input or input producing no lexical tokens MUST return `invalid query`.
5. A valid query with no matching passage MUST return an empty result list, not an operational error.

### Search corpus tool

The lore-agent search tool MUST:

1. accept plain query text only;
2. resolve the active release internally;
3. enforce normal or controlled-disabled retrieval condition supplied by the calling application;
4. return zero to eight ordered retrieval results;
5. preserve exact approved passage text and stable passage IDs; and
6. expose no arbitrary path, raw index query, release selector, or provenance-inspection operation.

The agent MAY call search repeatedly with different plain-text queries.

### Get surrounding context tool

1. The tool MUST accept one passage ID obtained from search; it has no release selector or radius input.
2. It MUST validate that the passage belongs to the active release and compatible index used for the call.
3. It MUST return the selected passage.
4. It MAY return only the immediately preceding and immediately following extracted paragraphs.
5. A neighbor MUST be in the same article, same exact heading path, same active release, and included as Internal lore.
6. The tool MUST NOT skip over an excluded, undecided, missing, or differently classified paragraph to find a substitute.
7. It MUST NOT cross a section or article boundary.
8. Absence of one or both eligible neighbors is a successful result, not an error.

### Controlled retrieval-disabled condition

1. Evaluation MAY invoke both tools under the configured retrieval-disabled condition.
2. Disabled tools MUST return an explicit `retrieval disabled` outcome without consulting the index.
3. This outcome MUST remain distinguishable from `index unavailable`, `invalid query`, no matches, and unknown passage ID.
4. The lore agent MUST NOT be allowed to enable retrieval from inside a disabled invocation.

### Evidence resolution boundary

1. Internal application code MAY resolve a result’s release and passage IDs to exact revision and attribution fields.
2. Resolution MUST use retained release and article artifacts, not the lore-agent result text as authority.
3. Evidence resolution MUST NOT change claim segmentation or assert that a retrieval hit supports a claim.
4. The lore agent MUST NOT receive a separate provenance-inspection tool.

### Strategy evolution

The initial supported strategy is SQLite full-text keyword search only. Vector retrieval, embedding generation, hybrid score fusion, graph retrieval, and GraphRAG MAY enter a future specification only after matched evaluation identifies a concrete baseline failure and demonstrates improvement sufficient to justify added complexity.

## Error Handling

### Index unavailable

- **Trigger:** The active release has no ready compatible index.
- **Detection:** No descriptor matches all compatibility fields.
- **Response:** Return explicit `index unavailable`; do not search, fallback, build, or return an empty list.
- **Recovery:** The operator builds a compatible index offline or activates a release with one.

### Index build failure

- **Trigger:** Source references are missing or duplicated, a passage is not releasable, index creation fails, or final validation count differs from the manifest.
- **Detection:** Offline build or validation does not complete every required step.
- **Response:** Mark the candidate build failed and preserve any prior ready compatible index.
- **Recovery:** Correct release data, storage, or configuration and rerun the offline build.

### Invalid query

- **Trigger:** Search input is empty or tokenless after plain-text normalization.
- **Detection:** Tokenization yields no searchable terms.
- **Response:** Return explicit `invalid query` without consulting ranking.
- **Recovery:** The agent submits meaningful plain text.

### Unknown passage identity

- **Trigger:** Surrounding-context input is malformed, absent, fabricated, or not included in the active release.
- **Detection:** Exact passage lookup fails against the active compatible index.
- **Response:** Return `unknown passage`; do not search filesystem paths or another release.
- **Recovery:** Use a passage ID returned by current corpus search.

### Excluded-content leakage

- **Trigger:** An indexed document or context neighbor is not an included Internal lore passage.
- **Detection:** Build validation or runtime consistency checks find a classification or manifest violation.
- **Response:** Fail the build, or mark the affected ready index unavailable if detected at runtime; never return the passage.
- **Recovery:** Rebuild from a valid manifest and corrected source artifacts.

### Active release changes during a call

- **Trigger:** Operator activation changes after tool-call admission.
- **Detection:** Current active identity differs from the call’s admitted identity.
- **Response:** Complete against the admitted compatible index and return its internal release identity, or fail without mixing results; never combine releases.
- **Recovery:** A later call resolves the new active release.

### Evidence resolution failure

- **Trigger:** A retained passage cannot resolve to its article, page/revision fields, permanent URL, or history URL.
- **Detection:** Referential lookup is incomplete.
- **Response:** Reject evidence materialization for that passage and report an internal provenance error.
- **Recovery:** Restore retained release/artifact data or remove the invalid release through operator workflow.

## Implementation Notes

- SQLite full-text index storage MAY be colocated with other instance-local data but remains a derived artifact.
- Search and context interfaces SHOULD use typed application models rather than exposing SQLite rows or query syntax.
- Query normalization MUST harden the boundary even if the chosen SQLite API already parameterizes input.
- Index replacement SHOULD prevent readers from observing a partial build.
- Retained inactive indexes MAY be kept or deleted by the operator; runtime tools never enumerate or choose them.
- No network provider, embedding model, provider timeout, or score-normalization contract exists in the initial retrieval path.

## Test Scenarios

| ID | Category | Priority | Preconditions | Exact input | Observable expected output |
|----|----------|----------|---------------|-------------|----------------------------|
| `TS-RET-001` | Index build | Critical | Valid release contains five lore passages | Offline build for release A | Ready descriptor identifies A and indexed count is exactly five |
| `TS-RET-002` | Index exclusion | Critical | Manifest or source attempts to expose one non-lore passage | Offline build | Build fails and no candidate index becomes ready |
| `TS-RET-003` | Atomic rebuild | Critical | Ready index exists; replacement build fails | Rebuild same release with failing storage | Existing ready index remains queryable and unchanged |
| `TS-RET-004` | Active gap | Critical | Release B is active with no index; release A has a ready index | Search query `Gandalf` | Tool returns `index unavailable` and does not query A |
| `TS-RET-005` | Active-only scope | Critical | A is retained; B is active; both have indexes | Agent searches `ring` without a release selector | Only B is queried and every result carries B internally |
| `TS-RET-006` | Plain text | Critical | Ready active index exists | Query containing SQLite operators, quotes, wildcard, and field-like text | Input is tokenized as plain text and cannot alter fields, filters, limit, or release |
| `TS-RET-007` | Invalid query | High | Ready active index exists | Empty string, then punctuation-only string | Each returns `invalid query`; neither returns no-match or index error |
| `TS-RET-008` | No matches | High | Ready active index exists | Valid tokens absent from corpus | Successful search returns an empty result list |
| `TS-RET-009` | Ranking fields | High | Same term appears only in title of A, heading of B, and body of C | Search that exact term | A and B both rank before C; A-versus-B order follows the recorded ranking configuration |
| `TS-RET-010` | Result limit | Critical | At least twelve passages match equally | One plain-text search | Exactly eight results return in deterministic tie-break order with no article quota |
| `TS-RET-011` | Context | Critical | Selected passage has immediate included neighbors in same section | Context lookup by returned passage ID | Selected, previous, and next passages return; all belong to same article, heading, and active release |
| `TS-RET-012` | Context boundary | Critical | Immediate predecessor is excluded and an earlier lore passage exists | Context lookup for selected passage | No previous passage returns; tool does not skip over exclusion |
| `TS-RET-013` | Context identity | High | Active index exists | Fabricated passage ID | Tool returns `unknown passage` without path lookup or release fallback |
| `TS-RET-014` | Retrieval ablation | Critical | Active compatible index exists | Search under retrieval-disabled condition | Explicit `retrieval disabled` returns without consulting index |
| `TS-RET-015` | Activation race | High | Call admitted against A; operator activates B during search | One search call | Output contains only A results and A identity, or fails without mixed-release results; later call uses B |
| `TS-RET-016` | Evidence boundary | Critical | Search result resolves to retained artifact | Internal evidence resolution by release and passage ID | Exact revision and URL fields resolve; no provenance tool appears in lore-agent tool list |
| `TS-RET-017` | Strategy scope | Medium | Initial deployment configuration | Enumerate supported retrieval projections | SQLite keyword index is the only supported strategy; vector and graph projections are absent |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-07-18 | Authored and approved SQLite keyword retrieval, active-corpus tool, indexing, context, and error contracts |
| 0.1.0 | 2026-07-18 | Initial skeleton |
