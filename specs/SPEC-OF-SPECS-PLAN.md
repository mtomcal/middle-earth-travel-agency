# Spec-of-Specs Authoring Plan

> **Version**: 0.3.0
> **Created**: 2026-07-18
> **Mode**: Greenfield
> **Purpose**: Track progress on authoring and approving the Halls of Knowledge specification suite.
> **Boundary**: This is a specification-authoring tracker, not an implementation plan, execution ledger, or implementation task graph.

---

## Authoring status

### Phase 1: Language and parameters

| Spec File | Status | Lines | Notes |
|-----------|--------|-------|-------|
| [UBIQUITOUS_LANGUAGE.md](UBIQUITOUS_LANGUAGE.md) | **Approved baseline** | — | Added acquisition review, rubric, and question-answer audit terminology |
| [DESIGN_LANGUAGE.md](DESIGN_LANGUAGE.md) | **Draft; operator slice approved** | — | Acquisition and curation cockpit interactions are approved; web visual direction remains unresolved |
| [parameters.md](parameters.md) | **Draft; corpus values approved** | — | Added canonical acquisition-pool and deterministic review-sampling values; unrelated selections remain `TBD` |

### Phase 2: Corpus foundation

| Spec File | Status | Lines | Notes |
|-----------|--------|-------|-------|
| [corpus-acquisition-and-provenance.md](corpus-acquisition-and-provenance.md) | **Approved 2.0.0** | — | Strict extraction, deterministic sampled review, atomic audit, and acquisition acceptance authored |
| [corpus-curation-and-releases.md](corpus-curation-and-releases.md) | **Approved 2.0.0** | — | Versioned rubric, conservative classification, atomic audit, complete-article selection, and release lifecycle authored |
| [corpus-retrieval-and-agent-tools.md](corpus-retrieval-and-agent-tools.md) | **Approved 1.0.0** | 288 | Active-corpus SQLite keyword retrieval and two-tool boundary authored |

### Phase 3: Response core

| Spec File | Status | Lines | Notes |
|-----------|--------|-------|-------|
| [lore-agent-and-response-policy.md](lore-agent-and-response-policy.md) | **Skeleton** | 139 | Needs prescriptive authoring and review |
| [evidence-presentation-and-attribution.md](evidence-presentation-and-attribution.md) | **Skeleton** | 123 | Needs prescriptive authoring and review |
| [conversation-and-attempt-lifecycle.md](conversation-and-attempt-lifecycle.md) | **Skeleton** | 135 | Needs prescriptive authoring and review |

### Phase 4: Surfaces and assurance

| Spec File | Status | Lines | Notes |
|-----------|--------|-------|-------|
| [web-experience.md](web-experience.md) | **Skeleton** | 146 | Needs prescriptive authoring and review |
| [evaluation-and-review.md](evaluation-and-review.md) | **Skeleton** | 124 | Needs prescriptive authoring and review |
| [private-demo-access-and-operations.md](private-demo-access-and-operations.md) | **Skeleton** | — | Backup guidance now consumes the approved curation-owned release-completion contract; system behavior still needs prescriptive authoring and review |

## Progress summary

- **System specs**: 9
- **Authored system specs (`1.0.0+`)**: 3
- **System skeletons (`0.1.0`)**: 5
- **Updated system skeletons (`0.2.0`)**: 1
- **Approved vocabulary baselines**: 1
- **Draft design/parameter preambles**: 2

## Required authoring order

1. Corpus Acquisition and Provenance
2. Corpus Curation and Releases
3. Corpus Retrieval and Agent Tools
4. Lore Agent and Response Policy
5. Evidence Presentation and Attribution
6. Conversation and Attempt Lifecycle
7. Web Experience
8. Evaluation and Review
9. Private Demo Access and Operations

Each spec MUST pass the quality gates in [SPEC-OF-SPECS.md](SPEC-OF-SPECS.md#authoring-quality-gates) before promotion to `1.0.0`.

## Cross-cutting decisions to preserve

- Claim granularity and citation placement remain unresolved.
- Raw and normalized article content forms one immutable compound artifact for one revision and extractor configuration.
- Corpus provenance intentionally excludes checksums, content digests, complete XML records, and permanent full-dump retention.
- Runtime retrieval exposes only the active corpus; conversation-lifetime versus attempt-level release association remains unresolved in the lifecycle spec.
- The prospective “evaluation run” term requires the `ubiquitous-language` workflow before adoption.
- Model/provider, attribution placement, AWS packaging, and reverse proxy remain open; parser library, artifact format, CLI framework, tokenizer/weights, and the release-ID encoding algorithm remain implementation choices within the approved deterministic identity inputs.
- Legal review remains required before broad, public, or commercial release.
- Acquisition review findings remain distinct from Curation decisions, and every state-changing review answer requires atomic question-answer audit evidence.
- Selected release articles must be fully classified under a current rubric and contribute every effective Internal lore passage.
- Behavior after a late extraction defect invalidates an accepted acquisition remains unresolved.

## Authoring log

| Date | Spec | What was done |
|------|------|---------------|
| 2026-07-18 | Suite | Initial Greenfield bootstrap, approved glossary migration, design-language preamble, parameters, and nine system skeletons |
| 2026-07-18 | Corpus foundation | Interviewed, prototyped, approved, and authored Specs 1–3; promoted each to 1.0.0 and updated corpus language and parameters |
| 2026-07-23 | Acquisition and curation revision | Approved strict corrected acquisition, separate sampled extraction review, atomic question-answer audit, versioned curation policy, complete-article release selection, and verified release-evidence backup |
