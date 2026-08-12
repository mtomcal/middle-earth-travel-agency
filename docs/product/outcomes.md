# Product outcomes

## Purpose

The private demo exists to produce evidence about product hypotheses. A working
application is necessary but is not, by itself, a successful outcome.

## Hypotheses

### Grounding improves trustworthiness

For questions covered by the curated corpus, retrieval-grounded responses
should make supported factual claims and expose enough provenance for a reviewer
to inspect their basis.

Evidence comes from human review of factual support, citation correctness, and
matched retrieval ablations.

### Abstention is better than unsupported fluency

When the corpus does not support an answer, the assistant should decline the
unsupported portion rather than rely on plausible pretrained knowledge.

Evidence comes from deliberately unsupported prompts and attempts to elicit
facts the model may already know.

### Newcomers can understand the answer

Grounding alone is insufficient if responses assume expert vocabulary or bury
the useful explanation. Answers should be understandable to the initial
newcomer audience while remaining faithful to evidence.

Evidence requires human judgment; citation presence is not a proxy for clarity.

### Temporally framed guides are useful without pretending inference is fact

A guide message should help a visitor explore places and routes within a stated
fictional time and perspective. Any plausible synthesis not directly stated by
sources should remain visibly distinguishable from sourced lore.

Evidence comes from reviewed guide cases covering supported facts, temporal
uncertainty, and itinerary inference.

### Provenance remains understandable end to end

The operator should be able to trace displayed claims back through retrieved
passages, curation decisions, immutable article artifacts, and an exact source
revision. Visitors need understandable citations and attribution, not access to
internal storage details.

## Initial evidence plan

The initial evaluation suite should contain approximately 12 to 20
human-reviewed cases spanning:

- supported single-source facts;
- small multi-source synthesis;
- insufficient-evidence abstention;
- explicit guide generation;
- conflicting or uncertain accounts; and
- prompts designed to elicit unsupported pretrained knowledge.

Each case is run under normal retrieval and retrieval disabled. The owner
reviews randomized left/right output pairs using `left better`, `tie`, `right
better`, or `both fail`, with optional notes and tags. An automated model judge
is intentionally outside the first experiment.

## Success criteria still requiring a decision

The suite does not yet have approved numeric thresholds for calling the product
bet successful. Before the demo is treated as validated, the owner should decide:

- which failures are release-blocking regardless of aggregate results;
- the minimum acceptable support and citation correctness;
- the acceptable abstention behavior for supported and unsupported prompts;
- how newcomer clarity will be judged; and
- what ablation result would justify retaining or changing the retrieval
  strategy.

Until those criteria exist, evaluation results are learning evidence rather
than a pass/fail certification.

## Failure signals

The following observations would challenge the current product direction:

- retrieval-enabled answers frequently contain unsupported factual claims;
- retrieval-disabled answers perform equivalently without a meaningful change
  in support or abstention;
- citations are present but do not support their associated claims;
- newcomers cannot understand answers without substantial external context;
- guide messages blur sourced facts and inferred routes; or
- corpus preparation costs overwhelm the value learned from the private demo.

