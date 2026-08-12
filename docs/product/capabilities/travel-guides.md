# Travel guides

> Maturity: Draft intent

## Purpose

Travel guides turn an accepted trip brief and grounded planning result into the
primary product artifact of Middle-earth Travel Agency. A guide combines
immersive in-world advice with an editorial layer that makes evidence,
uncertainty, assumptions, and travel inference inspectable.

## Desired outcomes

- The traveler receives a coherent artifact organized around the intended
  journey rather than a generic lore summary.
- The guide clearly states when and as whom the traveler journeys.
- Route, duration, provisions, customs, hazards, and notable places are useful
  without false precision.
- Sourced lore and travel inference remain distinguishable.
- Revisions preserve history and can be traced to their planning context and
  evidence.
- The guide remains understandable and useful as a text-first artifact without
  requiring a map.

## Boundaries

This capability owns guide structure, guide-generation eligibility, in-world
and editorial sections, revision identity, current-revision selection, and the
association between a guide, trip brief, consultation, corpus release, and
generation attempt.

It consumes planning output and claim bindings but does not own consultation
orchestration, corpus retrieval, citation URL construction, attribution text,
browser layout, export rendering, or corpus operations.

## Durable invariants

- A guide is a first-class artifact associated with exactly one travel
  consultation.
- Every guide revision records the accepted trip brief and exact corpus release
  used to produce it.
- A guide states a temporal frame narrower than the Third Age as a whole and a
  traveler perspective.
- Factual guide claims bind to retrieved evidence from the recorded corpus
  release.
- Route, duration, provisioning, lodging, access, risk, and itinerary synthesis
  not directly stated by evidence is visibly identified as travel inference.
- An inference must be a conservative synthesis of grounded facts; labeling
  does not permit arbitrary invention.
- Unsupported required details become an explicit limitation, assumption, or
  omission rather than fabricated specificity.
- The in-world guide and editorial layer are structurally distinct even when
  presented together.
- A material change creates a new immutable guide revision rather than mutating
  an earlier completed revision.
- At most one completed revision is identified as the current guide at a time.
- Failed or cancelled generation cannot create a completed guide revision or
  change which revision is current.
- Generated content is typed application data, never arbitrary trusted HTML.

## Initial guide shape

The initial guide can contain:

- journey title and premise;
- temporal frame and traveler perspective;
- trip-brief summary and explicit assumptions;
- route overview;
- ordered journey legs;
- notable places, peoples, customs, provisions, and hazards when supported;
- clearly marked travel estimates and other inference;
- limitations and unresolved uncertainties;
- claim-level citations; and
- a consolidated guide source list and attribution notice.

A section may be omitted when it is irrelevant or unsupported. The schema
should not reward empty headings or invented filler.

## Key decisions and rationale

### Make the guide an artifact, not a message style

The consultation is exploratory and may contain questions, alternatives, and
failed attempts. A separately identified artifact gives the traveler a stable
result, supports deliberate revision, and makes future print or PDF export
possible without making export part of the first scope.

### Separate in-world guidance from editorial evidence

Immersive prose helps the traveler imagine the journey. Citations, inference
labels, and uncertainty serve a different but equally important purpose.
Keeping both layers explicit allows charm and trustworthiness to coexist.

### Prefer journey legs over false day counts

Sources rarely support modern itinerary precision. Journey legs express useful
sequence while allowing time estimates to remain ranges or labeled inference.

### Preserve revisions rather than silently rewriting

A revision captures the relationship between traveler choices, evidence, and
output at one moment. Retaining it supports comparison, recovery, and
evaluation without treating every conversational turn as a document version.

## Representative scenarios

- A complete trip brief produces a first guide revision and makes it current.
- The traveler changes the route; the next successful attempt creates a new
  revision while the original remains inspectable.
- Evidence supports the existence and order of places but not travel duration;
  the guide labels the duration estimate as inference or omits it.
- A destination is inaccessible during the chosen period; the guide explains
  the conflict instead of silently moving the journey to another date.
- Generation fails after partial streaming; no revision is created and the
  previous current guide remains authoritative.

## Open questions

Required sections, journey-unit language, inference-label granularity, revision
comparison or restoration, and future export format remain open. See
[open product questions](../open-questions.md).
