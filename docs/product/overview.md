# Product overview

## Product thesis

Middle-earth Travel Agency is a noncommercial fan demo that helps a traveler
plan an imagined journey through Middle-earth during the Third Age. Through an
agentic travel consultation, the agency establishes when and as whom the
traveler is journeying, researches relevant places and routes against a small,
human-curated corpus, and produces a personalized Middle-earth travel guide.

The conversation is the workshop; the travel guide is the product. The demo
explores whether constrained retrieval, visible evidence, honest abstention,
and clearly labeled travel inference can produce a guide that is useful,
immersive, and trustworthy without presenting plausible invention as lore.

Middle-earth Travel Agency is an unofficial fan project. It is not affiliated
with or endorsed by the Tolkien Estate or other rights holders.

## Audience and needs

The primary traveler is a Tolkien newcomer who wants to imagine a journey
without already knowing which Ages, dates, peoples, roads, or places matter.
That traveler needs:

- a consultation that asks useful planning questions without requiring lore
  expertise;
- a declared temporal setting within the Third Age;
- a traveler perspective that makes access, knowledge, welcome, and risk
  understandable;
- a practical and readable itinerary grounded in inspectable evidence;
- a clear distinction between sourced lore and inferred travel advice; and
- honest uncertainty when the curated corpus cannot support a detail.

The operator is the single developer who acquires, reviews, publishes, and
evaluates the corpus and demo. Operator workflows should favor transparency,
reversibility, and focused human judgment over infrastructure breadth.

## Initial scope

The initial product includes:

- private access through a shared traveler credential;
- persistent, streamed travel consultations;
- a configurable traveler perspective with a generic traveler as the fallback;
- a required, supportable temporal frame narrower than the Third Age as a
  whole;
- a first-class, text-first travel guide associated with its consultation;
- explicit revisions that preserve earlier guide history;
- factual claims grounded only in retrieved passages;
- explicit abstention when retrieved evidence is insufficient;
- visibly labeled route, duration, provisioning, and itinerary inference;
- claim-level citations, a consolidated guide source list, and separate
  Wikimedia attribution;
- an immutable, versioned English Wikipedia corpus curated by one operator; and
- an owner-controlled blinded comparison of retrieval-enabled and
  retrieval-disabled guide generation.

## Non-goals

The initial product is not:

- a generic Tolkien question-answering chatbot;
- a public account-management or commercial travel product;
- a comprehensive Tolkien encyclopedia or assertion of canon;
- a source for LOTRO mechanics or current game state;
- a live Wikipedia search experience;
- a multi-source or multimedia corpus;
- a map generator or source of canonical route geometry;
- a system that treats pretrained model knowledge as evidence;
- a high-availability or distributed service; or
- a legal conclusion about public use, generated adaptations, Tolkien rights,
  or Wikimedia licensing.

## Primary journeys

### Plan a journey

An invited traveler describes a journey, destination, or experience. The
agency asks only the questions needed to establish the trip brief: temporal
frame, traveler perspective, origin, destination, interests, constraints, and
acceptable uncertainty. Lore questions may be answered along the way when
they help the traveler make a planning decision.

### Generate a travel guide

Once the trip brief is sufficient, the traveler requests a guide. The agency
creates a structured artifact containing the premise, temporal frame, traveler
perspective, route and journey legs, notable places, customs, provisions,
hazards, assumptions, citations, and sources. In-world guidance remains
readable on its own; editorial evidence and caveats remain available alongside
it.

### Revise a travel guide

The traveler continues the consultation to change the route, perspective,
timing, interests, or constraints. A successful revision creates a new guide
revision and preserves the earlier artifact rather than silently rewriting it.

### Curate and publish evidence

The operator acquires a fixed source snapshot, reviews conservative extraction,
classifies passages under a versioned rubric, and publishes an immutable corpus
release. Runtime research uses only material admitted through that process.

### Evaluate the product bet

The owner compares matched travel-planning outputs with retrieval enabled and
disabled, without seeing the condition assignment before recording a verdict.
The goal is to learn whether grounding materially improves guide correctness,
coherence, transparency, and usefulness.
