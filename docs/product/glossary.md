# Product glossary

This is the ubiquitous language for the Halls of Knowledge product. Product
documents, code, tests, and interfaces should use these terms consistently when
they refer to the domain concepts below.

The glossary defines shared meaning, not every implementation name. A local
class, database table, command flag, or UI helper does not need an entry unless
its meaning crosses capability boundaries.

## Product and audience

| Term | Meaning |
|---|---|
| **Halls of Knowledge** | The private chat demo through which invited visitors ask Tolkien-lore questions and explicitly request guide messages. |
| **Invited visitor** | A person admitted through the shared demo credential to use lore conversations. An invited visitor is not an account holder. |
| **Tolkien newcomer** | The initial audience member for whom answers favor accessible explanation over assumed prior lore knowledge. |
| **Operator** | The single developer who acquires, reviews, releases, indexes, and operates the initial demo corpus. |
| **Tolkien lore** | Fictional-world information about Tolkien's setting and chronology supported by approved internal-lore passages in this demo. It does not mean LOTRO state or an assertion of canon. |

## Conversations and responses

| Term | Meaning |
|---|---|
| **Conversation** | A server-owned, persistently addressable sequence of visitor messages, assistant messages, and generation-attempt history. |
| **Generation attempt** | One server-side execution initiated to produce or replace an assistant message. |
| **Assistant message** | A persisted, user-visible response produced by a successful generation attempt and associated with the corpus release that grounded it. |
| **Lore answer** | An assistant message that responds to a lore question with supported grounded claims or an abstention. |
| **Grounded claim** | An independently verifiable factual statement supported by retrieved lore passages from the associated corpus release. |
| **Abstention** | A lore answer that explicitly declines to make an unsupported factual claim because retrieved evidence is insufficient. |
| **Guide message** | A structured assistant message produced only after explicit request or confirmation and bounded by a temporal frame and traveler perspective. |
| **Temporal frame** | The stated Age and, when supportable, date that bounds what a guide message treats as contemporaneously true. |
| **Traveler perspective** | The stated in-world viewpoint from which a guide describes available knowledge and an itinerary. |
| **Itinerary inference** | Plausible route-related synthesis supported by lore passages but not directly stated by them, visibly labeled as inference. |
| **Cancellation** | A visitor request to stop the active generation attempt, propagated to backend work on a best-effort basis. It is not deletion or pause. |
| **Incomplete output** | Streamed text left by a failed or cancelled attempt, visibly marked and excluded from future assistant context. |
| **Retry** | A new generation attempt that replaces failed or cancelled visible output while preserving prior attempt history. |

## Evidence and attribution

| Term | Meaning |
|---|---|
| **Retrieved evidence** | Lore passages returned to a generation attempt for possible support. Retrieval does not itself prove that every result supports a claim. |
| **Citation** | A user-visible connection from a grounded claim to supporting passage context and exact Wikipedia revision provenance. |
| **Source list** | The consolidated set of cited Wikipedia revisions presented with a guide message in addition to claim-level citations. |
| **Attribution notice** | The license treatment that credits Wikipedia contributors, links the applicable revision and license, and identifies modifications made by Halls of Knowledge. |
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
| **Evaluation case** | A human-authored and reviewed prompt with expectations for support, synthesis, abstention, guide generation, or resistance to unsupported model knowledge. |
| **Evaluation suite** | The curated collection of evaluation cases used to assess the private demo. |
| **Retrieval ablation** | A controlled comparison of normal retrieval and retrieval disabled for the same evaluation case. |
| **Output pair** | The randomized left/right presentation of the two outputs from one retrieval ablation. |
| **Blinded evaluation review** | An owner-only human assessment of an output pair before either retrieval condition is revealed. |
| **Evaluation verdict** | `left better`, `tie`, `right better`, or `both fail`, optionally accompanied by notes and tags. |

## Relationships

- A conversation contains generation attempts and successful assistant messages,
  with at most one active attempt at a time.
- A successful generation attempt creates an assistant message; a failed or
  cancelled attempt may leave incomplete output instead.
- Every assistant message is associated with the corpus release used for its
  evidence.
- Every grounded claim has one or more citations to supporting lore passages.
- A corpus release is built from lore passages admitted through one accepted
  acquisition and current curation decisions.
- A corpus release may have multiple rebuildable retrieval indexes but only one
  immutable manifest.
- A retrieval ablation produces one output pair for blinded evaluation review.

## Evolving the language

Change this glossary when a domain concept is introduced, removed, or given a
materially different meaning. Do not update it for ordinary identifier renames.
Unresolved meanings belong in [open questions](open-questions.md) until there is
enough evidence to choose deliberately.

