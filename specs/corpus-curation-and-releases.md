# Corpus Curation and Releases

> **Spec Version**: 1.0.0
> **Last Updated**: 2026-07-18
> **Depends On**: [Corpus Acquisition and Provenance](corpus-acquisition-and-provenance.md)
> **Depended By**: [Corpus Retrieval and Agent Tools](corpus-retrieval-and-agent-tools.md), [Conversation and Attempt Lifecycle](conversation-and-attempt-lifecycle.md)

---

## Overview

Corpus Curation and Releases lets the single operator classify acquired prose at page, section, or paragraph scope and publish an immutable inventory of approved lore passages. It owns hierarchical curation decisions, the rapid offline curation cockpit, release assembly and validation, active-release selection, retention, and rollback.

Candidate discovery belongs to [Corpus Acquisition and Provenance](corpus-acquisition-and-provenance.md#candidate-discovery). This system begins with immutable article artifacts. It does not archive exclusion evidence in release manifests, maintain a multi-reviewer workflow, model conflicts among lore accounts, build retrieval indexes, or expose curation through the web application.

## Dependencies

### Technology dependencies

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | To be pinned | Package-owned curation and release commands |
| Terminal input/output | Host terminal baseline | Single-key interactive curation cockpit |
| Package-owned filesystem artifacts | Serialization format is an implementation choice | Mutable curation working data and immutable release manifests |

### Spec dependencies

- [Corpus Acquisition and Provenance](corpus-acquisition-and-provenance.md) — supplies candidate articles, immutable article artifacts, extracted passages, and lightweight provenance.

## Parameters

| Parameter | Authoritative value | Rationale |
|-----------|---------------------|-----------|
| [`INITIAL_APPROVED_ARTICLE_TARGET`](parameters.md#corpus-source-and-scope) | 25–50 pages | Guides manageable initial scope without becoming a release gate |
| [`INITIAL_MEDIA_SCOPE`](parameters.md#corpus-source-and-scope) | Text only | Prevents non-text material from entering curation |
| [`INITIAL_INDEXABLE_CLASSIFICATION`](parameters.md#corpus-source-and-scope) | Internal lore only | Defines the only classification eligible for a release |
| [`MINIMUM_RELEASE_PASSAGE_COUNT`](parameters.md#corpus-source-and-scope) | 1 lore passage | Rejects an operationally empty release |
| [`CORPUS_RELEASE_RETENTION_POLICY`](parameters.md#corpus-source-and-scope) | Until manual deletion | Keeps rollback simple without automated retention logic |

## Data Structures

### Curation decision

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| decision ID | string | Required; unique | Durable decision identity |
| article artifact ID | string | Required | Artifact being reviewed |
| scope | enum | page, section, or paragraph | Level to which the classification applies |
| scope identity | string | Required; artifact, heading path, or passage ID according to scope | Exact target |
| action | enum | classify or clear | Whether this decision assigns a value or removes the prior value at its scope |
| passage classification | enum | Required for classify; absent for clear | Classification inherited by the target and descendants |
| operator label | string | Required; non-empty | Offline-tool-supplied authorship label |
| timestamp | timestamp | Required | Decision time |
| supersedes decision IDs | list | Empty for an initial decision; one or more IDs when replacing prior decisions at the same scope | Explicit history linkage |

A curation decision does not require free-text rationale, authentication evidence, quorum, or a reviewer account.

### Curation working set

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| article artifacts | list | Zero or more immutable artifact references | Candidate content available for review |
| decisions | list | Zero or more ordered decisions | Complete retained classification history |
| effective classifications | map | Derived; MUST NOT be independently authoritative | Current most-specific classification for every passage |
| operator label | string | Required for new decisions | Label supplied by offline tooling |
| last reviewed passage | string | Optional | Convenience cursor; not classification authority |

### Passage classification

| Value | Release eligibility | Meaning |
|-------|---------------------|---------|
| Internal lore | Eligible | Fictional-world entities, events, relationships, places, or chronology |
| External creation history | Ineligible | Authorship, naming, sources, composition, or publication |
| Analysis or reception | Ineligible | Scholarship, criticism, influence, interpretation, or audience response |
| Adaptation material | Ineligible | Film, game, or other adaptation content outside initial lore scope |
| Reference or administrative material | Ineligible | Citation apparatus, navigation, or wiki-maintenance content |

### Corpus release manifest

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| release ID | string | Required; unique and operator supplied or deterministically generated | Immutable release identity |
| created timestamp | timestamp | Required | Manifest creation time |
| source snapshot identity | map | Exactly one wiki database, dump run, and filename | Homogeneous source boundary |
| extractor identity | string | Exactly one parser name and version | Homogeneous extraction boundary |
| extractor configuration | map | Exactly one complete configuration | Homogeneous extraction boundary |
| included article artifacts | list | One or more unique artifact IDs | Artifacts containing included passages |
| included lore passages | list | At least `MINIMUM_RELEASE_PASSAGE_COUNT`; unique passage IDs | Complete release body |

The manifest lists included content only. Excluded candidates, passages, and prior curation decisions remain in curation working data and MUST NOT be copied into the immutable release manifest.

### Corpus release

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| release ID | string | Required | Manifest identity |
| manifest | Corpus release manifest | Required; immutable after validation | Authoritative release body |
| validation state | enum | draft, valid, or invalid | Result of structural validation |
| validation timestamp | timestamp | Required when valid or invalid | Latest validation result |
| activation records | list | Zero or more activate/deactivate events | Mutable selection history outside the manifest body |

At most one valid release is active. A valid inactive release remains available for later rollback until manually deleted.

## Behavior

### Effective classification

For every extracted passage, the system MUST inspect decision scopes in this precedence:

1. the latest unsuperseded paragraph decision;
2. then the latest unsuperseded decision for its exact heading path;
3. then the latest unsuperseded page decision; and
4. finally undecided.

At each scope, a classify action supplies the effective classification and stops evaluation; a clear action removes that scope’s value and continues to the parent scope. A more-specific classify action MUST override an inherited decision regardless of timestamp. A changed decision at the same scope MUST explicitly supersede the prior decision; timestamps alone MUST NOT select between unresolved competing decisions. An undecided passage MUST be excluded from every corpus release.

### Classification workflow

1. The operator MAY classify an entire page, one section, or one paragraph.
2. A page classification MUST apply to every descendant without a section or paragraph override.
3. A section classification MUST apply to every descendant paragraph without a paragraph override.
4. A paragraph decision MUST apply only to its exact passage ID.
5. Every saved decision MUST record the configured operator label and timestamp.
6. Clear and undo MUST create explicit superseding decisions; when no prior classification existed, undo MUST create a clear action so parent inheritance resumes.
7. The system MUST retain superseded decisions so undo and history inspection do not erase prior actions.
8. Classification MUST NOT alter article artifacts or extracted-passage source fields.

### Conflicting and uncertain accounts

The system MUST preserve each extracted paragraph’s source wording and independent classification. It MUST NOT require conflict groups, choose a “canon” account, or reconcile disagreements. If multiple conflicting passages are internal lore, each MAY enter the release independently; response policy owns any later explanation of uncertainty.

### Curation cockpit

The package-owned interactive review command MUST implement the approved [Curation cockpit](DESIGN_LANGUAGE.md#operator-cli):

1. The default frame MUST show only review progress, article and heading location, current passage text, target scope, and effective classification.
2. Classification keys MUST remain stable:
   - `1` — Internal lore;
   - `2` — External creation history;
   - `3` — Analysis or reception;
   - `4` — Adaptation material; and
   - `5` — Reference or administrative material.
3. A classification key MUST save without requiring Enter and advance immediately.
4. Paragraph scope MUST advance to the next paragraph.
5. Section scope MUST advance to the first passage in the next section.
6. Page scope MUST classify the page and transition to the end-of-pass summary.
7. `x` MUST skip the current passage without adding a decision.
8. `u` MUST undo the latest decision, preserve supersession history, and return to the affected passage for immediate reclassification.
9. `m` MUST toggle [Expanded instruments](DESIGN_LANGUAGE.md#operator-cli) containing neighboring context, raw wikitext, decision hierarchy, page/revision/passage identities, and less-common bulk controls.
10. The cockpit MUST save every accepted decision durably before advancing.
11. Restarting review MUST offer the first effectively undecided passage while permitting explicit navigation elsewhere.

The terminal interaction MAY use color, but scope, classification, progress, and controls MUST remain understandable without color.

### End-of-pass summary

1. Reaching the final passage through classification or skip MUST replace the review frame with an [End-of-pass summary](DESIGN_LANGUAGE.md#operator-cli).
2. The summary MUST be visually and textually distinct from passage review and MUST NOT rely on color alone.
3. It MUST report counts for all five classifications and the number of effectively undecided passages.
4. It MUST state either that every passage is classified or that passages need attention.
5. An optional detail view MUST list each passage’s effective classification and source scope.
6. Undo from the summary MUST reverse the latest decision and return to its passage.
7. Resume from the summary MUST move to the first effectively undecided passage when one exists.
8. The summary is operator feedback, not release validation.

### Scriptable command surface

Package-owned non-interactive commands MUST support:

- listing acquired candidates and article artifacts;
- showing undecided passages and effective classifications;
- applying or superseding a decision at a specified scope;
- previewing a proposed release body;
- validating and creating a release;
- listing releases and active status;
- activating and rolling back releases; and
- returning deterministic command results suitable for operator inspection and automation.

Command names, flags, CLI framework, and artifact serialization are implementation choices.

### Manifest assembly

1. A proposed manifest MUST include only passages whose effective classification is Internal lore.
2. It MUST include every article artifact referenced by an included passage and no unreferenced artifact.
3. Every included artifact MUST share one source snapshot identity and one extractor identity and configuration.
4. The 25–50-page target MUST NOT be enforced as a validation threshold.
5. Creating a release MUST snapshot the included IDs into a new immutable manifest; later curation changes MUST NOT mutate it.
6. Exclusion inventories and free-text curation rationale MUST NOT be required.

### Release validation

A release MUST be valid only when all of these conditions hold:

| Condition | Required validation result |
|-----------|----------------------------|
| Release ID is absent or duplicates an existing release | Invalid |
| Included passage count is below `MINIMUM_RELEASE_PASSAGE_COUNT` | Invalid |
| Referenced artifact or passage is missing | Invalid |
| Included passage is not effectively Internal lore at assembly time | Invalid |
| Duplicate artifact or passage ID exists | Invalid |
| Source snapshot or extractor configuration is mixed | Invalid |
| Every identity resolves and all conditions above pass | Valid |

Validation does not require checksums, content digests, an exclusion inventory, a retrieval index, or the target page count.

### Activation

1. The operator MAY explicitly activate any valid retained release.
2. Activation MUST make it the sole active corpus release and deactivate the previously active release.
3. Activation MAY occur before a compatible retrieval index exists.
4. Activation MUST NOT trigger index construction.
5. The resulting temporary index gap is an accepted operational state governed by [Corpus Retrieval and Agent Tools](corpus-retrieval-and-agent-tools.md#active-release-resolution).
6. Re-activating the already active release MUST be an idempotent no-op with a successful command result.

### Rollback and retention

1. Rollback MUST use the same activation operation to select a prior valid retained release.
2. Rollback MUST NOT mutate either release manifest.
3. Every release, manifest, and required article artifact MUST remain retained until manual operator deletion.
4. The active release MUST NOT be deleted.
5. Deleting an inactive release MUST identify derived retrieval indexes that may also be removed, while index deletion semantics remain owned by Spec 3.
6. No automatic age, count, or storage-based cleanup is required.

### Offline boundary

Acquisition review, curation, release creation, validation, activation, rollback, and deletion MUST occur through offline operator commands. This system MUST NOT provide browser curation, reviewer accounts, approval queues, background corpus jobs, web-request mutation, or a public corpus-management API.

## Error Handling

### Missing operator label

- **Trigger:** A command attempts to create a curation decision without a non-empty operator label.
- **Detection:** Input validation occurs before decision persistence.
- **Response:** Reject the decision and leave effective classifications unchanged.
- **Recovery:** Configure or supply the operator label and retry.

### Unknown scope identity

- **Trigger:** A page, heading path, or passage ID does not exist in the referenced immutable article artifact.
- **Detection:** Scope resolution fails against acquired artifacts.
- **Response:** Reject the decision without partial persistence.
- **Recovery:** Inspect available identities and submit a valid target.

### Ambiguous decision history

- **Trigger:** More than one unsuperseded decision exists at the same exact scope.
- **Detection:** Effective-classification derivation finds competing decisions.
- **Response:** Mark affected passages undecided and block their release inclusion.
- **Recovery:** Record an explicit superseding decision that identifies the replaced decisions.

### Incremental save failure

- **Trigger:** The cockpit cannot durably persist an accepted classification.
- **Detection:** Persistence does not confirm completion before advancement.
- **Response:** Remain on the current passage, report the failure prominently, and MUST NOT show the decision as saved.
- **Recovery:** Correct the storage problem and retry the classification.

### Undo failure

- **Trigger:** No prior decision exists or a superseding restoration cannot be persisted.
- **Detection:** History is empty or durable write fails.
- **Response:** Preserve current decisions and cursor; report why undo was not performed.
- **Recovery:** Continue review or correct persistence and retry.

### Invalid manifest

- **Trigger:** One or more release-validation conditions fail.
- **Detection:** Complete validation reports every detected condition.
- **Response:** Do not create a valid release or alter active status.
- **Recovery:** Correct curation or manifest assembly and create a new candidate manifest.

### Activation conflict

- **Trigger:** The selected release is missing, invalid, deleted, or concurrently changed by another operator process.
- **Detection:** Activation preconditions fail at the state transition.
- **Response:** Preserve the currently active release and report the failed precondition.
- **Recovery:** Refresh release status and retry with a valid retained release.

### Deletion conflict

- **Trigger:** The operator requests deletion of the active release or an artifact required by a retained release.
- **Detection:** Retained release references exist.
- **Response:** Reject deletion and list blocking release identities.
- **Recovery:** Activate another release or delete dependent inactive releases first.

## Implementation Notes

| Prototype record | Durable answer |
|------------------|----------------|
| Question | Can one developer classify passages quickly when a terminal review surface exposes hierarchy, context, correction, and progress? |
| Verdict | Approved: use a single-key curation cockpit with essential information by default and expanded instruments on demand. |
| Evidence | Dense always-visible information was rejected as hard to read; a focused frame was still too slow; classify-and-advance, undo-and-return, cockpit prioritization, and a distinct end summary were each accepted after hands-on revision. |
| Implications | The durable interface requires one-key classification, immediate advancement, reversible correction, progressive detail, durable incremental saves, resumability, and a visually distinct end-of-pass summary. Prototype code is not implementation authority. |

- Curation working data MUST survive process restarts even though its serialization format is not specified here.
- Decision persistence and cursor advancement SHOULD use an ordering that never advances after an unconfirmed save.
- Derived effective classifications MAY be cached but MUST be reproducible from immutable artifacts and retained decisions.
- Release manifests SHOULD be inspectable as ordinary package-owned artifacts.
- The one-operator assumption removes authorization and quorum behavior; it does not permit silent mutation of immutable releases.

## Test Scenarios

| ID | Category | Priority | Preconditions | Exact input | Observable expected output |
|----|----------|----------|---------------|-------------|----------------------------|
| `TS-CCR-001` | Inheritance | Critical | Article has three sections and no decisions | Page classification `Internal lore` | Every passage is effectively Internal lore from page scope |
| `TS-CCR-002` | Override | Critical | Page is Internal lore | Section classification `External creation history`, then one paragraph classification `Internal lore` | Section descendants are creation history except the explicit lore paragraph |
| `TS-CCR-003` | Undecided | Critical | One passage has no page, section, or paragraph decision | Assemble release | Undecided passage is absent from proposed manifest |
| `TS-CCR-004` | Classifications | Critical | Five passages are available | Apply one distinct canonical classification to each | Exactly one passage is release-eligible; all effective labels remain inspectable |
| `TS-CCR-005` | Fast review | High | Cockpit starts on first undecided paragraph | Press `1` once without Enter | Decision is durably Internal lore and cockpit displays the next paragraph |
| `TS-CCR-006` | Undo | High | Latest action classified passage 2 and advanced to passage 3 | Press `u`, then `3` | Latest decision is superseded, cursor returns to passage 2, reclassification saves as Analysis or reception, then advances |
| `TS-CCR-007` | Progressive detail | Medium | Cockpit default frame is visible | Press `m` twice | First press reveals context, raw text, hierarchy, and identities; second restores essential-only frame |
| `TS-CCR-008` | Save failure | Critical | Durable curation storage rejects a write | Press classification key `2` | Cockpit remains on current passage and does not report or derive a saved decision |
| `TS-CCR-009` | End summary complete | High | Final passage is the only undecided passage | Classify the final passage | Distinct summary reports all five counts, zero unclassified, and complete status |
| `TS-CCR-010` | End summary incomplete | High | Earlier passage was skipped | Reach final passage and press `x` | Distinct summary reports unresolved count; resume moves to first undecided passage |
| `TS-CCR-011` | Manifest content | Critical | Mixed effective classifications exist | Create candidate release | Manifest includes only Internal lore passage IDs and their referenced artifacts; no exclusion inventory appears |
| `TS-CCR-012` | Homogeneity | Critical | Lore passages come from two extractor configurations | Validate proposed manifest | Release is invalid and active status remains unchanged |
| `TS-CCR-013` | Minimum size | Critical | Proposed manifest has zero passages | Validate proposed manifest | Release is invalid; 25–50-page guidance is not evaluated |
| `TS-CCR-014` | Early activation | High | Valid release exists and no retrieval index exists | Activate release | Release becomes sole active release; no index build starts |
| `TS-CCR-015` | Rollback | High | Active release B and retained valid release A exist | Activate release A | A becomes active, B remains immutable and retained, and index availability is not inferred |
| `TS-CCR-016` | Retention | Medium | Active and two inactive releases exist | Delete one inactive release, then active release | Inactive deletion succeeds when dependencies permit; active deletion is rejected |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-07-18 | Authored and approved hierarchical curation, cockpit, release, activation, rollback, and retention contracts |
| 0.1.0 | 2026-07-18 | Initial skeleton |
