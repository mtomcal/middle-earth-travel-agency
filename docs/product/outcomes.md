# Product outcomes

## Purpose

The noncommercial fan demo exists to produce evidence about whether an agentic
consultation can create a useful and trustworthy Middle-earth travel guide. A
working consultation interface or polished artifact is necessary but is not, by
itself, a successful outcome.

## Hypotheses

### A consultation can turn vague intent into a coherent trip brief

The agency should identify the few choices that materially affect a journey:
when it occurs, who is traveling, where the journey begins and ends, what the
traveler values, and which constraints matter. It should make reasonable
progress without turning the experience into a long questionnaire.

Evidence comes from reviewed consultations that begin with both vague and
specific requests.

### Grounding improves guide trustworthiness

For journeys covered by the curated corpus, retrieval-grounded guides should
make supported factual claims and expose enough provenance for a reviewer to
inspect their basis.

Evidence comes from human review of factual support, citation correctness,
temporal consistency, and matched retrieval ablations.

### Inference makes a guide useful without masquerading as lore

Travel guides require synthesis that source prose rarely states directly,
including route choice, journey legs, provisions, durations, and practical
advice. Those additions should be useful while remaining visibly
distinguishable from sourced lore.

Evidence comes from reviewed guides that mix direct support, uncertain
chronology, and itinerary inference.

### Honest limits are better than unsupported specificity

When the corpus cannot support a place, route, date, danger, or custom, the
agency should omit the detail, qualify it, ask the traveler to choose an
assumption, or explicitly abstain. It should not rely on plausible pretrained
knowledge or false precision.

Evidence comes from deliberately unsupported requests and prompts designed to
elicit details the model may already know.

### Newcomers can use the resulting guide

The consultation and guide should orient a newcomer without assuming expert
vocabulary. The artifact should communicate what the journey is, why each leg
matters, and which advice is uncertain without requiring separate research.

Evidence requires human judgment; citation presence is not a proxy for
clarity, coherence, or usefulness.

### Immersion and editorial transparency can coexist

The main guide should feel addressed to a traveler in Middle-earth, while its
editorial layer makes evidence, inference, uncertainty, and source attribution
inspectable. Neither layer should undermine the meaning of the other.

### Provenance remains understandable end to end

The operator should be able to trace displayed claims through retrieved
passages, curation decisions, immutable article artifacts, and an exact source
revision. Travelers need understandable citations and attribution, not access
to internal storage details.

## Initial evidence plan

The initial evaluation suite should contain approximately 12 to 20
human-reviewed cases spanning:

- vague requests that require consultation;
- a straightforward supported journey;
- a journey requiring small multi-source synthesis;
- alternative routes or traveler perspectives;
- temporally inconsistent or impossible requests;
- insufficient-evidence abstention;
- uncertain travel logistics and explicitly labeled inference; and
- prompts designed to elicit unsupported pretrained knowledge.

Each guide-generation case is run under normal retrieval and retrieval
disabled. The owner reviews randomized left/right output pairs using `left
better`, `tie`, `right better`, or `both fail`, with optional notes and tags.
An automated model judge is intentionally outside the first experiment.

## Success criteria still requiring a decision

The suite does not yet have approved thresholds for calling the product bet
successful. Before the demo is treated as validated, the owner should decide:

- which factual, temporal, or inference-label failures block a release;
- the minimum acceptable support and citation correctness;
- what constitutes a sufficiently complete trip brief;
- how guide coherence, newcomer clarity, and practical usefulness are judged;
- the acceptable response to supported and unsupported requests; and
- what ablation result justifies retaining or changing the retrieval strategy.

Until those criteria exist, evaluation results are learning evidence rather
than a pass/fail certification.

## Failure signals

The following observations would challenge the current product direction:

- consultations ask many questions without materially improving the guide;
- guides read like generic lore summaries instead of serving a journey;
- retrieval-enabled guides frequently contain unsupported or temporally
  inconsistent factual claims;
- route and logistics inference is presented as canonical fact;
- retrieval-disabled guides perform equivalently without a meaningful change
  in support, transparency, or abstention;
- citations are present but do not support their associated claims;
- newcomers cannot understand or use the guide without substantial outside
  context; or
- corpus preparation costs overwhelm the value learned from the demo.
