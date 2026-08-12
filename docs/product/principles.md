# Product principles

These are the durable commitments that should survive refactors and technology
changes. A proposal that violates one requires an explicit product decision,
not merely an implementation change.

## The conversation is the workshop; the guide is the product

The agency uses conversation to discover intent, research choices, explain
tradeoffs, and refine a plan. Its primary successful output is a structured,
persistent travel guide rather than an isolated chat answer.

## Ask questions that change the journey

The agency should clarify only choices that materially affect the trip brief or
the resulting guide. It may proceed with explicit, conservative assumptions
when a missing preference does not justify interrupting the traveler.

## Declare when and as whom

Every guide states a supportable temporal frame narrower than the Third Age as
a whole and a traveler perspective. The guide must account for how time,
culture, identity, knowledge, and welcome affect the proposed journey.

## Evidence before fluency

Factual lore claims must be supported by passages retrieved from the associated
corpus release. Pretrained model knowledge may help form a query or explanation,
but it is not evidence.

## Honest limits over invented precision

Insufficient evidence produces an explicit qualification, request for an
assumption, omission, or abstention. The system must not quietly fill gaps or
invent precise routes, durations, services, customs, or dangers.

## Inference must earn its place

Plausible travel synthesis is necessary for a useful guide, but it must be
grounded in cited facts, conservatively expressed, and visibly identified as
inference. An inference label does not excuse arbitrary invention.

## Immersion has an editorial boundary

The travel guide may use an in-world voice, but trusted application structure
keeps citations, uncertainty, inference, and attribution unambiguous. Immersive
language cannot obscure the status of a claim.

## Newcomer accessibility

The consultation and guide should favor clear orientation over assumed expert
knowledge. Trustworthiness includes whether the intended traveler can
understand and use the result.

## Revisions preserve history

A changed plan creates an explicit guide revision. Previously completed guides
remain traceable to the trip brief, conversation state, and corpus release that
produced them.

## Human-curated corpus boundary

Discovery does not imply approval. Only prose reviewed and classified as
internal lore by the operator may become runtime evidence.

## Immutable evidence releases

A published corpus release does not change in place. New source material,
extraction behavior, or curation decisions produce new retained evidence so old
guides remain traceable.

## Singular runtime corpus

Travelers and the agency use one operator-selected active corpus release. The
agent cannot choose a release or silently fall back to another one.

## Provenance without internal leakage

The system retains enough identity to trace a displayed claim to an exact
Wikipedia revision and the review decisions that admitted it. Internal paths,
working records, and curation history are not traveler-facing evidence.

## Citation and attribution are distinct

A citation explains support for a claim. An attribution notice addresses
contributors, modifications, and licensing. Neither substitutes for the other.

## Successful context only

Only successfully completed agency messages and guide revisions may influence
later work. Failed or cancelled output can remain visible when clearly marked,
but it is not accepted consultation context.

## Deliberate corpus mutation

Acquisition, curation, release publication, activation, rollback, and index
construction are operator actions outside traveler web requests and agent
tools.

## Human evidence over self-evaluation

The initial product bet is assessed through controlled, blinded human review.
The system should not use its own model output as proof that grounding works.

## Proportional operations

The noncommercial, one-operator fan demo should remain operationally simple
until observed demand or risk justifies public identity, distributed
coordination, or high availability.
