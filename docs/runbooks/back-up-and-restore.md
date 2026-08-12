# Back up and restore corpus evidence

## Create a backup

Commit the canonical acquisition records before creating a normal backup. The
command rejects a dirty working tree unless `--allow-dirty` is supplied
deliberately.

```bash
uv run hok corpus backup \
  --label acquisition-v1 \
  --output-dir backups/
```

The command writes a deterministic `.tar.gz` archive and a matching `.sha256`
sidecar. The archive manifest records its schema, label, Git HEAD, pinned source
identity, and the size and SHA-256 of every payload.

Secrets, the full Wikimedia dump, logs, PID files, temporary SQLite catalogs,
and invalidated acquisition runs are excluded by allowlist.

Use the thin script entry point only when an operator environment calls for it:

```bash
uv run python scripts/backup_corpus.py \
  --label acquisition-v1 \
  --output-dir backups/
```

## Verify a backup

Always verify an archive before treating it as recoverable:

```bash
uv run hok corpus verify-backup \
  backups/hok-enwiki-20260701-acquisition-v1.tar.gz
```

Verification checks the sidecar, archive safety, member allowlist, manifest
schema and member set, and every member size and digest without extracting the
archive.

## Restore to staging

Restore into a new staging directory. Do not merge an unverified archive into
the canonical corpus tree.

```bash
uv run hok corpus verify-backup \
  backups/hok-enwiki-20260701-acquisition-v1.tar.gz
mkdir restored-acquisition
tar -xzf backups/hok-enwiki-20260701-acquisition-v1.tar.gz \
  -C restored-acquisition
```

Inspect the restored `data/` tree and `backup-manifest.json` before promoting
anything to a canonical path.

## Verify the capability

```bash
uv run pytest tests/test_corpus_backup.py
```

