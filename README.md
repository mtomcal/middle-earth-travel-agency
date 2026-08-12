# Middle-earth Travel Agency

Middle-earth Travel Agency is a private, noncommercial fan demo that turns an
agentic travel consultation into a personalized guide for an imagined journey
through Middle-earth during the Third Age. It explores evidence-grounded
planning, explicit temporal and traveler perspectives, honest limits, labeled
travel inference, provenance, and blinded retrieval evaluation against a small
human-curated English Wikipedia corpus.

The conversation is the workshop; the travel guide is the product. The guide's
in-world advice is accompanied by an editorial layer that distinguishes
sourced lore, uncertainty, inference, citations, and attribution.

This is an unofficial fan project and is not affiliated with or endorsed by the
Tolkien Estate or other rights holders.

The implemented slice currently covers offline candidate discovery,
acquisition and extraction from the pinned Wikimedia source, and deterministic
corpus backup. Curation, retrieval indexing, travel planning, guide generation,
evaluation, and the web experience are not implemented yet.

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
META_WIKIMEDIA_CONTACT=mailto:YOUR_MONITORED_EMAIL
```

The implementation uses `middle_earth_travel_agency` as its Python package and
`meta` as its command, with `META_*` reserved for project configuration.

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
