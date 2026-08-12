# Halls of Knowledge

Halls of Knowledge is a private Tolkien-lore AI chat experiment for invited
newcomers. It explores citation-grounded answers, honest abstention, temporal
guide messages, provenance, and blinded retrieval evaluation against a small
human-curated English Wikipedia corpus.

The implemented slice currently covers offline candidate discovery,
acquisition and extraction from the pinned Wikimedia source, and deterministic
corpus backup. Curation, retrieval indexing, lore responses, evaluation, and the
web experience are not implemented yet.

## Documentation

- [Documentation map](docs/index.md)
- [Product overview](docs/product/overview.md)
- [Product glossary](docs/product/glossary.md)
- [Architecture decisions](docs/adr/index.md)
- [Operator runbooks](docs/runbooks/index.md)

Product documents explain intent and durable commitments. Code and tests explain
the current implementation.

## Install

```bash
uv sync
```

Store the monitored Wikimedia contact locally in the gitignored `.env` file:

```dotenv
HOK_WIKIMEDIA_CONTACT=mailto:YOUR_MONITORED_EMAIL
```

## Current workflows

- [Acquire the corpus](docs/runbooks/acquire-corpus.md)
- [Back up and restore corpus evidence](docs/runbooks/back-up-and-restore.md)

## Verification

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Network acquisition follows Wikimedia's API usage, User-Agent, and API
etiquette policies.
