# Corpus curation

> Maturity: Established intent

## Purpose

Corpus curation lets the single operator decide which accepted prose is usable
as internal Tolkien lore and publish an immutable, auditable body of evidence.
It protects runtime answers from creation history, analysis, adaptations, and
administrative source material without pretending that extraction can make
those semantic judgments automatically.

## Desired outcomes

- The operator can classify a practical corpus accurately without losing
  momentum or context.
- Every released passage has a current, explainable human classification.
- Published answer evidence cannot change silently after an answer cites it.
- Mistakes can be corrected without erasing prior decisions or releases.

## Boundaries

This capability owns the curation rubric, classifications at article, section,
and passage scope, effective classification, review audit, article selection,
release creation, validation, activation, rollback, and retention.

It begins with an accepted acquisition. It does not correct extraction defects,
build retrieval indexes, expose browser curation, or decide how claims are
written and cited.

## Durable invariants

- The five classifications are internal lore, external creation history,
  analysis or reception, adaptation material, and reference or administrative
  material.
- Only effectively internal-lore passages may enter a corpus release.
- More-specific decisions override inherited article or section decisions.
  Changed decisions supersede prior decisions explicitly rather than winning by
  timestamp.
- Undecided, stale, or ambiguously classified material is excluded.
- A material rubric change makes affected prior judgments stale until reviewed
  under the current rubric.
- Every state-changing review answer is saved atomically with the evidence,
  question, and semantic answer the operator saw.
- A selected article must be fully reviewed and contribute every passage
  currently classified as internal lore. Release assembly cannot cherry-pick
  only convenient lore passages from that article.
- A corpus release is an immutable manifest. Later curation creates a new
  release rather than mutating an old one.
- At most one release is active. Activation and rollback select among retained
  valid releases without changing them.
- The active release and evidence required by retained releases cannot be
  deleted.
- Curation and release mutation occur through offline operator workflows.

## Key decisions and rationale

### Use a versioned human rubric

The initial corpus is small enough for careful human judgment, while the
semantic boundary between lore and commentary is too consequential to infer
from extraction or Wikipedia structure. Versioning the rubric makes changed
policy visible and prevents old labels from appearing current by accident.

The initial rubric applies the five classifications as follows:

- **Internal lore** covers claims about the fictional setting, chronology,
  peoples, characters, places, objects, languages, and events. Neutral framing
  such as "in Tolkien's legendarium" does not by itself make an otherwise
  in-world claim external.
- **External creation history** covers authorship, drafting, textual
  development, publication, naming or linguistic inspiration, sources,
  influences, and Tolkien's stated or inferred creative intentions.
- **Analysis or reception** covers interpretation, themes, criticism,
  scholarship, comparisons, reviews, awards, popularity, and cultural impact.
- **Adaptation material** covers the production, casting, design, release, and
  adaptation-specific depiction or invention of film, television, radio,
  stage, game, and other derivative versions.
- **Reference or administrative material** covers bibliographic mechanics,
  navigation, disambiguation, source administration, and prose that does not
  make a self-contained evidentiary claim.

Classification is passage-wide and conservative. A passage is internal lore
only when its substantive claims are usable together as fictional-world
evidence. A passage mixing lore with creation history, analysis, reception, or
adaptation claims receives the applicable non-lore classification rather than
being partially admitted. When more than one non-lore classification applies,
the operator records the principal reason the passage is unsuitable. If that
reason is not clear from the available context, the passage remains undecided
until deferred review rather than being guessed.

### Favor complete-article inclusion

Once an article is selected, all of its current internal-lore passages enter the
release. This reduces confirmation bias and makes release composition
explainable. The initial release aims for 25 to 50 articles, but the count is a
review warning rather than a validity rule.

### Optimize the review interaction for reversible momentum

Hands-on prototyping showed that dense always-visible information was hard to
read, while a focused frame without immediate advancement was too slow. The
accepted direction uses one-key classify-and-advance, undo-and-return,
progressive detail, durable incremental saves, resumability, and a distinct end
summary. Those interaction outcomes matter; the exact storage and terminal
implementation do not.

### Publish immutable releases

Answers need to remain traceable even as curation improves. Immutable releases
separate historical evidence from current operator preference and make rollback
an explicit selection rather than data mutation. See
[ADR 0002](../../adr/0002-use-immutable-curated-corpus-releases.md).

## Representative scenarios

- An article-level internal-lore decision includes its passages until a
  section- or passage-level exclusion overrides it.
- The operator changes the rubric materially; affected selections remain
  blocked until their governing judgments are current.
- A classification save fails; the review view stays on the same question and
  neither the decision nor its audit event appears successful.
- A selected article has one undecided passage; release validation rejects the
  proposed release even if that passage would otherwise be omitted.
- The operator activates an older retained release; it becomes the sole active
  release without mutating either release.

## Open questions

Future classifier assistance may be explored, but it must not silently replace
the operator's review authority or train on audit questions as if they were
current labels.
