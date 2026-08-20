"""Package-owned offline corpus commands."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv

from .corpus_acquisition import (
    DiscoveryRecord,
    DiscoveryRequest,
    PywikibotCatalog,
    SourceSnapshot,
    discover_candidates,
    download_initial_dump,
    extract_article_artifacts,
)
from .corpus_backup import create_backup, verify_backup
from .corpus_curation import CurationState, load_corpus, run_terminal
from .corpus_release import create_release, validate_release
from .curation_snapshot import export_snapshot, load_snapshot
from .experiment_config import load_experiment_config
from .retrieval_index import build_index


class _EmptyCatalog:
    def articles(self, category: str, limit: int):
        return ()


def _parser() -> argparse.ArgumentParser:
    contact = os.environ.get("META_WIKIMEDIA_CONTACT")
    parser = argparse.ArgumentParser(prog="meta")
    commands = parser.add_subparsers(dest="command", required=True)
    corpus = commands.add_parser("corpus", help="offline corpus lifecycle")
    corpus_commands = corpus.add_subparsers(dest="corpus_command", required=True)

    discover = corpus_commands.add_parser("discover", help="record bounded candidates")
    discover.add_argument("--category", action="append", default=[])
    discover.add_argument("--nominate", action="append", default=[])
    discover.add_argument("--max-candidates", type=int, default=100)
    discover.add_argument(
        "--contact",
        default=contact,
        help="monitored email or URL (defaults to META_WIKIMEDIA_CONTACT)",
    )
    discover.add_argument("--minimum-request-interval", type=float, default=1.0)
    discover.add_argument("--output", type=Path, required=True)

    acquire = corpus_commands.add_parser(
        "acquire", help="download the pinned dump and extract candidate artifacts"
    )
    acquire.add_argument("--discoveries", type=Path, required=True)
    acquire.add_argument("--data-dir", type=Path, required=True)
    acquire.add_argument(
        "--contact",
        default=contact,
        help="required for download (defaults to META_WIKIMEDIA_CONTACT)",
    )
    acquire.add_argument("--dump-path", type=Path)
    acquire.add_argument(
        "--retrieved-at",
        help="ISO-8601 retrieval time required when supplying --dump-path",
    )
    acquire.add_argument("--download-rate-mib", type=int, default=16)

    backup = corpus_commands.add_parser(
        "backup", help="write a deterministic, allowlist-driven backup archive"
    )
    backup.add_argument("--label", required=True, help="operator label for the archive")
    backup.add_argument(
        "--output-dir", type=Path, required=True, help="directory to write the archive and sidecar"
    )
    backup.add_argument(
        "--allow-dirty",
        action="store_true",
        help="permit a dirty git working tree; the manifest still records the exact HEAD commit",
    )

    verify = corpus_commands.add_parser(
        "verify-backup", help="verify a backup archive and its sidecar"
    )
    verify.add_argument("archive", type=Path, help="path to the backup archive")

    curate = corpus_commands.add_parser(
        "curate", help="interactively classify extracted prose passages"
    )
    curate.add_argument(
        "--articles-dir",
        type=Path,
        required=True,
        help="directory containing immutable article JSON",
    )
    curate.add_argument(
        "--state-db", type=Path, required=True, help="explicit SQLite curation state path"
    )
    curate.add_argument(
        "--review-deferred",
        action="store_true",
        help="revisit deferred passages in deterministic corpus order",
    )

    export_curation = corpus_commands.add_parser(
        "export-curation", help="write deterministic, versionable curation JSONL"
    )
    export_curation.add_argument(
        "--state-db", type=Path, required=True, help="SQLite curation state to export"
    )
    export_curation.add_argument(
        "--output", type=Path, required=True, help="JSONL snapshot to create or update"
    )

    load_curation = corpus_commands.add_parser(
        "load-curation", help="create SQLite curation state from versioned JSONL"
    )
    load_curation.add_argument("--input", type=Path, required=True, help="curation JSONL snapshot")
    load_curation.add_argument(
        "--state-db", type=Path, required=True, help="new SQLite curation state to create"
    )

    release = corpus_commands.add_parser(
        "create-release", help="write an immutable lore-bearing corpus release manifest"
    )
    release.add_argument("--release-id", required=True, help="stable identifier for the release")
    release.add_argument("--articles-dir", type=Path, required=True)
    release.add_argument("--curation", type=Path, required=True, help="curation JSONL snapshot")
    release.add_argument("--output", type=Path, required=True, help="new manifest to create")

    validate = corpus_commands.add_parser(
        "validate-release", help="validate a corpus release against retained evidence"
    )
    validate.add_argument("manifest", type=Path, help="release manifest to validate")
    validate.add_argument("--articles-dir", type=Path, required=True)
    validate.add_argument("--curation", type=Path, required=True, help="curation JSONL snapshot")

    index = corpus_commands.add_parser(
        "build-index", help="publish a retrieval index for an immutable corpus release"
    )
    index.add_argument("--manifest", type=Path, required=True)
    index.add_argument("--config", type=Path, required=True)
    index.add_argument("--output", type=Path, required=True)
    return parser


def _write_new_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite retained record: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def _discover(arguments: argparse.Namespace) -> int:
    if not arguments.category and not arguments.nominate:
        raise ValueError("supply at least one --category or --nominate")
    if not 1 <= arguments.max_candidates <= 500:
        raise ValueError("max candidates must be between 1 and 500")
    if len(arguments.category) > 20:
        raise ValueError("at most 20 categories may be queried in one discovery operation")
    if arguments.category and not arguments.contact:
        raise ValueError("--contact is required for live category discovery")
    catalog = (
        PywikibotCatalog(
            contact=arguments.contact,
            minimum_request_interval=arguments.minimum_request_interval,
        )
        if arguments.category
        else _EmptyCatalog()
    )
    result = discover_candidates(
        DiscoveryRequest(
            categories=tuple(arguments.category),
            nominations=tuple(arguments.nominate),
            max_candidates=arguments.max_candidates,
        ),
        catalog=catalog,
        observed_at=datetime.now(UTC),
    )
    document = {"schema_version": 1, "records": [asdict(record) for record in result.records]}
    _write_new_json(arguments.output, document)
    print(f"recorded {len(result.records)} candidate(s) in {arguments.output}")
    return 0


def _load_discoveries(path: Path) -> tuple[DiscoveryRecord, ...]:
    document = json.loads(path.read_text())
    if document.get("schema_version") != 1 or not isinstance(document.get("records"), list):
        raise ValueError("unsupported discovery record schema")
    return tuple(DiscoveryRecord(**record) for record in document["records"])


def _acquire(arguments: argparse.Namespace) -> int:
    discoveries = _load_discoveries(arguments.discoveries)
    if not discoveries:
        raise ValueError("refusing to download a 25.5 GB dump for an empty candidate set")
    if not 1 <= arguments.download_rate_mib <= 32:
        raise ValueError("download rate must be between 1 and 32 MiB/s")
    if arguments.dump_path and not arguments.retrieved_at:
        raise ValueError("--retrieved-at is required with an operator-supplied --dump-path")
    if arguments.retrieved_at:
        retrieved_at = datetime.fromisoformat(arguments.retrieved_at)
        if retrieved_at.tzinfo is None:
            raise ValueError("--retrieved-at must include a timezone")
    else:
        retrieved_at = None
    data_dir: Path = arguments.data_dir
    source_dir = data_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    expected = SourceSnapshot.initial(retrieved_at="").filename
    dump_path = arguments.dump_path or source_dir / expected
    if not dump_path.exists():
        if dump_path.name != expected:
            raise ValueError(f"dump path must end with {expected}")
        if not arguments.contact:
            raise ValueError("--contact is required when downloading from Wikimedia")
        print(f"downloading pinned dump to {dump_path}; this is approximately 25.5 GB")
        download_initial_dump(
            dump_path,
            contact=arguments.contact,
            max_bytes_per_second=arguments.download_rate_mib * 1024 * 1024,
        )

    snapshot_path = source_dir / "source-snapshot.json"
    snapshot_is_new = not snapshot_path.exists()
    source = (
        SourceSnapshot.initial(
            retrieved_at=(retrieved_at or datetime.fromtimestamp(dump_path.stat().st_mtime, UTC))
            .astimezone(UTC)
            .isoformat()
        )
        if snapshot_is_new
        else SourceSnapshot(**json.loads(snapshot_path.read_text()))
    )

    def report_progress(scan_pass: int, page_count: int) -> None:
        if page_count:
            print(f"extraction pass {scan_pass}: scanned {page_count:,} pages", flush=True)
        else:
            print(f"starting extraction pass {scan_pass}", flush=True)

    result = extract_article_artifacts(
        dump_path,
        discoveries=discoveries,
        output_dir=data_dir / "articles",
        source=source,
        progress=report_progress,
    )
    if snapshot_is_new:
        _write_new_json(snapshot_path, asdict(source))
    result_path = data_dir / "acquisition-result.json"
    if result_path.exists():
        result_path = data_dir / (
            f"acquisition-result-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}.json"
        )
    _write_new_json(
        result_path,
        {
            "schema_version": 1,
            "source_snapshot": asdict(source),
            "scan_passes": result.scan_passes,
            "successes": [asdict(item) for item in result.successes],
            "failures": [asdict(item) for item in result.failures],
        },
    )
    print(
        f"extracted {len(result.successes)} artifact(s); "
        f"recorded {len(result.failures)} failure(s) in {result_path}"
    )
    return 0


def _backup(arguments: argparse.Namespace) -> int:
    result = create_backup(
        Path.cwd(),
        label=arguments.label,
        output_dir=arguments.output_dir,
        allow_dirty=arguments.allow_dirty,
    )
    size = result.archive_path.stat().st_size
    print(f"wrote {result.archive_path} ({size} bytes); sidecar {result.sidecar_path}")
    return 0


def _verify(arguments: argparse.Namespace) -> int:
    verify_backup(arguments.archive)
    print(f"verified {arguments.archive}")
    return 0


def _curate(arguments: argparse.Namespace) -> int:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError("corpus curation requires an interactive TTY")
    corpus = load_corpus(arguments.articles_dir)
    state = CurationState(arguments.state_db, corpus)
    try:
        run_terminal(state, review_deferred=arguments.review_deferred)
    finally:
        state.close()
    return 0


def _export_curation(arguments: argparse.Namespace) -> int:
    result = export_snapshot(arguments.state_db, arguments.output)
    print(
        f"exported {result.audit_events} audit event(s) and "
        f"{result.metadata_records} metadata record(s) to {arguments.output}"
    )
    return 0


def _load_curation(arguments: argparse.Namespace) -> int:
    result = load_snapshot(arguments.input, arguments.state_db)
    print(f"loaded {result.audit_events} audit event(s) into {arguments.state_db}")
    return 0


def _create_release(arguments: argparse.Namespace) -> int:
    result = create_release(
        release_id=arguments.release_id,
        articles_dir=arguments.articles_dir,
        curation_snapshot=arguments.curation,
        output=arguments.output,
    )
    print(
        f"created {result.release_id} with {result.article_count} article(s) and "
        f"{result.passage_count} lore passage(s); sha256 {result.manifest_sha256}"
    )
    return 0


def _validate_release(arguments: argparse.Namespace) -> int:
    result = validate_release(
        manifest=arguments.manifest,
        articles_dir=arguments.articles_dir,
        curation_snapshot=arguments.curation,
    )
    print(
        f"validated {result.release_id}: {result.article_count} article(s), "
        f"{result.passage_count} lore passage(s); sha256 {result.manifest_sha256}"
    )
    return 0


def _build_index(arguments: argparse.Namespace) -> int:
    config = load_experiment_config(arguments.config)
    manifest: Path = arguments.manifest
    validate_release(
        manifest=manifest,
        articles_dir=manifest.parent / "articles",
        curation_snapshot=manifest.parent / "curation.jsonl",
    )
    result = build_index(manifest=manifest, output=arguments.output, config=config)
    print(
        f"built {result.metadata.release_id} retrieval index with "
        f"{result.metadata.passage_count} lore passage(s) at {result.output}; "
        f"config {result.metadata.config_identity}"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv(dotenv_path=Path.cwd() / ".env")
    arguments = _parser().parse_args(argv)
    if arguments.corpus_command == "discover":
        return _discover(arguments)
    if arguments.corpus_command == "acquire":
        return _acquire(arguments)
    if arguments.corpus_command == "backup":
        return _backup(arguments)
    if arguments.corpus_command == "verify-backup":
        return _verify(arguments)
    if arguments.corpus_command == "curate":
        return _curate(arguments)
    if arguments.corpus_command == "export-curation":
        return _export_curation(arguments)
    if arguments.corpus_command == "load-curation":
        return _load_curation(arguments)
    if arguments.corpus_command == "create-release":
        return _create_release(arguments)
    if arguments.corpus_command == "validate-release":
        return _validate_release(arguments)
    if arguments.corpus_command == "build-index":
        return _build_index(arguments)
    raise AssertionError("unreachable command")


def console() -> None:
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
