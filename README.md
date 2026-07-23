# Halls of Knowledge

The implemented slice covers offline candidate discovery and acquisition/extraction of the pinned English Wikipedia source dump. Curation and runtime indexing are not implemented yet.

## Install

```bash
uv sync
```

Store the monitored Wikimedia contact locally in the gitignored `.env` file:

```dotenv
HOK_WIKIMEDIA_CONTACT=mailto:YOUR_MONITORED_EMAIL
```

`--contact` remains available as an explicit override, but normal commands load
`HOK_WIKIMEDIA_CONTACT` from `.env` so the address is not repeated in shell history.

## 1. Discover candidates

Category discovery is deliberately bounded, serial, non-recursive, and identified. Wikimedia requires a meaningful User-Agent with monitored contact information.

```bash
uv run hok corpus discover \
  --category "Middle-earth characters" \
  --category "Middle-earth locations" \
  --nominate "Gandalf" \
  --max-candidates 100 \
  --output data/discovery/initial.json
```

Safety defaults:

- one request at a time through Pywikibot;
- at least one second between API requests;
- `maxlag=5` and bounded retries/backoff;
- no recursive category traversal;
- at most 20 categories and 500 candidates per operation;
- output is never silently overwritten.

Human nominations require no network traffic and may be recorded without `--contact`:

```bash
uv run hok corpus discover \
  --nominate "Gandalf" \
  --nominate "Mithrandir" \
  --output data/discovery/nominations.json
```

Discovery is advisory. It does not approve a page or make live Wikipedia content authoritative.

## 2. Acquire and extract

This downloads the exact dated source required by the specs:

`https://dumps.wikimedia.org/enwiki/20260701/enwiki-20260701-pages-articles.xml.bz2`

```bash
uv run hok corpus acquire \
  --discoveries data/discovery/initial.json \
  --data-dir data/corpus
```

The dump is approximately 25.5 GB. Before starting, ensure storage is available for the compressed dump, a temporary SQLite redirect catalog, and extracted article artifacts.

Download behavior is conservative:

- one HTTP connection, never parallel range downloads;
- descriptive User-Agent with operator contact;
- default cap of 16 MiB/s;
- `.part` file with validated HTTP Range resume;
- bounded exponential retry delays;
- `Retry-After` honored up to 15 minutes;
- no retry on ordinary authorization/client errors;
- exact dated URL only, never `/latest/`.

If the exact dump has already been downloaded:

```bash
uv run hok corpus acquire \
  --discoveries data/discovery/initial.json \
  --data-dir data/corpus \
  --dump-path /absolute/path/enwiki-20260701-pages-articles.xml.bz2 \
  --retrieved-at "2026-07-20T12:30:00+00:00"
```

An operator-supplied dump requires its actual ISO-8601 retrieval timestamp so provenance is not silently invented.

Extraction performs two complete sequential scans. The first validates the dump and builds a temporary redirect catalog; the second materializes final redirect targets even when they appeared earlier in the dump. Only after complete decompression and XML parsing are immutable JSON article artifacts written under `data/corpus/articles/`.

The extractor retains exact raw wikitext and revision provenance. It emits conservative prose paragraphs and records lists, tables, administrative sections, block quotations, and meaning-affecting unresolved templates as structural exclusions.

## 3. Back up the canonical corpus

The backup capability produces a deterministic, allowlist-driven archive of
the canonical corpus tree. The output is a standard `.tar.gz` plus a
`.sha256` sidecar; `.env`, the 25.5 GB dump, logs, PID files, temporary
SQLite catalogs, and any invalidated acquisition run are never included.

```bash
uv run hok corpus backup \
  --label acquisition-v1 \
  --output-dir backups/
```

The backup writes `backups/hok-enwiki-20260701-acquisition-v1.tar.gz` and a
matching `backups/hok-enwiki-20260701-acquisition-v1.tar.gz.sha256` sidecar.
A `backup-manifest.json` inside the archive records the schema version, the
label, the exact Git HEAD, the pinned source identity, and the byte size and
SHA-256 of every archived payload. Same committed inputs + label yields a
byte-identical archive.

Commit the canonical acquisition records before creating a normal backup. The
default refuses to run against a dirty Git state (the exact HEAD commit remains
mandatory; rerun with `--allow-dirty` only if you understand the manifest will
record a HEAD whose working tree no longer matches):

```bash
uv run hok corpus backup \
  --label acquisition-v1 \
  --output-dir backups/ \
  --allow-dirty
```

A thin operator entry point at `scripts/backup_corpus.py` delegates to the
same package CLI without duplicating behavior:

```bash
uv run python scripts/backup_corpus.py \
  --label acquisition-v1 \
  --output-dir backups/
```

## 4. Verify a backup

Verification inspects the archive and sidecar without extracting files to
disk. It validates the SHA-256, the member allowlist (no path traversal,
no forbidden basenames, no temp/catalog/log/PID entries), the manifest
schema, the exact member set, and every member's size and hash:

```bash
uv run hok corpus verify-backup backups/hok-enwiki-20260701-acquisition-v1.tar.gz
```

A non-zero exit reports the specific failure (corruption, unsafe path, extra
or missing member, hash mismatch, malformed archive) on stderr.

## 5. Restore a backup

Verify before restoring, then unpack into a new staging directory rather than
merging files into an existing acquisition tree:

```bash
uv run hok corpus verify-backup backups/hok-enwiki-20260701-acquisition-v1.tar.gz
mkdir restored-acquisition
tar -xzf backups/hok-enwiki-20260701-acquisition-v1.tar.gz -C restored-acquisition
```

The restored directory contains `data/` and `backup-manifest.json`. The archive
uses standard gzip/tar tooling; no zstd dependency is required.

## Verification

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

The implementation follows Wikimedia's [API Usage Guidelines](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_API_Usage_Guidelines), [User-Agent policy](https://foundation.wikimedia.org/wiki/Policy:User-Agent_policy), and [API etiquette](https://www.mediawiki.org/wiki/API:Etiquette).
