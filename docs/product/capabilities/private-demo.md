# Private demo

> Maturity: Draft intent

## Purpose

The private demo gives a small invited audience access to the product while
keeping operations proportional to an early experiment. It protects visitor,
evaluation, corpus, and secret data without introducing a public identity
system or distributed production platform.

## Desired outcomes

- Invited visitors can reach the chat while anonymous public access remains
  closed.
- Evaluation review is more restricted than ordinary visitor access.
- Restarts and expected operator actions do not silently lose accepted data.
- Secrets remain outside source control, deployable artifacts, and logs.
- The operator can back up, verify, restore, activate, roll back, and delete data
  deliberately.

## Boundaries

This capability owns shared access, reviewer authorization, secret handling,
deployment shape, persistent storage, recovery, and operational authorization.

It does not redefine corpus commands, release validity, conversation semantics,
response policy, or evaluation verdicts.

## Durable invariants

- The initial visitor boundary uses one shared credential and provides no public
  registration, profiles, or anonymous access.
- Evaluation review requires authority beyond ordinary visitor access.
- Required secrets are supplied outside source and are redacted from diagnostics
  and logs; missing critical configuration fails closed.
- Corpus artifacts, releases, conversation data, attempts, and evaluation
  evidence survive ordinary process and instance restart.
- Offline corpus operations cannot be initiated through visitor web requests or
  lore-agent tools.
- Backup verification distinguishes a valid corpus release from a complete
  recoverable application state.
- Restore validates retained identities and rebuilds derived indexes when
  needed rather than treating them as source authority.
- Storage or persistence failure cannot report a successful state transition or
  completed assistant message falsely.
- Destructive operations require explicit scope and cannot remove active or
  retained supporting evidence still in use.
- The initial service targets one application instance without high
  availability, autoscaling, or distributed workers.

## Key decisions and rationale

### Keep access intentionally small

A shared visitor credential matches the invited-demo boundary and avoids
building account management before the product bet is understood. Reviewer
access remains separate because it exposes concealed evaluation evidence and
operational judgment.

### Use single-instance persistence

The initial workload and audience do not justify distributed coordination.
Local durable storage and rebuildable indexes keep recovery understandable for
one operator. See
[ADR 0005](../../adr/0005-use-a-single-instance-deployment.md).

### Treat backups as verified evidence

Creating an archive is not enough. The operator needs deterministic membership
and integrity checks and a staged restore path so backup success cannot mask a
missing artifact or unsafe archive.

## Representative scenarios

- An unauthenticated visitor requests a protected conversation and reaches the
  credential boundary without learning protected content.
- An ordinary visitor attempts to reach evaluation review; access is rejected
  without exposing case or condition data.
- The application starts without a required secret; it fails closed with a
  redacted operator diagnostic.
- The instance restarts during generation; the attempt becomes truthfully
  incomplete and retained conversations and releases remain available.
- A backup is missing one artifact required by a retained release; verification
  fails before restore or milestone completion is claimed.

## Open questions

Reviewer-role semantics, session duration, credential rotation, packaging,
persistent-volume choice, TLS termination, proxy behavior, resource monitoring,
and complete hosted recovery policy remain open. See
[open product questions](../open-questions.md).

