# Open product questions

Open questions are intentional gaps, not permission for an implementation to
choose silently. Resolve a question in the product document that owns it and
record a technical choice in an ADR when appropriate.

| Area | Question | Evidence or decision needed |
|---|---|---|
| Evaluation | What quantitative or qualitative thresholds define a successful private demo? | Review the initial case set and identify release-blocking failures before claiming validation. |
| Newcomer experience | What spoiler behavior should the initial product offer? | Decide whether the newcomer audience requires an explicit spoiler boundary, user control, or documented deferral. |
| Guide messages | How precise may a temporal frame be when only an Age or approximate date is supportable? | Test guide cases with uncertain chronology and choose conservative wording. |
| Guide messages | Is the traveler generic, visitor-selected, culturally situated, or a named canonical figure? | Prototype the smallest perspective choice that materially improves usefulness. |
| Guide messages | Does the inference label apply to each inferred claim or to an entire itinerary section? | Review comprehension with visitors and confirm that sourced fact and synthesis remain distinguishable. |
| Evidence | What is the minimum independently verifiable claim unit for citation placement? | Review compound claims and shared citations before fixing the rendering contract. |
| Conversations | Does a conversation keep one corpus release for its lifetime, or does each attempt use the active release at admission? | Compare traceability and visitor expectations across release activation. |
| Conversations | How much failed or replaced attempt history should visitors see? | Balance clarity with the need to explain incomplete and retried output. |
| Web experience | Where should sources and attribution appear, and what remains expanded? | Prototype for comprehension and obtain legal review before broader release. |
| Web experience | What visual and interaction language should distinguish guide messages? | Establish a product design direction before treating a presentation as durable. |
| Access | What exactly constitutes the owner/reviewer authorization role? | Decide whether it is one person, a deployment role, or a separate credential. |
| Corpus | What happens when a late extraction defect invalidates an accepted acquisition used by a release? | Define containment, replacement, and historical traceability without silently reclassifying defective extraction. |
| Agent | Which model and provider meet grounding, streaming, cancellation, cost, and deployment needs? | Evaluate candidate configurations against the initial case set. |
| Operations | Which packaging, storage attachment, TLS termination, and proxy arrangement should host the demo? | Decide after response streaming and recovery behavior are exercised locally. |
| Legal | What treatment is required for hosted-model transmission, generated adaptations, ShareAlike scope, and Tolkien rights? | Obtain legal review before public or commercial use. |

