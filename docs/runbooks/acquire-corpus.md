# Acquire the corpus

## Preconditions

Install the project:

```bash
uv sync
```

Store the monitored Wikimedia contact in the gitignored `.env` file:

```dotenv
META_WIKIMEDIA_CONTACT=mailto:YOUR_MONITORED_EMAIL
```

The contact is required for Wikimedia network operations. `--contact` is
available as an explicit override, but the environment file avoids repeating an
address in shell history.

The pinned compressed dump is approximately 25.5 GB. Leave enough space for the
dump, a temporary SQLite redirect catalog, and extracted article artifacts.

## Discover candidates

Run bounded category discovery and add direct human nominations as needed:

```bash
uv run meta corpus discover \
  --category "Middle-earth characters" \
  --category "Middle-earth locations" \
  --nominate "Gandalf" \
  --max-candidates 100 \
  --output data/discovery/initial.json
```

Human nominations do not require network traffic or a contact value:

```bash
uv run meta corpus discover \
  --nominate "Gandalf" \
  --nominate "Mithrandir" \
  --output data/discovery/nominations.json
```

Discovery is advisory. Inspect the resulting candidates before acquisition.

## Download and extract

Acquire from the exact source selected by
[ADR 0001](../adr/0001-use-a-pinned-wikimedia-source-snapshot.md):

```bash
uv run meta corpus acquire \
  --discoveries data/discovery/initial.json \
  --data-dir data/corpus
```

The command downloads:

```text
https://dumps.wikimedia.org/enwiki/20260701/enwiki-20260701-pages-articles.xml.bz2
```

If the dump is already present, supply its absolute path and actual retrieval
timestamp:

```bash
uv run meta corpus acquire \
  --discoveries data/discovery/initial.json \
  --data-dir data/corpus \
  --dump-path /absolute/path/enwiki-20260701-pages-articles.xml.bz2 \
  --retrieved-at "2026-07-20T12:30:00+00:00"
```

Do not invent a retrieval timestamp. The command performs complete sequential
scans before publishing immutable JSON article artifacts under
`data/corpus/articles/`.

## Verify the result

Inspect `data/corpus/acquisition-result.json`, the source snapshot, acquisition
failures, and emitted article artifacts. Discovery or extraction success does
not constitute curation approval.

Run the automated checks:

```bash
uv run pytest tests/test_cli.py tests/test_corpus_acquisition.py
uv run ruff check .
uv run ruff format --check .
```

