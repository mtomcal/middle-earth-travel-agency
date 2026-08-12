# Open product questions

Open questions are intentional gaps, not permission for an implementation to
choose silently. Resolve a question in the product document that owns it and
record a technical choice in an ADR when appropriate.

| Area | Question | Evidence or decision needed |
|---|---|---|
| Evaluation | What quantitative or qualitative thresholds define a successful private demo? | Review the initial case set and identify release-blocking failures before claiming validation. |
| Consultation | What is the minimum complete trip brief, and when should the agency ask rather than assume? | Prototype vague and specific journey requests and identify which questions materially change the result. |
| Consultation | How should the traveler invoke guide generation versus continue exploring? | Test an explicit generation action or confirmation without making ordinary lore discussion ambiguous. |
| Temporal framing | Which late-Third-Age date or period, if any, should be suggested as the newcomer default? | Compare a fixed default with an explicit traveler choice while avoiding unsupported precision and accidental spoilers. |
| Traveler perspective | Which attributes beyond cultural identity materially affect access, welcome, knowledge, pace, and risk? | Review representative routes before fixing the trip-brief schema. |
| Spoilers | What spoiler boundary or control should the initial product offer? | Decide how spoiler preferences interact with dates, political conditions, hazards, and guide sources. |
| Travel guides | Which sections are required, optional, or omitted when evidence is insufficient? | Review representative destination and point-to-point guides for usefulness without empty structure. |
| Travel guides | Are itinerary units named journey legs, days, stages, or another less precise measure? | Test whether day-level structure creates unsupported duration claims. |
| Travel guides | Which changes create a new guide revision, and may travelers compare or restore prior revisions? | Define the smallest history model that preserves traceability without becoming document management. |
| Inference | Should inferred advice be labeled per statement, per block, or through a dedicated assumptions section? | Test whether travelers can reliably distinguish sourced lore from synthesized logistics. |
| Evidence | What is the minimum independently verifiable claim unit for citation placement? | Review compound claims and shared citations before fixing the rendering contract. |
| Conversations | Does a consultation keep one corpus release for its lifetime, or does each attempt use the active release at admission? | Compare traceability and traveler expectations across release activation and guide revision. |
| Conversations | How much failed or replaced attempt history should travelers see? | Balance clarity with the need to explain incomplete and retried output. |
| Web experience | How should the consultation, current trip brief, and generated guide share the page? | Prototype the artifact-centered experience before treating a layout as durable. |
| Web experience | Where should editorial notes, citations, sources, and attribution appear? | Prototype for comprehension and obtain legal review before broader release. |
| Export | Which export format, if any, belongs in the initial demo? | Validate the on-screen guide first; then compare print HTML and PDF against actual traveler use. |
| Access | What exactly constitutes the owner/reviewer authorization role? | Decide whether it is one person, a deployment role, or a separate credential. |
| Corpus | What happens when a late extraction defect invalidates an accepted acquisition used by a release? | Define containment, replacement, and historical traceability without silently reclassifying defective extraction. |
| Agent | Which model and provider meet grounding, structured output, streaming, cancellation, cost, and deployment needs? | Evaluate candidate configurations against the initial case set. |
| Operations | Which packaging, storage attachment, TLS termination, and proxy arrangement should host the demo? | Decide after response streaming and recovery behavior are exercised locally. |
| Legal and brand | What disclaimer, naming, hosted-model transmission treatment, generated-adaptation boundary, and ShareAlike treatment are required for the noncommercial fan demo? | Obtain qualified review before broader public distribution; noncommercial status alone does not resolve these questions. |
