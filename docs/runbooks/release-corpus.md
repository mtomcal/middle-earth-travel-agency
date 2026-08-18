# Create and validate a corpus release

Create an immutable manifest after every extracted passage has a current
classification. Release creation includes every article with at least one
effective `internal lore` passage and every lore passage from those articles.
Articles with no lore passages are retained as acquisition and curation
evidence but are not listed in the release.

## Create a release candidate

Choose a unique lowercase release identifier. From the repository root, run:

```bash
uv run meta corpus create-release \
  --release-id corpus-v1-rc1 \
  --articles-dir data/corpus/articles \
  --curation data/curation/initial.jsonl \
  --output data/releases/corpus-v1-rc1/manifest.json
```

The command validates the curation snapshot before writing anything. It
rejects a snapshot bound to another artifact set, any deferred or undecided
passage, a mixed source snapshot, an empty lore selection, or an existing
output path. It never overwrites a retained release.

The command stages and publishes the complete release directory atomically. It
retains exact copies of the supplied snapshot as `curation.jsonl` and every
article artifact under `articles/`. This keeps the release verifiable after
later curation or acquisition work changes the shared corpus. The manifest
records:

- the release identifier and manifest schema;
- the pinned Wikimedia source snapshot;
- the curation rubric, corpus fingerprint, and exact JSONL snapshot digest;
- the filename, identity, and digest of every article in the curated corpus;
- each lore-bearing article's identity, revision, and exact artifact digest;
- the ordered lore passage identifiers for each included article; and
- article and lore-passage counts.

Creation is deterministic. The same release identifier, artifacts, and
curation snapshot produce byte-identical manifest files.

## Validate a retained release

Validate the manifest against the exact retained evidence:

```bash
uv run meta corpus validate-release \
  data/releases/corpus-v1-rc1/manifest.json \
  --articles-dir data/releases/corpus-v1-rc1/articles \
  --curation data/releases/corpus-v1-rc1/curation.jsonl
```

Validation captures and rebuilds the expected manifest from exactly the article
inventory recorded in the manifest, ignoring unrelated additions to a shared
articles directory. It verifies every retained blob digest, requires canonical
JSON bytes, and reports the manifest's SHA-256 digest on success.

Commit the manifest and its retained curation snapshot together with any
release-tooling or curation changes that produced them. Do not edit either
retained file. A classification correction, rubric change, source change, or
selection change requires a new release identifier and manifest.

## Understand current boundaries

A validated manifest publishes the immutable corpus contents but does not make
the release active. Release activation and retrieval indexes are separate and
are not implemented yet. Until they exist, the release candidate is a retained
content authority ready for index construction, not a runtime corpus.
