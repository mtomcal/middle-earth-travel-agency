# Corpus Curation and Releases

> **Spec Version**: 2.0.0
> **Last Updated**: 2026-07-23
> **Depends On**: [Corpus Acquisition and Provenance](corpus-acquisition-and-provenance.md)
> **Depended By**: [Corpus Retrieval and Agent Tools](corpus-retrieval-and-agent-tools.md), [Conversation and Attempt Lifecycle](conversation-and-attempt-lifecycle.md)

---

## Overview

Corpus Curation and Releases lets the single operator classify accepted acquired prose at page, section, or paragraph scope and publish an immutable inventory of approved lore passages. It owns the versioned curation rubric, hierarchical curation decisions, atomic question-and-answer audit, the rapid offline curation cockpit, reviewed-article selection, release assembly and validation, release-completion evidence, active-release selection, retention, and rollback.

Candidate discovery and acquisition acceptance belong to [Corpus Acquisition and Provenance](corpus-acquisition-and-provenance.md#acquisition-acceptance). This system begins only with accepted immutable article artifacts. It does not archive exclusion evidence or audit history inside release manifests, maintain a multi-reviewer workflow, model conflicts among lore accounts, build retrieval indexes, or expose curation through the web application.

## Dependencies

### Technology dependencies

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | To be pinned | Package-owned curation and release commands |
| Terminal input/output | Host terminal baseline | Single-key interactive curation cockpit |
| Package-owned filesystem artifacts | Serialization format is an implementation choice | Mutable curation working data and immutable release manifests |

### Spec dependencies

- [Corpus Acquisition and Provenance](corpus-acquisition-and-provenance.md) — supplies accepted homogeneous acquisitions, immutable article artifacts, extracted passages, and lightweight provenance.

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
| article artifact ID | string | Required; belongs to one accepted homogeneous acquisition | Artifact being reviewed |
| curation rubric version | string | Required | Policy used to answer the classification question |
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
| article artifacts | list | Zero or more immutable artifact references from one accepted acquisition | Candidate content available for review |
| decisions | list | Zero or more ordered decisions | Complete retained classification history |
| effective classifications | map | Derived; MUST NOT be independently authoritative | Current most-specific classification for every passage |
| operator label | string | Required for new decisions | Label supplied by offline tooling |
| curation rubric | Curation rubric | Required | Current classification policy and retained history |
| quick-key audit events | list | Complete append-only state-changing history | Question-and-answer evidence |
| stale decision IDs | list | Derived from material rubric revisions | Decisions requiring re-answer before selected-article release |
| last reviewed passage | string | Optional | Convenience cursor; not classification authority |

### Curation rubric

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| rubric version | string | Required; unique | Policy identity recorded by decisions and audit events |
| predecessor version | string | Optional | Prior policy identity |
| change kind | enum | initial, editorial clarification, or material | Effect on earlier decisions |
| classification rules | list | Required | Concrete boundaries for all five passage classifications |
| affected prior decisions | list or rule | Required for material change | Decisions made stale; when impact cannot be bounded, every prior decision is affected |
| created timestamp | timestamp | Required | Policy creation time |

A Curation rubric narrows operator judgment consistently but MUST NOT weaken or replace this specification.

### Quick-key audit event

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| audit event ID | string | Required; unique and append-only | Durable audit identity |
| event type | enum | classify, clear, skip, undo, article selection, warning acknowledgment, or release confirmation | State-changing question type |
| input mechanism | enum | cockpit key or scriptable command | How the answer was supplied |
| target evidence | map | Required; exact artifact/passage identities and displayed primary text | Evidence shown to the operator |
| display state | map | Required; compact or expanded plus context identities and decision hierarchy | Additional evidence visible at answer time |
| question identity and text | map | Required; typed identity and exact displayed wording | Question answered |
| input and semantic answer | map | Required; key or command value plus answer code and displayed label | Exact answer |
| scope and affected passages | map | Required | Actual decision scope and complete affected identity set |
| curation rubric version | string | Required for classification actions | Applied policy identity |
| resulting record identity | string | Optional only for non-committing skip | Decision, selection, or release identity produced |
| operator label | string | Required | Authorship label |
| timestamp | timestamp | Required | Event time |
| supersedes or undo target | string | Optional | Earlier event affected by reversal |

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
| release ID | string | Required; unique and deterministically generated from source, extractor, selected-artifact, and included-passage identities | Machine-stable content-inventory identity |
| release label | string | Required; operator supplied and human-readable | Semantic operator reference such as source and release version |
| created timestamp | timestamp | Required | Manifest creation time |
| acquisition identity | string | Exactly one accepted acquisition | Reviewed artifact-set boundary |
| source snapshot identity | map | Exactly one wiki database, dump run, and filename | Homogeneous source boundary |
| extractor identity | string | Exactly one parser and package-owned extractor implementation identity | Homogeneous extraction boundary |
| extractor configuration | map | Exactly one complete configuration | Homogeneous extraction boundary |
| selected article artifacts | list | One or more unique, fully reviewed artifact IDs | Explicit article-level release selection |
| included article artifacts | list | Exactly the selected artifacts; unique | Artifacts containing included passages |
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

### Curation rubric policy

1. The operator MUST select one current Curation rubric before recording a classification decision.
2. A passage containing substantive Internal lore and substantive external content MUST be classified under a non-lore category for the whole paragraph; predominant content MUST NOT make it release-eligible.
3. When multiple non-lore classifications apply, precedence MUST be Adaptation material, then Analysis or reception, then External creation history, then Reference or administrative material.
4. Minimal framing that only identifies a fictional source or character MAY coexist with Internal lore; substantive publication, interpretation, creation, or adaptation claims MUST NOT.
5. In-world meanings and relationships among fictional names or languages MAY be Internal lore; Tolkien’s invention or revision process is External creation history, and scholarly proposed connections are Analysis or reception.
6. Alternate in-world accounts MAY each be Internal lore when uncertainty remains explicit; drafting, revision, abandonment, or publication history is External creation history.
7. A heading path is evidence, not classification authority; the system MUST NOT automatically classify from headings.
8. The initial curation pass MUST NOT pre-highlight heading-rule or model-generated answers.
9. An editorial rubric clarification MAY preserve prior decisions. A material change MUST identify potentially affected prior decisions as stale; when impact cannot be bounded, every prior decision under the predecessor rubric becomes stale.
10. Stale decisions MUST remain retained but MUST be explicitly re-answered under the current rubric before their article may enter a release.

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
5. Every saved decision MUST record the configured operator label, timestamp, and current Curation rubric version.
6. Every state-changing answer and its Quick-key audit event MUST become durable atomically; a decision without its audit event or an audit event without its resulting decision is invalid.
7. Clear and undo MUST create explicit superseding decisions; when no prior classification existed, undo MUST create a clear action so parent inheritance resumes.
8. The system MUST retain superseded decisions and audit events so undo and history inspection do not erase prior actions.
9. Classification MUST NOT alter article artifacts or extracted-passage source fields.
10. Scriptable classification and supersession commands MUST synthesize and persist the same typed question, displayed wording, semantic answer, scope, evidence, and audit relationship as the equivalent cockpit action.

### Conflicting and uncertain accounts

The system MUST preserve each extracted paragraph’s source wording and independent classification. It MUST NOT require conflict groups, choose a “canon” account, or reconcile disagreements. If multiple conflicting passages are internal lore, each MAY enter the release independently; response policy owns any later explanation of uncertainty.

### Curation cockpit

The package-owned interactive review command MUST implement the approved [Curation cockpit](DESIGN_LANGUAGE.md#operator-cli):

1. The default frame MUST show only review progress, article and heading location, current passage text, exact classification question, target scope, effective classification, and current rubric version.
2. Classification keys MUST remain stable:
   - `1` — Internal lore;
   - `2` — External creation history;
   - `3` — Analysis or reception;
   - `4` — Adaptation material; and
   - `5` — Reference or administrative material.
3. Paragraph MUST be the default target scope, including after a Section-scope bulk decision.
4. A classification key MUST save its decision and audit event without requiring Enter and advance immediately.
5. Paragraph scope MUST advance to the next paragraph.
6. Section scope MUST visibly state the affected-passage count, classify on one key without a second confirmation, then advance to the first passage in the next section and restore Paragraph scope.
7. Page scope MUST visibly state the affected-passage count, classify on one key without a second confirmation, and transition to the end-of-pass summary.
8. `x` MUST skip the current passage without adding a Curation decision but MUST append an audited skip answer.
9. `u` MUST undo the latest decision, preserve supersession and audit history, and return to the affected passage for immediate reclassification.
10. `m` MUST toggle [Expanded instruments](DESIGN_LANGUAGE.md#operator-cli) containing neighboring context, raw wikitext, decision hierarchy, page/revision/passage identities, and less-common bulk controls.
11. A state-changing audit event MUST record whether Expanded instruments were visible, the resolved context identities, and the exact primary passage text; navigation and detail toggles do not require audit events.
12. One Section- or Page-scope action MUST create one truthful scoped audit event listing every affected passage and its before/after effective classification; it MUST NOT fabricate independent paragraph decisions.
13. The cockpit MUST save every accepted decision and audit event durably before advancing.
14. Restarting review MUST offer the first effectively undecided or stale passage while permitting explicit navigation elsewhere.

The terminal interaction MAY use color, but scope, classification, progress, and controls MUST remain understandable without color.

### End-of-pass summary

1. Reaching the final passage through classification or skip MUST replace the review frame with an [End-of-pass summary](DESIGN_LANGUAGE.md#operator-cli).
2. The summary MUST be visually and textually distinct from passage review and MUST NOT rely on color alone.
3. It MUST report counts for all five classifications plus effectively undecided and stale passages.
4. It MUST state either that every passage is current and classified or that passages need attention.
5. An optional detail view MUST list each passage’s effective classification and source scope.
6. Undo from the summary MUST reverse the latest decision and return to its passage.
7. Resume from the summary MUST move to the first stale passage, then the first effectively undecided passage, when either exists.
8. The summary is operator feedback, not release validation.

### Scriptable command surface

Package-owned non-interactive commands MUST support:

- listing acquired candidates and article artifacts;
- showing undecided, stale, and effective classifications;
- inspecting and selecting a Curation rubric version;
- applying or superseding a decision at a specified scope with atomic audit evidence;
- inspecting quick-key audit history;
- selecting fully reviewed articles and previewing a proposed release body;
- validating and creating a release;
- listing releases and active status;
- activating and rolling back releases; and
- returning deterministic command results suitable for operator inspection and automation.

Command names, flags, CLI framework, and artifact serialization are implementation choices.

### Manifest assembly

1. The operator MUST answer an audited Include-or-Exclude question for each fully reviewed Article artifact considered for a proposed release.
2. A selected artifact MUST have zero effectively undecided passages, zero stale decisions, unambiguous decision history, and complete audit relationships.
3. Every effectively Internal lore passage from each selected artifact MUST enter the proposed manifest; the operator MUST NOT cherry-pick individual Lore passages from a selected artifact.
4. A selected artifact MUST contribute at least one Lore passage, but no higher per-article passage minimum applies.
5. The manifest MUST include exactly the selected article artifacts and no unreferenced artifact.
6. Every included artifact MUST share one accepted acquisition, source snapshot identity, extractor identity, and extractor configuration.
7. A release outside the 25–50-article target MUST produce a prominent warning and audited operator acknowledgment but MUST NOT be rejected for count alone.
8. Release ID MUST be generated deterministically from the acquisition, source, extractor, selected-artifact, and included-passage identities; it MUST exclude the generated ID, release label, and creation timestamp from its identity input, while the operator supplies the distinct human-readable release label.
9. Creating a release MUST present an audited final confirmation naming the proposed label and identity, then snapshot the included IDs into a new immutable manifest; later curation changes MUST NOT mutate it.
10. Exclusion inventories, curation decisions, audit events, and free-text rationale MUST remain outside the included-content manifest.

### Release validation

A release MUST be valid only when all of these conditions hold:

| Condition | Required validation result |
|-----------|----------------------------|
| Release label is absent, release identity is not the deterministic result, or identity duplicates an existing release | Invalid |
| Included passage count is below `MINIMUM_RELEASE_PASSAGE_COUNT` | Invalid |
| Selected artifact is missing, contributes no Lore passage, has an undecided passage, or has a stale decision | Invalid |
| Included artifact set differs from selected artifact set | Invalid |
| Any effective Internal lore passage from a selected artifact is absent, or any non-lore passage is present | Invalid |
| Referenced artifact or passage is missing | Invalid |
| Duplicate artifact or passage ID exists | Invalid |
| Source snapshot, accepted acquisition, or extractor configuration is mixed | Invalid |
| A governing decision lacks an atomic audit event or has ambiguous supersession history | Invalid |
| Article-count warning or final creation confirmation lacks its required audit event | Invalid |
| Every identity resolves and all conditions above pass | Valid |

Validation does not require checksums, content digests, an exclusion inventory, a retrieval index, free-text rationale, or conformance to the target page count.

### Release completion evidence

1. Corpus release validity MUST remain independent of backup creation or verification.
2. The first-release project milestone MUST NOT be reported complete until the operator creates and verifies one deterministic backup containing source and discovery records, accepted acquisition artifacts and acceptance evidence, extraction review findings and audit events, Curation decisions and audit events, every governing Curation rubric version, and the immutable Corpus release manifest and identity.
3. Backup verification MUST reject missing or inconsistent required evidence and MUST preserve the distinction between a valid release and an incomplete milestone backup.
4. Superseded acquisition v1 MAY remain through its immutable Git tag and one verified historical backup, but it MUST NOT occupy active canonical corpus paths after corrected acquisition acceptance.
5. Full application-state backup, restore, and hosted recovery behavior remains owned by [Private Demo Access and Operations](private-demo-access-and-operations.md#persistent-data-and-recovery).

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
3. Every release, manifest, required article artifact, governing Curation decision, Curation rubric version, and Quick-key audit event MUST remain retained until every dependent release is manually deleted.
4. The active release MUST NOT be deleted.
5. Deleting an inactive release MUST identify blocking shared review evidence and derived retrieval indexes that may also be removed, while index deletion semantics remain owned by Spec 3.
6. No supporting review or audit record MAY be independently deleted while a retained release depends on it.
7. No automatic age, count, or storage-based cleanup is required.

### Offline boundary

Curation, audit inspection, article selection, release creation, validation, activation, rollback, and deletion MUST occur through offline operator commands. This system MUST NOT provide browser curation, reviewer accounts, approval queues, background corpus jobs, web-request mutation, or a public corpus-management API.

## Error Handling

### Missing operator label

- **Trigger:** A cockpit or scriptable command attempts to create a state-changing Curation decision, selection, confirmation, or audit event without a non-empty operator label.
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

### Incremental save or audit failure

- **Trigger:** The cockpit or scriptable command cannot atomically persist a state-changing answer and its authoritative record or Quick-key audit event.
- **Detection:** Persistence does not confirm the complete atomic relationship before advancement or command success.
- **Response:** Preserve prior state, remain on the current question when interactive, report the failure prominently, and MUST NOT show either record as saved.
- **Recovery:** Correct the storage problem and answer the same question again.

### Undo failure

- **Trigger:** No prior decision exists or a superseding restoration cannot be persisted.
- **Detection:** History is empty or durable write fails.
- **Response:** Preserve current decisions and cursor; report why undo was not performed.
- **Recovery:** Continue review or correct persistence and retry.

### Stale or incomplete selected article

- **Trigger:** A proposed selected artifact contains an undecided passage, stale decision, ambiguous history, missing governing audit event, or no Lore passage.
- **Detection:** Article-selection preview and complete release validation inspect every passage and governing relationship.
- **Response:** Reject article selection or invalidate the proposed release without altering retained decisions.
- **Recovery:** Complete or re-answer curation under the current rubric, repair audit relationships through a new explicit answer, or leave the article unselected.

### Invalid manifest

- **Trigger:** One or more release-validation conditions fail.
- **Detection:** Complete validation reports every detected condition.
- **Response:** Do not create a valid release or alter active status.
- **Recovery:** Correct curation, audit completeness, article selection, or manifest assembly and create a new candidate manifest.

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
- Audit viewers SHOULD resolve immutable evidence references while preserving the exact primary passage text captured at answer time.
- Deterministic model-training exports MAY be derived from current effective decisions and audit history, but extraction findings, skips, superseded answers, question text, and answer text MUST NOT be treated as model inputs or current labels.
- Evaluation splits for any later classifier SHOULD separate whole Article artifacts rather than random passages.
- Release manifests SHOULD be inspectable as ordinary package-owned artifacts.
- The one-operator assumption removes authorization and quorum behavior; it does not permit silent mutation of immutable releases.

## Test Scenarios

| ID | Category | Priority | Preconditions | Exact input | Observable expected output |
|----|----------|----------|---------------|-------------|----------------------------|
| `TS-CCR-001` | Inheritance | Critical | Article has three sections and no decisions | Page classification `Internal lore` | Every passage is effectively Internal lore from page scope |
| `TS-CCR-002` | Override | Critical | Page is Internal lore | Section classification `External creation history`, then one paragraph classification `Internal lore` | Section descendants are creation history except the explicit lore paragraph |
| `TS-CCR-003` | Undecided | Critical | One selected article has a passage with no page, section, or paragraph decision | Assemble release | Proposed release is invalid and the undecided passage is never included |
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
| `TS-CCR-017` | Mixed content | Critical | One paragraph contains lore plus substantive film analysis | Classify under current rubric | Whole passage is Adaptation material and is release-ineligible |
| `TS-CCR-018` | Classification precedence | High | One paragraph analyzes an adaptation and discusses its publication | Answer classification question | Adaptation material wins and exact rubric/question/answer evidence is auditable |
| `TS-CCR-019` | Atomic audit | Critical | Audit persistence rejects a write | Press `1` on a passage | Neither decision nor audit event persists and cockpit does not advance |
| `TS-CCR-020` | Bulk truthfulness | High | Section has five passages and Paragraph is default scope | Select Section scope and press `2` | One scoped decision and one audit event list all five affected passages; cockpit advances and restores Paragraph scope |
| `TS-CCR-021` | Rubric revision | Critical | Prior decisions use rubric A | Material rubric B cannot bound affected rules | Every decision under A becomes stale and selected articles are blocked until re-answered |
| `TS-CCR-022` | Complete article | Critical | Selected article has one undecided passage | Validate release | Release is invalid even though the undecided passage would otherwise be excluded |
| `TS-CCR-023` | Complete inclusion | Critical | Selected article has three effective Lore passages | Assemble proposed manifest while attempting to omit one | Assembly or validation rejects the body and requires all three passages |
| `TS-CCR-024` | Article target | Medium | Valid selected set contains 24 articles | Acknowledge warning and create release | Count warning and acknowledgment are audited; count alone does not invalidate release |
| `TS-CCR-025` | Release identity | High | One immutable body and semantic label exist | Assemble twice | Both previews produce the same machine identity and display the same release label |
| `TS-CCR-026` | Audit retention | Critical | Retained release depends on decision, rubric, and audit records | Delete one supporting record | Deletion is rejected and identifies the blocking release |
| `TS-CCR-027` | Completion backup | High | Valid first release exists but no complete verified backup exists | Inspect project milestone status, then verify a backup missing one audit event | Release remains valid, milestone remains incomplete, and backup verification fails with the missing evidence |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-07-23 | Added versioned curation policy, conservative mixed-content rules, atomic question-answer audit, complete-article selection, deterministic release identity, stronger validation, and audit retention |
| 1.0.0 | 2026-07-18 | Authored and approved hierarchical curation, cockpit, release, activation, rollback, and retention contracts |
| 0.1.0 | 2026-07-18 | Initial skeleton |
