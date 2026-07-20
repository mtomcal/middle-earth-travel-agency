# Spec-of-Specs: Halls of Knowledge Documentation Blueprint

> **Version**: 1.0.0
> **Last Updated**: 2026-07-18
> **Purpose**: Define the structure, content requirements, and review rules for every specification in `specs/`.
> **Target Audience**: AI agents and human reviewers defining or implementing Halls of Knowledge from an approved behavior contract.

---

## Suite status

The nine system specifications begin as version `0.1.0` skeletons and are not implementation authority until their behavior is authored, reviewed, and promoted to `1.0.0`. The approved [Ubiquitous Language](UBIQUITOUS_LANGUAGE.md) is the canonical terminology authority even while system specs remain skeletons.

## Document conventions

### Formatting standards

- Every specification MUST use GitHub-flavored Markdown.
- `#` MUST identify the document title, `##` a required major section, and `###` a behavior, structure, error, or scenario subsection.
- Tables SHOULD express schemas, parameters, decision rules, and other structured contracts.
- Fenced blocks without a language identifier MAY express language-agnostic pseudocode.
- Relative links MUST use descriptive text and SHOULD include a section anchor when referencing one rule.
- Canonical domain terms MUST match [UBIQUITOUS_LANGUAGE.md](UBIQUITOUS_LANGUAGE.md).
- Interface terms MUST match [DESIGN_LANGUAGE.md](DESIGN_LANGUAGE.md).

### Prescriptive language

Authored system specs are behavior contracts and MUST use prescriptive language such as “The system MUST…”, “MUST NOT…”, “SHOULD…”, and “MAY…”. They MUST NOT describe an implementation merely because it currently exists.

### Required sections

Every system spec MUST contain these sections in this order:

1. **Overview** — responsibility, boundary, and design motivation.
2. **Dependencies** — technology and specification dependencies.
3. **Parameters** — referenced tuning values and their rationale.
4. **Data Structures** — language-agnostic entities and fields.
5. **Behavior** — rules, state transitions, pseudocode, and decision tables.
6. **Error Handling** — trigger, detection, response, and recovery for each error.
7. **Implementation Notes** — language-agnostic constraints and edge cases.
8. **Test Scenarios** — acceptance behavior using canonical scenario identifiers.
9. **Changelog** — every version and its reviewable change.

Authoring guidance in a skeleton MUST be removed or replaced when the section becomes authoritative.

## Language-agnostic policy

Specifications MUST NOT contain implementation code, implementation-source paths, or references to internal source files. They MAY contain:

- plain-language pseudocode;
- schema tables using plain-language types;
- state and decision tables;
- public standards, external source identifiers, and specification cross-references; and
- technology dependencies when a confirmed product constraint requires them.

Implementation-specific examples belong outside the specification suite.

## Structure formats

### Schema table

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| field name | plain-language type | required limits and invariants | domain meaning and lifecycle role |

Types SHOULD use `string`, `integer`, `decimal`, `boolean`, `timestamp`, `enum`, `map`, `list`, or another language-independent name.

### Decision table

| Condition | Required action |
|-----------|-----------------|
| Precisely stated condition | Observable system response |

Every overlapping condition MUST have an explicit precedence rule, and uncovered conditions MUST be identified as errors or intentional no-ops.

### Error contract

Each error subsection MUST provide:

- **Trigger** — the condition that creates the error;
- **Detection** — how the system identifies it;
- **Response** — the required immediate behavior; and
- **Recovery** — the permitted route back to a valid state.

## Parameters

[parameters.md](parameters.md) is the single suite authority for tuning values, limits, timeouts, target ranges, and configuration selections. Every parameter MUST include a rationale that explains why the value exists and what risk a change introduces. A system spec MUST link to the authoritative parameter rather than silently duplicate a value.

An unresolved value MUST remain visibly `TBD`, identify the owning spec, and explain why selecting it without evidence would be premature.

## Test scenarios

Scenario identifiers MUST use `TS-{PREFIX}-{NUMBER}` where:

- `PREFIX` is the registered 2–6 character system abbreviation;
- `NUMBER` is a zero-padded three-digit sequence beginning at `001`; and
- identifiers are never reused after publication.

| System | Prefix |
|--------|--------|
| Corpus Acquisition and Provenance | `CAP` |
| Corpus Curation and Releases | `CCR` |
| Corpus Retrieval and Agent Tools | `RET` |
| Lore Agent and Response Policy | `AGENT` |
| Evidence Presentation and Attribution | `EVID` |
| Conversation and Attempt Lifecycle | `LIFE` |
| Web Experience | `WEB` |
| Evaluation and Review | `EVAL` |
| Private Demo Access and Operations | `OPS` |

Each authored scenario MUST state category, priority, preconditions, exact inputs, and observable expected outputs. Content authoring creates each system’s actual scenario index; skeleton guidance does not count as an authored scenario.

## Cross-reference conventions

- A specification dependency MUST appear both in document metadata and under **Spec Dependencies**.
- `Depends On` means the current system consumes a behavior or contract owned by the linked specification.
- `Depended By` is navigational and MUST agree with the dependency graph in [README.md](README.md).
- Orthogonal operational support MAY use a dashed graph edge and does not reverse domain ownership.
- Cross-references MUST point to existing relative files and valid headings.

## Vocabulary preambles

- [UBIQUITOUS_LANGUAGE.md](UBIQUITOUS_LANGUAGE.md) is the sole canonical domain glossary.
- [DESIGN_LANGUAGE.md](DESIGN_LANGUAGE.md) is the shared interface vocabulary and interaction preamble.
- Vocabulary files are not substitutes for behavior contracts.
- Glossary evolution MUST use the `ubiquitous-language` workflow and preserve flagged ambiguities instead of silently deciding them.

## Versioning policy

- `0.1.0` identifies a scaffold whose requirements are not yet authoritative.
- `1.0.0` identifies the first fully authored and human-approved behavior contract.
- A patch increment clarifies behavior without changing its contract.
- A minor increment adds backward-compatible requirements, scenarios, or parameters.
- A major increment changes a behavior, data, or interface contract incompatibly.
- Every version change MUST appear in the document changelog.

## Authoring quality gates

Before a system spec may become `1.0.0`, reviewers MUST verify:

- every required section is complete and guidance prompts are removed;
- every behavior is prescriptive and has acceptance coverage;
- every parameter is centralized and justified;
- every error has detection, response, and recovery rules;
- all relative links and dependency declarations resolve;
- terminology follows the canonical glossary;
- known ambiguities are resolved explicitly or remain visibly flagged;
- no implementation code, implementation-source path, or inferred implementation detail appears; and
- the spec has explicit human approval.
