# Product glossary

This is the ubiquitous language for Middle-earth Travel Agency. Product
documents, code, tests, and interfaces should use these terms consistently when
they refer to the domain concepts below.

The glossary defines shared meaning, not every implementation name. A local
class, database table, command flag, or UI helper does not need an entry unless
its meaning crosses capability boundaries.

## Product and audience

| Term | Meaning |
|---|---|
| **Middle-earth Travel Agency** | The noncommercial fan demo through which invited travelers plan imagined Third Age journeys and produce personalized travel guides. |
| **Invited traveler** | A person admitted through the shared demo credential to use travel consultations. An invited traveler is not an account holder. |
| **Tolkien newcomer** | The initial audience member for whom consultations and guides favor accessible orientation over assumed prior lore knowledge. |
| **Operator** | The single developer who acquires, reviews, releases, indexes, evaluates, and operates the initial demo corpus. |
| **Tolkien lore** | Fictional-world information about Tolkien's setting and chronology supported by approved internal-lore passages in this demo. It does not mean LOTRO state or an assertion of canon. |

## Consultations and generation

| Term | Meaning |
|---|---|
| **Travel consultation** | A server-owned, persistently addressable conversation in which a traveler and the agency develop a trip brief, explore relevant lore, and generate or revise a travel guide. |
| **Trip brief** | The accepted planning context for a guide, including its temporal frame, traveler perspective, origin, destination or experience, interests, constraints, and explicit assumptions. |
| **Generation attempt** | One server-side execution initiated to produce or replace an agency message or create a guide revision. |
| **Agency message** | A persisted, user-visible conversational response produced by a successful generation attempt. It may clarify the trip, answer a planning-relevant lore question, or prepare guide generation. |
| **Guidance answer** | An agency message that responds to a planning or lore question with supported grounded claims, useful qualification, or an abstention. It is not itself a travel guide. |
| **Grounded claim** | An independently verifiable factual statement supported by retrieved lore passages from the associated corpus release. |
| **Abstention** | An explicit refusal to make an unsupported factual claim because retrieved evidence is insufficient. |
| **Cancellation** | A traveler request to stop the active generation attempt, propagated to backend work on a best-effort basis. It is not deletion or pause. |
| **Incomplete output** | Streamed text left by a failed or cancelled attempt, visibly marked and excluded from future accepted consultation context. |
| **Retry** | A new generation attempt that replaces failed or cancelled visible output while preserving prior attempt history. |

## Travel guides

| Term | Meaning |
|---|---|
| **Middle-earth travel guide** | The primary structured artifact produced from a trip brief and associated with its travel consultation. It combines in-world guidance with an inspectable editorial layer. |
| **Guide revision** | One immutable completed version of a travel guide. A material change produces a new revision rather than rewriting a prior one. |
| **Temporal frame** | The stated date, range, or supportable period within the Third Age that bounds what a guide treats as contemporaneously true. The Third Age by itself is not sufficiently narrow. |
| **Traveler perspective** | The stated in-world viewpoint from which the guide evaluates knowledge, welcome, access, pace, and risk. It is traveler-configurable with a generic traveler as the fallback. |
| **Journey leg** | One meaningful portion of a proposed route. It does not imply an exact day or canonical travel duration. |
| **Travel inference** | Plausible route, duration, provisioning, lodging, risk, or itinerary synthesis derived from grounded lore but not directly stated by it. It is visibly labeled and conservatively expressed. |
| **In-world guide** | The immersive, traveler-facing portion of a guide, written as practical advice appropriate to its temporal frame and traveler perspective. |
| **Editorial layer** | The out-of-world guide structure that exposes citations, travel inference, uncertainty, assumptions, provenance, and attribution without pretending those elements are in-world knowledge. |

## Evidence and attribution

| Term | Meaning |
|---|---|
| **Retrieved evidence** | Lore passages returned to a generation attempt for possible support. Retrieval does not itself prove that every result supports a claim. |
| **Citation** | A user-visible connection from a grounded claim to supporting passage context and exact Wikipedia revision provenance. |
| **Guide source list** | The consolidated set of cited Wikipedia revisions presented with a guide in addition to claim-level citations. It does not imply that every source supports every statement. |
| **Attribution notice** | The license treatment that credits Wikipedia contributors, links the applicable revision and license, and identifies modifications made by Middle-earth Travel Agency. |
| **Provenance** | The retained chain from source snapshot and revision through extraction, curation, release, retrieval, and claim support. It is not an internal file path. |

## Corpus

| Term | Meaning |
|---|---|
| **Source snapshot** | A fixed official Wikimedia dump identified by wiki database, dated run, exact filename, and dated source URL. |
| **Candidate article** | A namespace-zero English Wikipedia page proposed for review but not yet admitted to a corpus release. |
| **Canonical target preview** | The redirect-resolved and deduplicated candidate view the operator approves or revises before accepting an acquisition. |
| **Accepted acquisition** | One homogeneous source-and-extractor artifact set whose automated checks, canonical targets, and sampled extraction review have passed. |
| **Article artifact** | An immutable package-owned record of one pinned Wikipedia page revision and extraction configuration, including raw wikitext, prose passages, source identity, and redirect provenance. |
| **Extracted passage** | A stably identified prose paragraph produced deterministically from an article artifact and available for review and classification. |
| **Extraction review finding** | The operator's pass, flag, or skip judgment about whether an extracted passage or structural exclusion conforms to the acquisition policy. It is not a curation decision. |
| **Passage classification** | One of internal lore, external creation history, analysis or reception, adaptation material, or reference or administrative material. |
| **Lore passage** | An extracted passage whose effective classification is internal lore and which is therefore eligible for release and retrieval. |
| **Curation decision** | An operator judgment at article, section, or passage scope under a specific curation-rubric version. |
| **Curation rubric** | The versioned operator policy used to apply passage classifications consistently. |
| **Review audit event** | An append-only record of the evidence shown, question asked, and semantic answer supplied for a state-changing acquisition or curation judgment. |
| **Corpus release manifest** | The authoritative immutable inventory of article artifacts and lore passages in one corpus release. |
| **Corpus release** | An immutable, validated, versioned body of curated lore passages defined by one manifest. |
| **Active corpus release** | The one validated release selected by the operator for runtime retrieval. |
| **Lore corpus** | The curated body of approved lore passages available through the active corpus release. |
| **Retrieval index** | A disposable and rebuildable search projection derived from a corpus release, not an authoritative source. |

## Evaluation

| Term | Meaning |
|---|---|
| **Evaluation case** | A human-authored and reviewed consultation prompt or trip brief with expectations for clarification, support, synthesis, abstention, inference labeling, or guide quality. |
| **Evaluation suite** | The curated collection of evaluation cases used to assess the private demo. |
| **Retrieval ablation** | A controlled comparison of normal retrieval and retrieval disabled for the same evaluation case. |
| **Output pair** | The randomized left/right presentation of the two outputs from one retrieval ablation. |
| **Blinded evaluation review** | An owner-only human assessment of an output pair before either retrieval condition is revealed. |
| **Evaluation verdict** | `left better`, `tie`, `right better`, or `both fail`, optionally accompanied by notes and tags. |

## Relationships

- A travel consultation contains generation attempts and successful agency
  messages, with at most one active attempt at a time.
- A trip brief is developed within a travel consultation and supplies the
  accepted planning context for guide generation.
- A successful generation attempt may create an agency message or a guide
  revision; a failed or cancelled attempt may leave incomplete output instead.
- A travel consultation may have multiple guide revisions and identifies one
  as the current guide.
- Every agency message and guide revision is associated with the corpus release
  used for its evidence.
- Every grounded claim has one or more citations to supporting lore passages.
- A corpus release is built from lore passages admitted through one accepted
  acquisition and current curation decisions.
- A corpus release may have multiple rebuildable retrieval indexes but only one
  immutable manifest.
- A retrieval ablation produces one output pair for blinded evaluation review.

## Evolving the language

Change this glossary when a domain concept is introduced, removed, or given a
materially different meaning. Do not update it for ordinary identifier renames.
Unresolved meanings belong in [open questions](open-questions.md) until there
is enough evidence to choose deliberately.
