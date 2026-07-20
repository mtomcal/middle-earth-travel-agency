# Corpus Acquisition and Provenance

> **Spec Version**: 1.0.0
> **Last Updated**: 2026-07-18
> **Depends On**: None
> **Depended By**: [Corpus Curation and Releases](corpus-curation-and-releases.md)

---

## Overview

Corpus Acquisition and Provenance turns one dated official Wikimedia source snapshot into immutable, package-owned article artifacts and deterministic prose passages for operator curation. It owns candidate discovery, dump retrieval, namespace and revision selection, redirect resolution, raw-wikitext retention, conservative normalization, and lightweight source traceability.

The system optimizes for a one-developer private demo rather than archival or compliance-grade preservation. It MUST retain enough identity to attribute and reproduce an article extraction, but it does not require checksums, content digests, complete XML records, or permanent retention of the full dump. It ends before semantic passage classification, release governance, retrieval indexing, and runtime agent access.

## Dependencies

### Technology dependencies

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | To be pinned | Package-owned offline discovery, acquisition, and extraction commands |
| Wikimedia XML dump format | Export schema supplied by the selected dump | Official page, redirect, revision, timestamp, and raw-wikitext records |
| Offline wikitext parser | Implementation choice recorded in each artifact | Deterministic structural parsing and conservative prose normalization |

### Spec dependencies

None; this system is the foundation of the corpus data path.

## Parameters

| Parameter | Authoritative value | Rationale |
|-----------|---------------------|-----------|
| [`SOURCE_WIKI_DATABASE`](parameters.md#corpus-source-and-scope) | `enwiki` | Fixes source language and wiki identity |
| [`INITIAL_SOURCE_DUMP_RUN`](parameters.md#corpus-source-and-scope) | `20260701` | Identifies the dated initial source run without implying a transaction timestamp |
| [`INITIAL_SOURCE_DUMP_FILENAME`](parameters.md#corpus-source-and-scope) | `enwiki-20260701-pages-articles.xml.bz2` | Selects the exact full article-dump artifact |
| [`FIRST_DUMP_EXTRACTION_PROFILE`](parameters.md#corpus-source-and-scope) | Full non-multistream article dump | Keeps initial acquisition to one sequential offline scan |
| [`SOURCE_NAMESPACE`](parameters.md#corpus-source-and-scope) | 0 | Prevents non-article namespaces from entering curation |
| [`INITIAL_MEDIA_SCOPE`](parameters.md#corpus-source-and-scope) | Text only | Keeps non-text rights and extraction outside the first demo |
| [`SUPPORTED_PASSAGE_STRUCTURE`](parameters.md#corpus-source-and-scope) | Prose paragraphs | Defines the only initial structure eligible to become an extracted passage |

## Data Structures

### Source snapshot

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| wiki database | string | Required; equals `SOURCE_WIKI_DATABASE` | Wikimedia database identity |
| dump run | string | Required; dated identifier; MUST NOT be `/latest/` | Named source run |
| filename | string | Required; exact selected artifact name | Full non-multistream XML dump |
| source URL | string | Required; dated URL containing the run and filename | Retrieval location |
| retrieval timestamp | timestamp | Required | Time the operator obtained the local copy |
| extraction profile | enum | Required; full non-multistream for the initial release | Scan strategy |

A source snapshot identifies source material; it does not assert transaction-time consistency or checksum verification.

### Discovery record

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| discovery route | enum | `category or API`, or `human nomination` | How the candidate was proposed |
| discovery reference | string | Required | Category/query URL or human-nomination label |
| observed page title | string | Required when page ID is absent | Proposed title |
| observed page ID | integer | Optional until resolved from the dump | Proposed page identity |
| discovery timestamp | timestamp | Required | When the proposal was recorded |

Complete API responses, recursive category traversals, and category snapshots are not part of this record.

### Article artifact

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| article artifact ID | string | Required; deterministic from dump run, page ID, revision ID, and extractor configuration | Stable identity for one immutable extraction |
| wiki database | string | Required | Source wiki |
| dump run | string | Required | Source snapshot identity |
| page ID | integer | Required | Namespace-0 page identity |
| namespace | integer | Required; equals `SOURCE_NAMESPACE` | Explicitly verified namespace |
| canonical title | string | Required | Title serialized in the selected dump |
| redirect chain | list | Zero or more source-title and target-title steps | Provenance from proposed alias to final page |
| revision ID | integer | Required | Exact revision serialized in the dump |
| parent revision ID | integer | Optional when absent from source | Revision lineage |
| revision timestamp | timestamp | Required | Exact source revision timestamp |
| permanent revision URL | string | Required | User-usable exact-revision destination |
| history URL | string | Required | Contributor-attribution destination |
| raw wikitext | string | Required | Exact source text from the selected revision |
| extractor identity | string | Required | Parser name and version |
| extractor configuration | map | Required | Complete behavior-affecting extraction configuration |
| extracted passages | list | Zero or more | Deterministic normalized prose paragraphs |
| structural exclusions | list | Zero or more structure type and reason records | Material not eligible for extraction |

An article artifact MUST be immutable after successful creation. Reprocessing the same revision with changed extractor identity or configuration MUST create a different article artifact.

### Extracted passage

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| passage ID | string | Required; deterministic from article artifact ID, heading path, and paragraph ordinal | Stable identity within one article artifact |
| article artifact ID | string | Required | Owning artifact |
| heading path | list | Required; lead uses the canonical `Lead` path | Ordered section context |
| paragraph ordinal | integer | Required; positive and unique within heading path | Deterministic structural coordinate |
| normalized text | string | Required; non-empty prose | Text eligible for curation |
| structure | enum | `prose paragraph` | Initial supported structure |

Passage IDs MUST distinguish duplicate text at different structural coordinates. The system does not infer identity across different article artifacts.

### Acquisition failure

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| candidate identity | string | Required | Failed proposal or resolved page identity |
| stage | enum | discovery resolution, source scan, redirect resolution, parsing, normalization, artifact creation | Failed operation |
| reason | string | Required | Operator-readable cause |
| recoverable | boolean | Required | Whether corrected input or configuration may be retried |

## Behavior

### Candidate discovery

1. The system MUST accept candidate articles from preserved Wikimedia category/API queries and direct human nomination.
2. A live discovery result MAY differ from the page or revision in the dated source snapshot; discovery is advisory and MUST NOT replace dump authority.
3. Discovery records MUST be deduplicated by resolved page ID when available and otherwise by normalized proposed title.
4. Category membership MUST NOT classify, approve, or include a page.
5. Candidate discovery MUST run only as an offline corpus command.

### Source selection and retrieval

1. The initial source URL MUST contain the exact dated run and filename from [parameters.md](parameters.md#corpus-source-and-scope).
2. `/latest/` MUST NOT be recorded or accepted as source provenance.
3. Successful retrieval MUST produce a local file that decompresses completely and contains a complete parseable XML document through its expected end marker.
4. Whole-file checksums, published digest manifests, local content digests, and byte-size evidence are not required by this contract.
5. The system MUST stop the source scan when retrieval, decompression, or document-level parsing is incomplete.

### Page and revision selection

1. The system MUST scan the full non-multistream article dump offline for proposed identities.
2. It MUST explicitly accept only namespace `0`, regardless of the dump filename.
3. The authoritative revision MUST be exactly the revision serialized for that page in the selected dump.
4. The nominal dump-run date MUST NOT be interpreted as a transaction cutoff.
5. A later API revision, an earlier revision selected by date, or pretrained source knowledge MUST NOT replace the serialized dump revision.
6. A candidate absent from the dump MUST produce an acquisition failure and no article artifact.

### Redirect resolution

1. A redirect candidate MUST be resolved using redirect records from the selected dump.
2. Every redirect hop MUST be retained in the final article artifact’s redirect chain.
3. Only the final namespace-0 target MAY receive an article artifact.
4. A redirect fragment MAY be retained as discovery context but MUST NOT automatically restrict extracted passages.
5. A loop, missing target, or target outside namespace 0 MUST produce an acquisition failure and no artifact for that proposal.

### Artifact construction

1. An article artifact MUST contain raw wikitext and normalized prose in one compound immutable record.
2. It MUST retain exact page, revision, timestamp, permanent-revision, history, redirect, and extractor identities.
3. It MUST NOT require the complete XML page record, contributor identity, edit comment, checksums, content digests, or source byte offsets.
4. Artifact and passage identifiers MUST be deterministic from their declared source and structural identities.
5. Repeating extraction with the same source revision and extractor configuration MUST reproduce the same semantic fields, passage boundaries, normalized text, and identifiers.

### Eligible structures

| Source structure | Required treatment |
|------------------|-------------------|
| Lead prose paragraph | Extract under heading path `Lead` |
| Prose paragraph under headings | Extract with full heading path and paragraph ordinal |
| Infobox or table | Record as structurally excluded |
| List or navigation box | Record as structurally excluded |
| Inline reference or reference section | Remove inline marker or record section as structurally excluded; never emit as answer prose |
| Caption | Record as structurally excluded |
| Poetry, lyrics, or block quotation | Record as structurally excluded |
| Image, map, audio, video, or logo | Exclude under text-only scope |

Sections organize passages but MUST NOT become duplicate indexable passages.

### Prose normalization

The extractor MUST:

- remove emphasis markup while preserving displayed text;
- replace links with their displayed labels;
- decode standard entities;
- remove inline references and citation markers;
- normalize whitespace within each paragraph;
- preserve punctuation and capitalization; and
- preserve heading hierarchy as passage metadata.

The extractor MUST NOT silently invent displayed text, merge separate paragraphs, or cross section boundaries.

### Template handling

1. Template handling MUST be offline, deterministic, and versioned in extractor configuration.
2. Explicitly understood formatting or metadata templates MAY use fixed handling rules.
3. If an unresolved template may affect a paragraph’s meaning, the system MUST exclude that paragraph and record the structural exclusion.
4. The system MUST NOT call live MediaWiki rendering to complete extraction.
5. Full revision-correct template expansion is outside the initial contract.

### Best-effort candidate processing

1. Candidate processing MUST be independent after the source document is available.
2. Failure of one candidate MUST NOT remove successful artifacts or stop processing unrelated candidates.
3. The command result MUST list successful artifacts and acquisition failures separately.
4. A later corpus release MAY use any successfully acquired and curated subset.

### Local dump retention

1. The operator MAY delete the full downloaded dump after the scan completes and every successful article artifact can be read and structurally validated.
2. Deletion of the dump MUST NOT delete article artifacts, discovery records, or acquisition failures.
3. Reproduction after deletion requires reacquisition from the recorded dated URL; permanent source availability is not guaranteed.

### Offline command boundary

Package-owned offline commands MUST support candidate nomination/discovery, source acquisition and extraction, failure inspection, and artifact inspection. These operations MUST NOT execute in an HTTP request, background web job, lore-agent tool, or public corpus-management API.

## Error Handling

### Incomplete source download or XML

- **Trigger:** Retrieval fails, decompression ends unexpectedly, or the XML document lacks a valid terminal structure.
- **Detection:** The offline scan cannot reach successful decompression and document parsing completion.
- **Response:** Stop the scan and create no new artifacts from the incomplete source.
- **Recovery:** Reacquire the dated file and rerun the offline command.

### Candidate absent from source snapshot

- **Trigger:** No page matching the proposed page ID or title exists in the selected dump.
- **Detection:** The complete scan ends without a matching namespace-0 record.
- **Response:** Record a recoverable acquisition failure; continue other candidates.
- **Recovery:** Correct the nomination or select a later source snapshot through a future spec change.

### Namespace rejection

- **Trigger:** A proposed or redirected page resolves outside namespace 0.
- **Detection:** The serialized namespace differs from `SOURCE_NAMESPACE`.
- **Response:** Produce no artifact and record a non-eligible candidate failure.
- **Recovery:** Nominate an eligible namespace-0 target.

### Invalid redirect chain

- **Trigger:** A redirect loops, has no resolvable target, or ends outside namespace 0.
- **Detection:** A target repeats, is absent after the complete scan, or has a rejected namespace.
- **Response:** Produce no artifact for the proposal and preserve the observed chain in the failure record.
- **Recovery:** Correct the nomination or use a source snapshot in which the target resolves.

### Unsupported or ambiguous wikitext

- **Trigger:** Unsupported markup or an unresolved template may alter paragraph meaning.
- **Detection:** No configured deterministic handling rule can preserve readable meaning.
- **Response:** Exclude the affected paragraph and continue the article; if no eligible prose remains, the artifact MAY contain zero passages.
- **Recovery:** Change the extractor configuration, creating a new article artifact, or leave the material excluded.

### Nondeterministic extraction

- **Trigger:** Identical source and extractor configuration produce different semantic output or identifiers.
- **Detection:** A repeatability check finds unequal fields, boundaries, text, or IDs.
- **Response:** Reject the newly produced artifact and report the extractor defect.
- **Recovery:** Correct or replace the extractor and create a new artifact configuration.

### Artifact identity collision

- **Trigger:** A proposed artifact ID already exists with different source or extraction fields.
- **Detection:** Existing immutable fields differ from the proposed record.
- **Response:** Preserve the existing artifact and reject the proposed write.
- **Recovery:** Correct deterministic identity construction or use the proper extractor configuration identity.

## Implementation Notes

- The offline scan SHOULD be restartable without rewriting valid immutable artifacts.
- Artifact writes SHOULD become visible only after their complete record is durable.
- The parser library and artifact serialization format are implementation choices; neither is a suite parameter.
- Raw wikitext is the local source authority after the full dump is deleted.
- Internal filesystem paths MAY locate artifacts but MUST NOT become user-visible provenance.
- The initial pipeline intentionally favors a small candidate set and sequential scan over category closure, multistream ranges, checksum archives, or full MediaWiki rendering.

## Test Scenarios

| ID | Category | Priority | Preconditions | Exact input | Observable expected output |
|----|----------|----------|---------------|-------------|----------------------------|
| `TS-CAP-001` | Source selection | Critical | Dated source is reachable | Run `20260701`, filename `enwiki-20260701-pages-articles.xml.bz2` | Source snapshot records the dated URL and a complete scan begins without digest requirements |
| `TS-CAP-002` | Source rejection | Critical | None | Source URL containing `/latest/` | Command rejects the source before extraction and identifies the dated-run requirement |
| `TS-CAP-003` | Revision authority | Critical | Candidate exists in dump and live API reports another revision | Candidate page ID plus both observations | Artifact records only the revision serialized in the dump and preserves API data as discovery evidence only |
| `TS-CAP-004` | Namespace | Critical | Dump contains matching non-zero namespace page | Candidate title resolving to namespace other than 0 | No artifact is created; failure identifies namespace rejection; other candidates continue |
| `TS-CAP-005` | Redirect | High | Dump contains alias, target, and namespace data | Candidate naming a two-hop redirect to a namespace-0 page | One target artifact is created with both redirect hops and no redirect-only artifact |
| `TS-CAP-006` | Structure | Critical | Article contains prose, table, list, references, and block quotation | One pinned revision | Only lead/body prose paragraphs become passages; every unsupported structure is recorded as excluded |
| `TS-CAP-007` | Template safety | Critical | One paragraph contains meaning-dependent unresolved template | Pinned raw wikitext | Affected paragraph is excluded; unaffected prose remains; no live renderer is called |
| `TS-CAP-008` | Determinism | Critical | Valid artifact was previously extracted | Same revision and identical extractor configuration, run twice | Semantic fields, passage boundaries, normalized text, and identifiers are exactly equal |
| `TS-CAP-009` | Partial failure | High | Three candidates: valid, missing, valid | One acquisition operation | Two artifacts and one failure are reported; valid artifacts remain usable |
| `TS-CAP-010` | Retention | Medium | Scan complete and successful artifacts are readable | Operator deletes downloaded dump | Artifacts, discovery records, and failures remain; subsequent reproduction reports reacquisition requirement |
| `TS-CAP-011` | Identity | High | Same revision extracted under changed configuration | Original and changed extractor configuration | A new artifact and new passage IDs are produced; original artifact remains unchanged |
| `TS-CAP-012` | Provenance | Critical | One successful artifact | Inspect article and passage | Dump run, page/revision identity and timestamp, URLs, extractor configuration, heading path, and ordinal are available without checksums or source offsets |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-07-18 | Authored and approved acquisition, lightweight provenance, extraction, and error contracts |
| 0.1.0 | 2026-07-18 | Initial skeleton |
