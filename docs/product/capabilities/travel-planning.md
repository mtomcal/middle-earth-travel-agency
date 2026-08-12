# Travel planning

> Maturity: Draft intent

## Purpose

Travel planning turns consultation context and retrieved corpus evidence into
useful planning dialogue, a sufficiently complete trip brief, and structured
input for travel-guide generation. It is the main trust boundary between model
fluency and the agency's factual or practical claims.

## Desired outcomes

- A vague journey idea becomes a coherent trip brief through a focused
  consultation.
- The agency asks only questions whose answers materially affect the journey.
- Planning-relevant lore questions receive accessible, grounded answers.
- Unsupported requests receive honest qualification or abstention.
- Traveler choices, sourced facts, and agency assumptions remain distinct.
- Live consultations and controlled evaluation exercise the same planning
  policy.

## Boundaries

This capability owns consultation orchestration, allowed agent tools,
trip-brief development, evidence-only factual reasoning, abstention,
claim-to-passage bindings, and structured input to guide generation.

It does not own live attempt concurrency, guide artifact persistence or
revision, browser streaming, release activation, citation URL construction,
attribution rendering, or evaluation scheduling.

## Durable invariants

- Factual claims require retrieved evidence from the attempt's corpus release.
- Model knowledge is not a fallback source when retrieval is empty or
  insufficient.
- Conflicting or uncertain evidence remains visible as uncertainty rather than
  being reconciled inventively.
- The agent asks for clarification when a missing choice materially changes the
  journey and otherwise may use a visible conservative assumption.
- The trip brief distinguishes traveler-supplied preferences, grounded facts,
  and explicit assumptions.
- Guide generation requires a trip brief with a temporal frame, traveler
  perspective, and journey intent.
- The agent may use only approved corpus search and immediate-context
  operations for lore evidence.
- Agent output is typed application data, never arbitrary trusted HTML.
- Cancellation and tool failure cannot promote partial output into a successful
  agency message or accepted trip-brief change.
- Live and evaluation invocations use equivalent grounding policy even though
  their surrounding lifecycle differs.

## Key decisions and rationale

### Clarify for consequence, not completeness

A consultation is useful when it discovers choices that change the route,
timing, welcome, risk, or character of the journey. Requiring every possible
preference would make the agency feel like a form; silently assuming material
choices would make the guide arbitrary.

### Treat claim bindings as part of planning

The component deciding what a factual statement means is best placed to say
which passages support it. A downstream renderer may validate and present that
binding, but must not invent support after generation.

### Keep the trip brief semantic

The brief is accepted planning context, not a summary inferred anew from the
entire transcript every time. Typed fields and explicit assumptions make guide
generation, revision, and evaluation reproducible.

### Preserve one policy across product and evaluation

Evaluation should test the planning system travelers receive, not a separate
prompt path optimized for benchmark behavior.

## Representative scenarios

- A traveler says, "I want to see Rivendell"; the agency determines the
  supportable period, starting point, traveler perspective, and interests
  before offering to generate a guide.
- A traveler already supplies a complete brief; the agency does not repeat a
  generic questionnaire.
- Search returns related material but not a requested road condition; the
  agency qualifies or omits the claim rather than completing it from memory.
- Retrieved passages disagree about chronology; the agency describes the
  uncertainty and asks for an assumption only when it changes the proposed
  journey.
- A traveler changes from a generic traveler to a Hobbit perspective; the
  accepted brief records the change so the next guide revision can account for
  pace, knowledge, welcome, and risk.

## Open questions

Minimum trip-brief completeness, clarification policy, default temporal
suggestion, traveler attributes, claim segmentation, model provider, and model
configuration remain open. See
[open product questions](../open-questions.md).
