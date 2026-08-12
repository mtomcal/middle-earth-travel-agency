# Lore responses

> Maturity: Draft intent

## Purpose

Lore responses turn conversation context and retrieved corpus evidence into
accessible answers or explicitly requested guides. This capability is the main
trust boundary between model fluency and product claims.

## Desired outcomes

- Supported questions receive useful, newcomer-friendly explanations.
- Unsupported questions receive honest abstentions.
- Every factual claim can be bound to evidence before presentation.
- Guide messages remain useful without blurring sourced lore and inference.
- Live conversations and controlled evaluation exercise the same response
  policy.

## Boundaries

This capability owns response orchestration, allowed agent tools, evidence-only
factual reasoning, abstention, claim-to-passage bindings, and structured lore
answer and guide output.

It does not own live attempt concurrency, browser streaming, release
activation, citation URL construction, attribution rendering, or evaluation
scheduling.

## Durable invariants

- Factual claims require retrieved evidence from the response's corpus release.
- Model knowledge is not a fallback source when retrieval is empty or
  insufficient.
- Conflicting or uncertain evidence remains visible as uncertainty rather than
  being reconciled inventively.
- A guide requires explicit visitor request or confirmation.
- Every guide states a temporal frame and traveler perspective.
- Route synthesis not directly stated by evidence is visibly identified as
  itinerary inference.
- The agent may use only the approved corpus search and immediate-context
  operations for lore evidence.
- Agent output is typed application data, never arbitrary trusted HTML.
- Cancellation and tool failure cannot promote partial output into a successful
  assistant message.
- Live and evaluation invocations use equivalent grounding policy even though
  their surrounding lifecycle differs.

## Key decisions and rationale

### Treat bindings as part of response generation

The component deciding what a factual statement means is best placed to say
which passages support it. A downstream renderer may validate and present that
binding, but must not invent support after generation.

### Separate ordinary answers and guides

Guide messages introduce temporal truth, traveler knowledge, and route
inference that ordinary questions do not require. A distinct structured output
keeps those obligations explicit without creating a separate standalone
artifact outside the conversation.

### Preserve one policy across product and evaluation

Evaluation should test the response system visitors receive, not a separate
prompt path optimized for benchmark behavior.

## Representative scenarios

- One passage directly supports a requested fact; the response explains it and
  binds the claim to that passage.
- Search returns related material but not the requested fact; the response
  abstains from that claim.
- Retrieved passages disagree; the response describes the conflict and cites
  both rather than selecting an unsupported synthesis.
- A visitor implies interest in travel but does not request a guide; the system
  asks for confirmation before producing guide structure.
- A guide proposes a plausible route assembled from several facts; the route is
  labeled as inference and retains claim-level evidence.

## Open questions

Claim segmentation, temporal precision, traveler identity, inference-label
granularity, model provider, and model configuration remain open. See
[open product questions](../open-questions.md).

