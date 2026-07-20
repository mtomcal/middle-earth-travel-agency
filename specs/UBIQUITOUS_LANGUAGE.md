# Ubiquitous Language

> **Version**: 0.2.0
> **Last Updated**: 2026-07-18
> **Purpose**: Canonical shared vocabulary for all Halls of Knowledge specifications; read this before any system spec.

---

This glossary governs the initial **Halls of Knowledge** bounded context: a private, Wikipedia-backed Tolkien-lore chat demo for invited newcomers. LOTRO game mechanics and current game state, experienced-reader behavior, spoiler policy, public account management, and later corpus sources belong outside this context unless a future specification explicitly introduces them.

## Product and audience

| Term | Definition | Aliases to avoid |
|------|------------|------------------|
| **Halls of Knowledge** | Halls of Knowledge is the private chat demo through which invited visitors ask Tolkien-lore questions and explicitly request structured guide messages. | LOTRO companion, public Tolkien chatbot |
| **Invited visitor** | An invited visitor is a person admitted through the demo's shared credential to use its lore conversations. | account holder, customer, player |
| **Tolkien newcomer** | A Tolkien newcomer is the initial audience member for whom answers favor accessible explanation over assumed prior lore knowledge. | novice player, LOTRO player |
| **Operator** | The operator is the single developer who uses package-owned offline commands to acquire, curate, release, and index the demo corpus. | corpus owner, reviewer account, curator service |
| **Tolkien lore** | Tolkien lore is fictional-world information about Tolkien's setting and chronology that is supported by approved internal-lore passages in this demo. | Middle-earth facts, LOTRO lore, canon |

## Conversation and response lifecycle

| Term | Definition | Aliases to avoid |
|------|------------|------------------|
| **Conversation** | A conversation is a server-owned, persistently addressable sequence of visitor messages, assistant messages, and their generation-attempt history. | chat session, thread, client session |
| **Assistant message** | An assistant message is a persisted user-visible response produced by a successful generation attempt and associated with the corpus release that grounded it. | model output, completion |
| **Lore answer** | A lore answer is an assistant message that responds to a visitor's lore question with cited grounded claims or an abstention. | ordinary response, answer |
| **Grounded claim** | A grounded claim is an independently verifiable factual statement whose content is supported only by retrieved lore passages from the approved corpus release. | model knowledge, uncited fact |
| **Abstention** | An abstention is a lore answer that explicitly declines to make a factual claim because the retrieved evidence is insufficient. | refusal, no answer, fallback guess |
| **Guide message** | A guide message is a structured assistant message, generated only after an explicit request or confirmation, that adopts a temporal frame and traveler perspective. | guide, travel guide, guide artifact |
| **Temporal frame** | A temporal frame is the stated Age and, when supported, date that bounds what a guide message may treat as contemporaneously true. | current time, timeline setting |
| **Traveler perspective** | A traveler perspective is the explicitly stated in-world viewpoint from which a guide message describes an itinerary and available knowledge. | player perspective, narrator |
| **Itinerary inference** | An itinerary inference is a plausible route-related synthesis supported by lore passages but not directly stated by them and visibly labeled as inference. | route fact, known itinerary |
| **Generation attempt** | A generation attempt is one server-side execution initiated to produce or replace one assistant message in a conversation. | generation, run, completion |
| **Cancellation** | Cancellation is an immediate visitor request to stop the active generation attempt, with best-effort propagation to backend work. | deletion, pause |
| **Incomplete output** | Incomplete output is streamed text left visible by a failed or cancelled generation attempt, marked as incomplete and excluded from future agent context. | draft answer, assistant message |
| **Retry** | A retry is a new generation attempt that replaces the failed or cancelled output shown to the visitor while preserving prior attempt metadata. | resume, rerun in place |

## Evidence, citation, and attribution

| Term | Definition | Aliases to avoid |
|------|------------|------------------|
| **Retrieved evidence** | Retrieved evidence is the set of lore passages returned to a generation attempt for possible support, not a declaration that every returned passage supports a claim. | context, sources, proof |
| **Citation** | A citation is a user-visible link from a grounded claim to its supporting passage context and exact Wikipedia revision provenance. | source, retrieval hit, footnote only |
| **Source list** | A source list is the consolidated set of cited Wikipedia revisions presented with a guide message in addition to claim-level citations. | bibliography, corpus manifest |
| **Attribution notice** | An attribution notice is the persistent license treatment that credits Wikipedia contributors, links the applicable revision and CC BY-SA 4.0 license, and identifies Halls of Knowledge's modifications. | citation, disclaimer |
| **Provenance** | Provenance is the retained chain of source run, page and revision identity, extraction configuration, passage classification, release association, and claim support from Wikimedia source to a displayed claim. | file path, citation, checksum archive |

## Corpus curation and releases

| Term | Definition | Aliases to avoid |
|------|------------|------------------|
| **Source snapshot** | A source snapshot is a fixed official Wikimedia dump run identified by its wiki database, dated run identifier, exact filename, and dated source URL. | latest dump, Wikipedia snapshot, live Wikipedia |
| **Candidate article** | A candidate article is a namespace-0 English Wikipedia page proposed for human curation but not yet admitted to a corpus release. | corpus article, approved page |
| **Article artifact** | An article artifact is an immutable package-owned filesystem record for exactly one pinned Wikipedia page revision and extractor configuration, retaining its raw wikitext, normalized prose passages, source identifiers, and redirect provenance. | document, page file, index record |
| **Extracted passage** | An extracted passage is a stably identified prose-paragraph unit produced deterministically from an article artifact and available for an operator’s page, section, or paragraph classification. | chunk, snippet, document |
| **Lore passage** | A lore passage is an operator-approved extracted passage whose effective classification is internal lore and is therefore eligible for release and retrieval. | chunk, context, approved text |
| **Passage classification** | A passage classification is the curation category that distinguishes internal lore from creation history, analysis or reception, adaptation material, and reference or administrative material. | tag, topic |
| **Internal lore** | Internal lore is passage content that describes the fictional world's entities, events, relationships, places, or chronology from within the lore context. | canon, in-universe truth |
| **External creation history** | External creation history is passage content about Tolkien's authorship, naming, sources, composition, publication, or other real-world creative development. | lore, background |
| **Analysis or reception** | Analysis or reception is passage content that interprets Tolkien's work or records scholarship, criticism, influence, or audience response. | lore, commentary |
| **Adaptation material** | Adaptation material is passage content originating in or describing films, games, or other adaptations rather than Tolkien's lore as scoped for the demo. | lore, LOTRO content |
| **Reference or administrative material** | Reference or administrative material is source apparatus or wiki-maintenance content retained for provenance but excluded from answer text. | lore passage, answer context |
| **Curation decision** | A curation decision is an operator review outcome that records scope, classify-or-clear action, optional passage classification, operator label, timestamp, and explicit supersession at page, section, or paragraph level. | filter, approval, review rationale |
| **Corpus release manifest** | A corpus release manifest is the authoritative immutable inventory of the article artifacts and lore passages included in one corpus release together with their source and extraction identities. | approved corpus manifest, allowlist, exclusion inventory |
| **Corpus release** | A corpus release is an immutable, validated, versioned body of curated lore passages defined by exactly one corpus release manifest. | lore corpus version, index version, dataset |
| **Active corpus release** | The active corpus release is the one explicitly selected validated release targeted by runtime retrieval, with prior releases retained for association and rollback and temporary index unavailability permitted. | current corpus, latest corpus |
| **Lore corpus** | The lore corpus is the curated body of approved lore passages selected for runtime retrieval through the active corpus release. | knowledge base, Middle-earth category dump, approved corpus |
| **Retrieval index** | A retrieval index is a rebuildable keyword, vector, or future graph projection derived from one corpus release rather than an authoritative source artifact. | corpus, source of truth, database |

## Evaluation and review

| Term | Definition | Aliases to avoid |
|------|------------|------------------|
| **Evaluation case** | An evaluation case is a hand-authored, human-reviewed prompt with expectations for supported facts, synthesis, abstention, guide generation, or resistance to pretrained-knowledge elicitation. | vibe eval, benchmark item, test prompt |
| **Evaluation suite** | The evaluation suite is the initial curated collection of approximately 12–20 evaluation cases used to assess demo behavior. | benchmark, automated judge |
| **Retrieval ablation** | A retrieval ablation is the controlled comparison of the normal retrieval condition with retrieval disabled for the same evaluation case. | ablation test, retrieval test |
| **Output pair** | An output pair is the randomized left/right presentation of the two condition outputs from one retrieval ablation. | A/B test, answer pair |
| **Blinded evaluation review** | A blinded evaluation review is an owner-only human assessment of an output pair without revealing which retrieval condition produced either side. | vibe check, LLM judge |
| **Evaluation verdict** | An evaluation verdict is one of left better, tie, right better, or both fail, optionally accompanied by reviewer notes and tags. | score, winner |

## Presentation architecture

| Term | Definition | Aliases to avoid |
|------|------------|------------------|
| **Interactive island** | An interactive island is a narrowly scoped native Web Component that owns browser behavior requiring more state or lifecycle control than ordinary server-rendered HTML and HTMX interactions. | frontend app, SPA component, widget |
| **Generative UI block** | A generative UI block is a typed, allowlisted assistant-response structure rendered into trusted HTML by application code rather than supplied as arbitrary agent HTML. | agent HTML, dynamic component, tool UI |

## Relationships

- One **Conversation** contains zero or more **Generation attempts**, with at most one active generation attempt at a time.
- One successful **Generation attempt** produces one **Assistant message**; a failed or cancelled generation attempt may leave one **Incomplete output** instead.
- One **Assistant message** is either a **Lore answer** or a **Guide message** and is associated with exactly one **Corpus release**.
- Each **Grounded claim** has one or more **Citations**, and each citation identifies one or more supporting **Lore passages** and their exact article-revision provenance.
- A **Guide message** has one **Temporal frame**, one **Traveler perspective**, claim-level **Citations**, and one consolidated **Source list**; it may contain zero or more visibly labeled **Itinerary inferences**.
- The **Operator** may propose **Candidate articles**, record **Curation decisions**, create a **Corpus release**, and build its **Retrieval index** only through offline corpus commands.
- The initial **Source snapshot** is English Wikipedia dump run `20260701`, and each **Article artifact** represents exactly one page revision and extractor configuration drawn from that pinned source evidence.
- One **Article artifact** contains zero or more **Extracted passages**, while only operator-approved **Lore passages** are eligible to enter a **Corpus release**.
- One **Corpus release** has exactly one **Corpus release manifest** and may have multiple rebuildable **Retrieval indexes**.
- **Candidate articles** discovered through Wikimedia categories remain outside the **Lore corpus** until explicit **Curation decisions** approve their relevant passages.
- Conflicting or uncertain **Lore passages** remain separately represented so a **Lore answer** can state the uncertainty rather than invent a reconciliation.
- One **Retrieval ablation** produces one **Output pair** per **Evaluation case**, and each **Blinded evaluation review** records one **Evaluation verdict**.
- A **Generative UI block** may appear within an **Assistant message**, while an **Interactive island** may manage its browser-side interaction without accepting arbitrary agent HTML.

## Example dialogue

> **Dev:** “Can a generation attempt answer from Tolkien facts the model already knows if corpus search finds nothing?”  
> **Domain expert:** “No; it must produce an abstention because every grounded claim needs retrieved evidence from the associated corpus release.”  
> **Dev:** “May a guide message still propose a likely route?”  
> **Domain expert:** “Only after the visitor explicitly requests or confirms the guide, and any route synthesis must be a visibly labeled itinerary inference within its temporal frame and traveler perspective.”  
> **Dev:** “Does linking a citation satisfy our Wikipedia obligations?”  
> **Domain expert:** “Not by itself; citations show claim support, while the attribution notice supplies the separate contributor, modification, and CC BY-SA 4.0 treatment.”

## Flagged ambiguities

- “Age/date” is confirmed as required for a **Temporal frame**, but the calendar system, precision, handling of approximate dates, and behavior when only an Age is supportable are unresolved — define these in the guide specification rather than implying exact dates.
- “Traveler perspective” does not yet establish whether the traveler is generic, visitor-selected, culturally situated, or a named canonical figure — keep the perspective explicit but do not assign identity rules until specified.
- “Independently verifiable claim” does not yet establish citation granularity for compound sentences, shared citations, or purely inferential connective language — specify a claim-segmentation and citation-placement rule before rendering behavior is fixed.
- “Associated with the corpus release” is required for answers, but it is unresolved whether a conversation pins one release for its lifetime or each generation attempt selects the then-active release — preserve attempt-level traceability and decide conversation pinning in the specifications.
- “Owner-only” identifies access to evaluation review but does not define whether owner is a single person, a deployment role, or merely possession of a separate credential — define the authorization role before specifying the review UI.
- “Retry replaces the failed visible answer” does not settle whether replacement preserves a visible audit marker or makes prior attempts accessible anywhere outside debugging and evaluation metadata — specify the visitor-visible history policy separately from retained attempt records.
- **Itinerary inference** is required to be visibly labeled, but the label wording and whether each inferred claim or the whole itinerary carries it are unresolved — specify the minimum labeling unit in the guide contract.
- The first release targets approximately 25–50 manually approved pages, but the exact page set and final passage decisions remain release data chosen by the single operator, not glossary definitions.
- Wikimedia attribution is intentionally conservative, but exact source-panel placement and legal conclusions about private demos, hosted-model transmission, generated adaptations, ShareAlike scope, and Tolkien rights remain unresolved — retain separate **Citation** and **Attribution notice** concepts and obtain legal review before broader release.
