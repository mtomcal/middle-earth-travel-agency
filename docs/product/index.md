# Product documentation

The product documentation captures the intent that cannot be recovered safely
from code alone. It tells contributors and coding agents what Halls of Knowledge
is trying to learn, which tradeoffs are deliberate, and which behaviors must not
be lost during implementation changes.

## Product foundation

- [Overview](overview.md) defines the problem, audience, scope, and primary
  journeys.
- [Outcomes](outcomes.md) defines the hypotheses and evidence the private demo
  is intended to produce.
- [Principles](principles.md) records durable cross-cutting commitments.
- [Glossary](glossary.md) is the project's ubiquitous language.
- [Open questions](open-questions.md) keeps unresolved product decisions visible.

## Capabilities

- [Corpus acquisition](capabilities/corpus-acquisition.md)
- [Corpus curation](capabilities/corpus-curation.md)
- [Corpus retrieval](capabilities/corpus-retrieval.md)
- [Lore responses](capabilities/lore-responses.md)
- [Evidence and attribution](capabilities/evidence-and-attribution.md)
- [Conversations](capabilities/conversations.md)
- [Web experience](capabilities/web-experience.md)
- [Evaluation](capabilities/evaluation.md)
- [Private demo](capabilities/private-demo.md)

Each capability states its maturity. **Established intent** records decisions
already reviewed through implementation or hands-on prototyping. **Draft
intent** records the current direction without claiming that unresolved product
behavior has been approved.

## Ubiquitous language

Ubiquitous language remains important here. The filename is simply
`glossary.md`: the practice is that product documents, code, tests, interfaces,
and conversation use the same domain terms with the same meanings.

The glossary contains domain concepts whose meaning matters across boundaries.
It does not need an entry for every class, table, command flag, or UI component.
Those local implementation names are best explained where they are used.

