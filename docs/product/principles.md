# Product principles

These are the durable commitments that should survive refactors and technology
changes. A proposal that violates one requires an explicit product decision,
not merely an implementation change.

## Evidence before fluency

Factual lore claims must be supported by passages retrieved from the associated
corpus release. Pretrained model knowledge may help form a query or explanation,
but it is not evidence.

## Honest abstention

Insufficient retrieved evidence produces an explicit abstention. The system
must not quietly fill evidence gaps with likely-sounding lore.

## Newcomer accessibility

Answers should favor clear orientation and explanation over assumed expert
knowledge. Trustworthiness includes whether the intended visitor can understand
the answer.

## Explicit guide intent

A guide message appears only after the visitor explicitly requests or confirms
it. It states its temporal frame and traveler perspective and labels itinerary
inference rather than presenting synthesis as a directly sourced route fact.

## Human-curated corpus boundary

Discovery does not imply approval. Only prose reviewed and classified as
internal lore by the operator may become runtime answer evidence.

## Immutable evidence releases

A published corpus release does not change in place. New source material,
extraction behavior, or curation decisions produce new retained evidence so old
answers remain traceable.

## Singular runtime corpus

Visitors and the lore agent use one operator-selected active corpus release.
The agent cannot choose a release or silently fall back to another one.

## Provenance without internal leakage

The system retains enough identity to trace a displayed claim to an exact
Wikipedia revision and the review decisions that admitted it. Internal paths,
working records, and curation history are not visitor-facing evidence.

## Citation and attribution are distinct

A citation explains support for a claim. An attribution notice addresses
contributors, modifications, and licensing. Neither substitutes for the other.

## Successful context only

Only successfully completed assistant messages may influence later conversation
responses. Failed or cancelled output can remain visible when clearly marked,
but it is not accepted conversation context.

## Deliberate corpus mutation

Acquisition, curation, release publication, activation, rollback, and index
construction are operator actions outside visitor web requests and agent tools.

## Human evidence over self-evaluation

The initial product bet is assessed through controlled, blinded human review.
The system should not use its own model output as proof that grounding works.

## Proportional operations

The private, one-operator demo should remain operationally simple until observed
demand or risk justifies public identity, distributed coordination, or high
availability.

