# Project documentation

This documentation explains why Middle-earth Travel Agency has its present
shape and which commitments an implementation must preserve. It is
deliberately not a prose copy of the code.

## Sources of authority

| Question | Authority |
|---|---|
| Why does the product exist, and what must remain true? | [Product](product/index.md) |
| Why was a consequential technical approach chosen? | [Architecture decision records](adr/index.md) |
| How does an operator perform a current task? | [Runbooks](runbooks/index.md) |
| How does the system work now? | Code and automated tests |
| What has changed over time? | Git history |

When documentation and code disagree, the kind of disagreement determines the
fix. Code that violates product intent should change. Product documentation
that describes an obsolete implementation detail should be removed or moved to
an ADR or runbook.

## Update policy

Product documents change only when at least one of these changes:

- the product problem, audience, scope, or intended outcome;
- a durable behavior or trust-boundary commitment;
- the ownership boundary between capabilities;
- the rationale for a product decision; or
- an open product question is resolved or materially reframed.

Product documents do not need updates for ordinary refactors, internal schema
changes, renamed implementation types, library upgrades, new internal error
types, or equivalent behavior implemented in a different way.

ADRs change when a technical decision is proposed, accepted, superseded, or no
longer accurately states its rationale and consequences. Runbooks change when
the operator workflow changes. Code and tests own all remaining implementation
detail.

## Writing conventions

- Use lowercase kebab-case filenames.
- Name a document after the concept it owns, not after its document type.
- Keep product statements independent of implementation unless the technology
  is itself a deliberate constraint.
- Record alternatives and replacement triggers in ADRs, not product documents.
- Prefer a few representative scenarios over exhaustive catalogs that mirror
  tests.
- Use terms from the [product glossary](product/glossary.md) consistently.
- Do not add per-file versions, update timestamps, or changelogs; Git already
  provides that history.

## Change test

Before editing a product document, ask:

> Could this code change without changing product intent, a user-visible
> commitment, or a durable trust boundary?

If the answer is yes, the product document should normally remain unchanged.
