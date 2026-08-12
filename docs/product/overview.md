# Product overview

## Product thesis

Halls of Knowledge is a private Tolkien-lore chat demo for a small invited
audience, primarily people who are new to Tolkien's world. It explores whether
an AI assistant can make unfamiliar lore approachable while grounding factual
claims in a small, human-curated and inspectable corpus.

The demo is an experiment, not a general Tolkien authority. Its value lies in
learning whether constrained retrieval, visible evidence, honest abstention,
and temporally framed guide messages produce a more trustworthy experience than
unconstrained model knowledge.

## Audience and needs

The primary visitor is a Tolkien newcomer who wants a clear answer without
having to know which names, Ages, books, or places to search for first. That
visitor needs:

- accessible explanations that do not assume extensive prior knowledge;
- a visible basis for factual claims;
- honest uncertainty when the available corpus cannot support an answer;
- a way to explore lore from a stated point in the fictional chronology; and
- a private, low-stakes environment in which the experience can be evaluated.

The operator is the single developer who acquires, reviews, publishes, and
evaluates the corpus and demo. Operator workflows should favor transparency,
reversibility, and focused human judgment over infrastructure breadth.

## Initial scope

The initial product includes:

- private access through a shared visitor credential;
- stable lore conversations with streamed responses;
- factual answers grounded only in retrieved passages;
- explicit abstention when retrieved evidence is insufficient;
- explicitly requested guide messages with a temporal frame and traveler
  perspective;
- claim-level citations and separate Wikimedia attribution;
- an immutable, versioned English Wikipedia corpus curated by one operator; and
- an owner-controlled blinded comparison of retrieval-enabled and
  retrieval-disabled responses.

## Non-goals

The initial product is not:

- a public chatbot or account-management product;
- a comprehensive Tolkien encyclopedia;
- a source for LOTRO mechanics or current game state;
- a live Wikipedia search experience;
- a multi-source or multimedia corpus;
- a system that treats pretrained model knowledge as evidence;
- a high-availability or distributed service; or
- a legal conclusion about broader public or commercial use of Tolkien or
  Wikimedia material.

## Primary journeys

### Ask a lore question

An invited visitor enters the private demo, asks a question in a persistent
conversation, watches the response arrive, and can inspect the evidence behind
the completed answer. When the corpus cannot support the requested facts, the
assistant says so instead of filling the gap from memory.

### Request a guide

A visitor explicitly asks for or confirms a guide. The resulting message stays
inside the conversation, states its temporal frame and traveler perspective,
and distinguishes sourced lore from plausible itinerary inference.

### Curate and publish evidence

The operator acquires a fixed source snapshot, reviews conservative extraction,
classifies passages under a versioned rubric, and publishes an immutable corpus
release. Runtime retrieval uses only material admitted through that process.

### Evaluate the product bet

The owner compares matched responses with retrieval enabled and disabled,
without seeing the condition assignment before recording a verdict. The goal is
to learn where retrieval improves or fails to improve the product, not merely
to demonstrate that the pipeline runs.

