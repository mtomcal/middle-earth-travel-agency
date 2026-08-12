# 0006: Use a Python modular monolith

> Status: Accepted

## Context

The product combines offline corpus processing, retrieval, model orchestration,
web behavior, and evaluation, all operated by one developer. Splitting these
capabilities across languages or network services would add deployment and
contract overhead before their scale or ownership requires it.

## Decision

Implement the initial system as one Python package with explicit internal
capability boundaries. Use package-owned CLI entry points for offline work and a
FastAPI application for planned web surfaces. Keep the option to extract a
service later without designing network boundaries prematurely.

## Rationale

- One language covers the current parsing, SQLite, web, and model ecosystem.
- Shared domain identities can remain internal typed contracts.
- One package is simpler to test, deploy, and operate for a single developer.
- Logical ownership can be enforced without distributed runtime complexity.

## Consequences

- Capability boundaries require discipline because process boundaries do not
  enforce them.
- Offline commands and web requests share a codebase but must preserve distinct
  authority and execution paths.
- Resource-heavy corpus operations must not run in request handling.
- A later split will require deliberate public contracts and migration work.

## Alternatives considered

- Separate corpus, agent, and web services were deferred because there are no
  independent scaling or team boundaries.
- Multiple implementation languages were rejected because they add packaging
  and operational cost without current product value.
- A distributed job system was deferred because corpus mutation is an explicit
  operator workflow.

## Replacement triggers

Reconsider the monolith when capabilities need independent deployment or
scaling, separate teams own them, corpus jobs interfere with runtime isolation,
or a stable non-HTML public interface becomes a product requirement.

