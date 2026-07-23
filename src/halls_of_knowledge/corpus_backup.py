"""Deterministic, allowlist-driven corpus backup.

Public seams:

* :func:`create_backup` — materialize a deterministic ``.tar.gz`` plus
  ``.sha256`` sidecar from a repository containing the canonical corpus.
* :func:`verify_backup` — validate a previously-written archive without
  extracting files to disk.

All domain failures raise :class:`BackupError` (a :class:`ValueError`
subclass) so the existing ``hok`` console entry point can surface them as
operator-actionable errors. Internal Python errors during verification
(malformed JSON, truncated gzip) are converted to :class:`BackupError`
with an operator-readable message.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import tarfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

# --------------------------------------------------------------------------- #
# Constants                                                                   #
# --------------------------------------------------------------------------- #

MANIFEST_FILENAME = "backup-manifest.json"
ARCHIVE_SUFFIX = ".tar.gz"
SIDECAR_SUFFIX = ".sha256"
PART_SUFFIX = ".part"
ARCHIVE_BASENAME_PREFIX = "hok-enwiki-20260701"

# Pinned source identity required on every canonical backup.
WIKI_DATABASE = "enwiki"
DUMP_RUN = "20260701"
DUMP_FILENAME = "enwiki-20260701-pages-articles.xml.bz2"
SOURCE_URL = "https://dumps.wikimedia.org/enwiki/20260701/enwiki-20260701-pages-articles.xml.bz2"

ACQUISITION_SCHEMA_VERSION = 1
ACQUISITION_SCAN_PASSES = 2
DISCOVERY_SCHEMA_VERSION = 1

# Exact payload path shapes enforced on every canonical backup.
DISCOVERY_PATH_RE = re.compile(r"^data/discovery/[^/]+\.json$")
ARTICLE_PATH_RE = re.compile(r"^data/corpus/articles/[^/]+\.json$")
SOURCE_SNAPSHOT_PATH = "data/corpus/source/source-snapshot.json"
ACQUISITION_RESULT_PATH = "data/corpus/acquisition-result.json"

# Strict label format: lowercase letters, digits, dot, dash, underscore.
_LABEL_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


# --------------------------------------------------------------------------- #
# Errors                                                                      #
# --------------------------------------------------------------------------- #


class BackupError(ValueError):
    """Raised for every operator-actionable backup/verify failure."""


# --------------------------------------------------------------------------- #
# Result                                                                      #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class BackupResult:
    archive_path: Path
    sidecar_path: Path
    label: str
    git_head: str


# --------------------------------------------------------------------------- #
# Small helpers                                                               #
# --------------------------------------------------------------------------- #


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BackupError(f"{path} is not valid JSON: {error}") from error


def _relative(repository: Path, path: Path) -> str:
    return path.resolve().relative_to(repository.resolve()).as_posix()


def _hash_and_size(data: bytes) -> tuple[int, str]:
    return len(data), hashlib.sha256(data).hexdigest()


def _expect_dict(value: object, what: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise BackupError(f"{what} must be a JSON object")
    return value


def _require_fields(document: dict[str, object], fields: Sequence[str], what: str) -> None:
    for field in fields:
        if field not in document:
            raise BackupError(f"{what} missing required field {field!r}")


def _require_string(value: object, what: str) -> str:
    if not isinstance(value, str) or not value:
        raise BackupError(f"{what} must be a non-empty string")
    return value


def _require_positive_int(value: object, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise BackupError(f"{what} must be a positive integer")
    return value


def _require_timestamp(value: object, what: str) -> str:
    timestamp = _require_string(value, what)
    if "T" not in timestamp:
        raise BackupError(f"{what} must be an ISO-8601 timestamp with a timezone")
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise BackupError(f"{what} must be an ISO-8601 timestamp with a timezone") from error
    if parsed.tzinfo is None:
        raise BackupError(f"{what} must be an ISO-8601 timestamp with a timezone")
    return timestamp


def _require_regular_file(path: Path, what: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise BackupError(f"{what} must be a regular file, not a directory or symlink")


def _require_real_directory(path: Path, what: str) -> None:
    if path.is_symlink() or not path.is_dir():
        raise BackupError(f"{what} must be a real directory, not a symlink")


# --------------------------------------------------------------------------- #
# Label validation                                                            #
# --------------------------------------------------------------------------- #


def _validate_label(label: str) -> str:
    if not isinstance(label, str) or not label:
        raise BackupError("backup label is required")
    for bad in ("..", "/", "\\", "\x00"):
        if bad in label:
            raise BackupError(f"backup label {label!r} contains forbidden substring {bad!r}")
    for suffix in (".tar", ".tar.gz", ".tgz"):
        if label.endswith(suffix):
            raise BackupError(f"backup label {label!r} must not include an archive extension")
    if not _LABEL_PATTERN.match(label):
        raise BackupError(f"backup label {label!r} must match {_LABEL_PATTERN.pattern}")
    return label


# --------------------------------------------------------------------------- #
# Git introspection                                                           #
# --------------------------------------------------------------------------- #


def _run_git(repository: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=repository, capture_output=True, text=True, check=False
        )
    except OSError as error:
        raise BackupError(
            f"git is unavailable; backup requires an exact HEAD commit: {error}"
        ) from error
    if completed.returncode != 0:
        raise BackupError(
            f"git {' '.join(args)} failed: {completed.stderr.strip() or completed.stdout.strip()}"
        )
    return completed.stdout.strip()


def _resolve_git_head(repository: Path, *, allow_dirty: bool) -> str:
    # Do not inspect .git here: linked worktrees use a .git *file*. Git itself
    # is the authority for both ordinary repositories and worktrees.
    head = _run_git(repository, "rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise BackupError("git did not return a 40-character HEAD commit")
    if not allow_dirty and _run_git(repository, "status", "--porcelain"):
        raise BackupError(
            "working tree is dirty; commit or stash changes, or rerun with --allow-dirty"
        )
    return head


# --------------------------------------------------------------------------- #
# Source snapshot / discovery / acquisition / artifact validation             #
# --------------------------------------------------------------------------- #


def _validate_source_snapshot(snapshot: object, *, what: str) -> dict[str, object]:
    snapshot = _expect_dict(snapshot, what)
    _require_fields(
        snapshot,
        (
            "wiki_database",
            "dump_run",
            "filename",
            "source_url",
            "retrieval_timestamp",
            "extraction_profile",
        ),
        what,
    )
    if snapshot["wiki_database"] != WIKI_DATABASE:
        raise BackupError(
            f"{what} wiki_database {snapshot['wiki_database']!r} != pinned {WIKI_DATABASE!r}"
        )
    if snapshot["dump_run"] != DUMP_RUN:
        raise BackupError(f"{what} dump_run {snapshot['dump_run']!r} != pinned {DUMP_RUN!r}")
    if snapshot["filename"] != DUMP_FILENAME:
        raise BackupError(f"{what} filename {snapshot['filename']!r} != pinned {DUMP_FILENAME!r}")
    if snapshot["source_url"] != SOURCE_URL:
        raise BackupError(f"{what} source_url {snapshot['source_url']!r} != pinned {SOURCE_URL!r}")
    if snapshot["extraction_profile"] != "full non-multistream article dump":
        raise BackupError(
            f"{what} extraction_profile is not the pinned full non-multistream profile"
        )
    _require_timestamp(snapshot["retrieval_timestamp"], f"{what} retrieval_timestamp")
    return snapshot


def _same_source_snapshot(left: dict[str, object], right: dict[str, object], what: str) -> None:
    for key in (
        "wiki_database",
        "dump_run",
        "filename",
        "source_url",
        "retrieval_timestamp",
        "extraction_profile",
    ):
        if left.get(key) != right.get(key):
            raise BackupError(f"{what} field {key!r} does not match canonical source snapshot")


def _validate_artifact(
    artifact: object, expected_source: dict[str, object], expected_filename: str, what: str
) -> dict[str, object]:
    artifact = _expect_dict(artifact, what)
    _require_fields(
        artifact,
        (
            "article_artifact_id",
            "wiki_database",
            "dump_run",
            "source_snapshot",
            "page_id",
            "namespace",
            "canonical_title",
            "redirect_chain",
            "revision_id",
            "revision_timestamp",
            "permanent_revision_url",
            "history_url",
            "raw_wikitext",
            "extractor_identity",
            "extractor_configuration",
            "extracted_passages",
            "structural_exclusions",
        ),
        what,
    )
    artifact_id = _require_string(artifact["article_artifact_id"], f"{what} article_artifact_id")
    if expected_filename != f"data/corpus/articles/{artifact_id}.json":
        raise BackupError(
            f"{what} filename {expected_filename!r} does not match article_artifact_id {artifact_id!r}"
        )
    if artifact["wiki_database"] != expected_source["wiki_database"]:
        raise BackupError(f"{what} wiki_database does not match canonical source")
    if artifact["dump_run"] != expected_source["dump_run"]:
        raise BackupError(f"{what} dump_run does not match canonical source")
    _require_positive_int(artifact["page_id"], f"{what} page_id")
    if artifact["namespace"] != 0 or isinstance(artifact["namespace"], bool):
        raise BackupError(
            f"{what} has namespace {artifact['namespace']!r}; only namespace 0 is eligible"
        )
    _require_string(artifact["canonical_title"], f"{what} canonical_title")
    _require_positive_int(artifact["revision_id"], f"{what} revision_id")
    if artifact.get("parent_revision_id") is not None:
        _require_positive_int(artifact["parent_revision_id"], f"{what} parent_revision_id")
    _require_timestamp(artifact["revision_timestamp"], f"{what} revision_timestamp")
    _require_string(artifact["raw_wikitext"], f"{what} raw_wikitext")
    _require_string(artifact["extractor_identity"], f"{what} extractor_identity")
    if not isinstance(artifact["extractor_configuration"], dict):
        raise BackupError(f"{what} extractor_configuration must be an object")
    for field in ("permanent_revision_url", "history_url"):
        url = _require_string(artifact[field], f"{what} {field}")
        if not url.startswith(("https://", "http://")):
            raise BackupError(f"{what} {field} is not a URL")
    if f"oldid={artifact['revision_id']}" not in artifact["permanent_revision_url"]:
        raise BackupError(f"{what} permanent_revision_url does not identify its revision_id")
    inner = _validate_source_snapshot(artifact["source_snapshot"], what=f"{what} source_snapshot")
    _same_source_snapshot(inner, expected_source, what)

    redirects = artifact["redirect_chain"]
    if not isinstance(redirects, list):
        raise BackupError(f"{what} redirect_chain must be a list")
    for index, redirect in enumerate(redirects):
        redirect_what = f"{what} redirect_chain[{index}]"
        redirect = _expect_dict(redirect, redirect_what)
        _require_fields(redirect, ("source_title", "target_title"), redirect_what)
        _require_string(redirect["source_title"], f"{redirect_what} source_title")
        _require_string(redirect["target_title"], f"{redirect_what} target_title")

    passages = artifact["extracted_passages"]
    if not isinstance(passages, list):
        raise BackupError(f"{what} extracted_passages must be a list")
    passage_coordinates: set[tuple[tuple[str, ...], int]] = set()
    for index, passage in enumerate(passages):
        passage_what = f"{what} extracted_passages[{index}]"
        passage = _expect_dict(passage, passage_what)
        _require_fields(
            passage,
            (
                "passage_id",
                "article_artifact_id",
                "heading_path",
                "paragraph_ordinal",
                "normalized_text",
                "structure",
            ),
            passage_what,
        )
        _require_string(passage["passage_id"], f"{passage_what} passage_id")
        if passage["article_artifact_id"] != artifact_id:
            raise BackupError(f"{passage_what} article_artifact_id does not match its artifact")
        heading_path = passage["heading_path"]
        if (
            not isinstance(heading_path, list)
            or not heading_path
            or not all(isinstance(heading, str) and heading for heading in heading_path)
        ):
            raise BackupError(f"{passage_what} heading_path must be a non-empty list of strings")
        ordinal = _require_positive_int(
            passage["paragraph_ordinal"], f"{passage_what} paragraph_ordinal"
        )
        coordinate = (tuple(heading_path), ordinal)
        if coordinate in passage_coordinates:
            raise BackupError(f"{passage_what} duplicates a passage heading path and ordinal")
        passage_coordinates.add(coordinate)
        _require_string(passage["normalized_text"], f"{passage_what} normalized_text")
        if passage["structure"] != "prose paragraph":
            raise BackupError(f"{passage_what} structure must be 'prose paragraph'")

    exclusions = artifact["structural_exclusions"]
    if not isinstance(exclusions, list):
        raise BackupError(f"{what} structural_exclusions must be a list")
    for index, exclusion in enumerate(exclusions):
        exclusion_what = f"{what} structural_exclusions[{index}]"
        exclusion = _expect_dict(exclusion, exclusion_what)
        _require_fields(
            exclusion,
            ("heading_path", "paragraph_ordinal", "structure_type", "reason"),
            exclusion_what,
        )
        if not isinstance(exclusion["heading_path"], list) or not all(
            isinstance(heading, str) and heading for heading in exclusion["heading_path"]
        ):
            raise BackupError(f"{exclusion_what} heading_path must be a list of strings")
        _require_positive_int(exclusion["paragraph_ordinal"], f"{exclusion_what} paragraph_ordinal")
        _require_string(exclusion["structure_type"], f"{exclusion_what} structure_type")
        _require_string(exclusion["reason"], f"{exclusion_what} reason")
    return artifact


def _validate_discovery(payload: object, what: str) -> None:
    payload = _expect_dict(payload, what)
    if type(payload.get("schema_version")) is not int or (
        payload.get("schema_version") != DISCOVERY_SCHEMA_VERSION
    ):
        raise BackupError(
            f"{what} schema_version {payload.get('schema_version')!r} != required "
            f"{DISCOVERY_SCHEMA_VERSION}"
        )
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise BackupError(f"{what} must record a non-empty 'records' list")
    for index, record in enumerate(records):
        _expect_dict(record, f"{what} records[{index}]")


def _validate_payloads(
    repository: Path,
) -> tuple[dict[str, object], list[Path]]:
    """Validate the canonical allowlist and return ``(source_snapshot, payload_paths)``."""
    data_dir = repository / "data"
    _require_real_directory(data_dir, f"data/ at {repository}")
    corpus_dir = data_dir / "corpus"
    _require_real_directory(corpus_dir, "data/corpus")
    source_dir = corpus_dir / "source"
    _require_real_directory(source_dir, "data/corpus/source")

    snapshot_path = source_dir / "source-snapshot.json"
    _require_regular_file(snapshot_path, f"canonical source snapshot {snapshot_path}")
    source_snapshot = _validate_source_snapshot(
        _read_json(snapshot_path), what="source-snapshot.json"
    )

    result_path = data_dir / "corpus" / "acquisition-result.json"
    _require_regular_file(result_path, f"canonical acquisition result {result_path}")
    result = _expect_dict(_read_json(result_path), "acquisition-result.json")
    if type(result.get("schema_version")) is not int or (
        result.get("schema_version") != ACQUISITION_SCHEMA_VERSION
    ):
        raise BackupError(
            f"acquisition-result.json schema_version {result.get('schema_version')!r} != "
            f"required {ACQUISITION_SCHEMA_VERSION}"
        )
    if result.get("scan_passes") != ACQUISITION_SCAN_PASSES:
        raise BackupError(
            f"acquisition-result.json scan_passes {result.get('scan_passes')!r} != required "
            f"{ACQUISITION_SCAN_PASSES}"
        )
    failures = result.get("failures")
    if not isinstance(failures, list) or failures:
        raise BackupError(
            "acquisition-result.json must record a failures list with zero failures before backup"
        )
    inner = _validate_source_snapshot(
        result.get("source_snapshot"), what="acquisition-result.json source_snapshot"
    )
    _same_source_snapshot(inner, source_snapshot, what="acquisition-result.json source_snapshot")
    successes = result.get("successes")
    if not isinstance(successes, list) or not successes:
        raise BackupError("acquisition-result.json must record at least one success")
    declared_ids: dict[str, object] = {}
    for entry in successes:
        if not isinstance(entry, dict):
            raise BackupError("acquisition-result.json each success must be an object")
        _require_fields(
            entry,
            ("candidate_title", "article_artifact_id"),
            "acquisition-result.json success",
        )
        _require_string(entry["candidate_title"], "acquisition-result.json success candidate_title")
        artifact_id = _require_string(
            entry["article_artifact_id"], "acquisition-result.json success article_artifact_id"
        )
        if artifact_id in declared_ids:
            raise BackupError(
                f"acquisition-result.json duplicate success artifact_id {artifact_id!r}"
            )
        declared_ids[artifact_id] = entry

    articles_dir = corpus_dir / "articles"
    try:
        _require_real_directory(articles_dir, "canonical articles directory")
    except BackupError as error:
        raise BackupError(f"missing canonical articles directory at {articles_dir}") from error
    article_paths = sorted(articles_dir.glob("*.json"))
    if not article_paths:
        raise BackupError("canonical articles directory is empty")
    seen_ids: set[str] = set()
    for path in article_paths:
        _require_regular_file(path, f"article payload {path}")
        relative = _relative(repository, path)
        if not ARTICLE_PATH_RE.match(relative):
            raise BackupError(f"article path {relative!r} is not an allowlisted shape")
        artifact = _validate_artifact(
            _read_json(path),
            source_snapshot,
            expected_filename=relative,
            what=relative,
        )
        artifact_id = str(artifact["article_artifact_id"])
        if artifact_id in seen_ids:
            raise BackupError(f"duplicate article artifact id on disk: {artifact_id}")
        seen_ids.add(artifact_id)
        if artifact_id not in declared_ids:
            raise BackupError(
                f"article {artifact_id!r} on disk is not declared in acquisition-result.json"
            )
    for artifact_id in declared_ids:
        if artifact_id not in seen_ids:
            raise BackupError(
                f"acquisition-result.json declares artifact {artifact_id!r} that is not on disk"
            )

    discovery_dir = data_dir / "discovery"
    try:
        _require_real_directory(discovery_dir, "canonical discovery directory")
    except BackupError as error:
        raise BackupError(f"missing canonical discovery directory at {discovery_dir}") from error
    discovery_paths = sorted(discovery_dir.glob("*.json"))
    if not discovery_paths:
        raise BackupError("canonical discovery directory is empty")
    for path in discovery_paths:
        _require_regular_file(path, f"discovery payload {path}")
        relative = _relative(repository, path)
        if not DISCOVERY_PATH_RE.match(relative):
            raise BackupError(f"discovery path {relative!r} is not an allowlisted shape")
        _validate_discovery(_read_json(path), what=relative)
    return source_snapshot, [
        *discovery_paths,
        snapshot_path,
        result_path,
        *article_paths,
    ]


# --------------------------------------------------------------------------- #
# Archive writer                                                              #
# --------------------------------------------------------------------------- #


def _normalized_tarinfo(name: str, payload: bytes) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name=name)
    info.size = len(payload)
    info.mode = 0o644
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.mtime = 0
    return info


def _compress_tar_to_bytes(payloads: Sequence[tuple[str, bytes]]) -> bytes:
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        for arcname, data in payloads:
            tar.addfile(_normalized_tarinfo(arcname, data), io.BytesIO(data))
    gz_buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=gz_buffer, mode="wb", mtime=0, compresslevel=6) as gz:
        gz.write(tar_buffer.getvalue())
    return gz_buffer.getvalue()


def _path_is_occupied(path: Path) -> bool:
    """Return true for a file, directory, or even a dangling symlink."""
    return path.exists() or path.is_symlink()


def _remove_if_present(path: Path) -> None:
    if _path_is_occupied(path):
        path.unlink()


def _assert_backup_outputs_available(archive: Path, sidecar: Path) -> None:
    for path in (
        archive,
        sidecar,
        archive.with_name(archive.name + PART_SUFFIX),
        sidecar.with_name(sidecar.name + PART_SUFFIX),
    ):
        if _path_is_occupied(path):
            raise BackupError(f"refusing to overwrite existing output or partial file {path}")


def _publish_backup_outputs(
    archive: Path, archive_bytes: bytes, sidecar: Path, sidecar_bytes: bytes
) -> None:
    """Publish both outputs through parts, cleaning both on any local failure.

    POSIX cannot make two independent replacements one transaction.  Writing
    both parts before either replacement, then removing all four paths when a
    replacement fails, ensures a failed invocation does not leave a usable
    archive without its required checksum sidecar.
    """
    archive_part = archive.with_name(archive.name + PART_SUFFIX)
    sidecar_part = sidecar.with_name(sidecar.name + PART_SUFFIX)
    _assert_backup_outputs_available(archive, sidecar)
    try:
        archive_part.write_bytes(archive_bytes)
        sidecar_part.write_bytes(sidecar_bytes)
        os.replace(archive_part, archive)
        os.replace(sidecar_part, sidecar)
    except OSError as error:
        cleanup_errors: list[str] = []
        for path in (archive_part, sidecar_part, archive, sidecar):
            try:
                _remove_if_present(path)
            except OSError as cleanup_error:
                cleanup_errors.append(f"{path}: {cleanup_error}")
        suffix = f"; cleanup failed: {'; '.join(cleanup_errors)}" if cleanup_errors else ""
        raise BackupError(f"failed to publish archive or sidecar: {error}{suffix}") from error


def _build_manifest(
    *,
    label: str,
    git_head: str,
    source_snapshot: dict[str, object],
    members: Sequence[tuple[str, int, str]],
) -> bytes:
    return (
        json.dumps(
            {
                "schema_version": 1,
                "label": label,
                "git_head": git_head,
                "source_snapshot": source_snapshot,
                "members": [
                    {"path": path, "size_bytes": size, "sha256": digest}
                    for path, size, digest in members
                ],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


# --------------------------------------------------------------------------- #
# Public: create_backup                                                       #
# --------------------------------------------------------------------------- #


def create_backup(
    repository: Path,
    *,
    label: str,
    output_dir: Path,
    allow_dirty: bool = False,
) -> BackupResult:
    """Materialize a deterministic backup archive plus ``.sha256`` sidecar."""
    label = _validate_label(label)
    repository = repository.resolve()
    if not repository.is_dir():
        raise BackupError(f"repository path {repository} is not a directory")
    git_head = _resolve_git_head(repository, allow_dirty=allow_dirty)
    source_snapshot, payload_paths = _validate_payloads(repository)

    output_dir = output_dir.resolve()
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise BackupError(f"cannot create backup output directory {output_dir}: {error}") from error
    archive_name = f"{ARCHIVE_BASENAME_PREFIX}-{label}{ARCHIVE_SUFFIX}"
    sidecar_name = f"{archive_name}{SIDECAR_SUFFIX}"
    archive = output_dir / archive_name
    sidecar = output_dir / sidecar_name
    _assert_backup_outputs_available(archive, sidecar)

    payloads: list[tuple[str, bytes]] = []
    members: list[tuple[str, int, str]] = []
    seen: set[str] = set()
    for path in payload_paths:
        arcname = _relative(repository, path)
        if arcname in seen:
            raise BackupError(f"duplicate archived path {arcname!r}")
        seen.add(arcname)
        try:
            data = path.read_bytes()
        except OSError as error:
            raise BackupError(f"cannot read payload {arcname}: {error}") from error
        size, digest = _hash_and_size(data)
        members.append((arcname, size, digest))
        payloads.append((arcname, data))
    payloads.sort(key=lambda item: item[0])
    members.sort(key=lambda item: item[0])

    manifest_bytes = _build_manifest(
        label=label,
        git_head=git_head,
        source_snapshot=source_snapshot,
        members=members,
    )
    # Insert the manifest at its sorted position so archive order is canonical.
    insert_at = next(
        (i for i, (name, _) in enumerate(payloads) if name > MANIFEST_FILENAME),
        len(payloads),
    )
    payloads.insert(insert_at, (MANIFEST_FILENAME, manifest_bytes))

    try:
        archive_bytes = _compress_tar_to_bytes(payloads)
    except (OSError, EOFError, ValueError, tarfile.TarError) as error:
        raise BackupError(f"failed to build archive: {error}") from error
    archive_digest = hashlib.sha256(archive_bytes).hexdigest()
    sidecar_text = f"{archive_digest}  {archive.name}\n".encode("ascii")

    _publish_backup_outputs(archive, archive_bytes, sidecar, sidecar_text)
    return BackupResult(
        archive_path=archive,
        sidecar_path=sidecar,
        label=label,
        git_head=git_head,
    )


# --------------------------------------------------------------------------- #
# Public: verify_backup                                                       #
# --------------------------------------------------------------------------- #


def _read_member(tar: tarfile.TarFile, name: str) -> bytes:
    try:
        member = tar.getmember(name)
    except KeyError as error:
        raise BackupError(f"archive is missing required member {name!r}") from error
    if not member.isfile():
        raise BackupError(f"archive member {name!r} is not a regular file")
    payload = tar.extractfile(member)
    if payload is None:
        raise BackupError(f"archive member {name!r} is not readable")
    return payload.read()


def _expected_archive_name(label: str) -> str:
    return f"{ARCHIVE_BASENAME_PREFIX}-{label}{ARCHIVE_SUFFIX}"


def _validate_member_allowlist_shape(name: str) -> None:
    """Reject anything that does not match the canonical payload path shapes."""
    if not name or name != name.strip():
        raise BackupError(f"archive member {name!r} has unsafe whitespace")
    if name.startswith(("/", "\\")):
        raise BackupError(f"archive member {name!r} is an absolute path")
    parts = name.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise BackupError(f"archive member {name!r} contains a path-traversal segment")
    if name == MANIFEST_FILENAME:
        return
    if name == SOURCE_SNAPSHOT_PATH or name == ACQUISITION_RESULT_PATH:
        return
    if DISCOVERY_PATH_RE.match(name) or ARTICLE_PATH_RE.match(name):
        return
    raise BackupError(f"archive member {name!r} is outside the canonical allowlist")


def _ensure_manifest_types(manifest: object) -> dict[str, object]:
    if not isinstance(manifest, dict):
        raise BackupError("backup-manifest.json must be a JSON object")
    schema_version = manifest.get("schema_version")
    if type(schema_version) is not int or schema_version != 1:
        raise BackupError(f"backup-manifest.json schema_version {schema_version!r} != required 1")
    label = manifest.get("label")
    if not isinstance(label, str) or not label:
        raise BackupError("backup-manifest.json label must be a non-empty string")
    try:
        _validate_label(label)
    except BackupError as error:
        raise BackupError(f"backup-manifest.json has an invalid backup label: {error}") from error
    git_head = manifest.get("git_head")
    if not isinstance(git_head, str) or not re.fullmatch(r"[0-9a-f]{40}", git_head):
        raise BackupError("backup-manifest.json git_head must be a 40-character hex string")
    source_snapshot = _expect_dict(
        manifest.get("source_snapshot"), "backup-manifest.json source_snapshot"
    )
    _validate_source_snapshot(source_snapshot, what="manifest source_snapshot")
    members = manifest.get("members")
    if not isinstance(members, list) or not members:
        raise BackupError("backup-manifest.json must list at least one member")
    for index, entry in enumerate(members):
        if not isinstance(entry, dict):
            raise BackupError(f"backup-manifest.json member #{index} must be an object")
        path = entry.get("path")
        size = entry.get("size_bytes")
        sha = entry.get("sha256")
        if not isinstance(path, str) or not path:
            raise BackupError(
                f"backup-manifest.json member #{index} path must be a non-empty string"
            )
        if type(size) is not int or size < 0:
            raise BackupError(
                f"backup-manifest.json member #{index} size_bytes must be a non-negative integer"
            )
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise BackupError(
                f"backup-manifest.json member #{index} sha256 must be a 64-character hex string"
            )
        _validate_member_allowlist_shape(path)
    return manifest


def _verify_archive_contents(tar: tarfile.TarFile, archive_path: Path) -> None:
    names = tar.getnames()
    if len(names) != len(set(names)):
        raise BackupError("archive contains duplicate member names")
    # Reject non-allowlisted member names BEFORE consulting the manifest.
    # The manifest cannot smuggle a path that is not in the canonical
    # allowlist; this is the first defense the operator relies on.
    for name in names:
        _validate_member_allowlist_shape(name)
    for member in tar.getmembers():
        if member.uid != 0 or member.gid != 0 or member.uname or member.gname:
            raise BackupError(f"member {member.name!r} has non-normalized tar ownership")
        if member.mtime != 0:
            raise BackupError(f"member {member.name!r} has non-zero mtime")
        if stat.S_IMODE(member.mode) != 0o644:
            raise BackupError(f"member {member.name!r} has non-normalized mode {oct(member.mode)}")
    if names != sorted(names):
        raise BackupError("archive members are not sorted")
    try:
        manifest_text = _read_member(tar, MANIFEST_FILENAME).decode("utf-8")
        manifest_raw = json.loads(manifest_text)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as error:
        raise BackupError(f"backup-manifest.json is not valid JSON: {error}") from error
    manifest = _ensure_manifest_types(manifest_raw)
    expected = _expected_archive_name(manifest["label"])
    if archive_path.name != expected:
        raise BackupError(
            f"archive name {archive_path.name!r} does not match manifest label "
            f"{manifest['label']!r} (expected {expected!r})"
        )
    manifest_members = manifest["members"]
    manifest_paths: list[str] = [entry["path"] for entry in manifest_members]
    if len(set(manifest_paths)) != len(manifest_paths):
        raise BackupError("backup-manifest.json contains duplicate member paths")
    if MANIFEST_FILENAME in manifest_paths:
        raise BackupError(f"manifest must not list {MANIFEST_FILENAME!r} in payload members")
    for fixed in (SOURCE_SNAPSHOT_PATH, ACQUISITION_RESULT_PATH):
        if fixed not in set(names):
            raise BackupError(f"archive is missing required member {fixed!r}")
        if fixed not in set(manifest_paths):
            raise BackupError(f"backup-manifest.json is missing required member {fixed!r}")
    archive_payload = [n for n in names if n != MANIFEST_FILENAME]
    archive_discovery = [n for n in archive_payload if DISCOVERY_PATH_RE.match(n)]
    archive_articles = [n for n in archive_payload if ARTICLE_PATH_RE.match(n)]
    if not archive_discovery:
        raise BackupError("archive contains no data/discovery/*.json member")
    if not archive_articles:
        raise BackupError("archive contains no data/corpus/articles/*.json member")
    if archive_payload != manifest_paths:
        missing = sorted(set(manifest_paths) - set(archive_payload))
        extras = sorted(set(archive_payload) - set(manifest_paths))
        details = []
        if missing:
            details.append(f"missing: {missing}")
        if extras:
            details.append(f"unexpected: {extras}")
        raise BackupError("archive membership disagrees with manifest: " + "; ".join(details))
    for entry in manifest_members:
        path = entry["path"]
        size = entry["size_bytes"]
        sha = entry["sha256"]
        payload = _read_member(tar, path)
        if len(payload) != size:
            raise BackupError(f"member {path!r} size {len(payload)} does not match manifest {size}")
        if hashlib.sha256(payload).hexdigest() != sha:
            raise BackupError(f"member {path!r} sha256 does not match manifest")


def verify_backup(archive_path: Path) -> None:
    """Validate an archive: sidecar, member allowlist, manifest, member hashes."""
    archive_path = archive_path.resolve()
    if not archive_path.is_file():
        raise BackupError(f"archive {archive_path} does not exist")
    sidecar_path = archive_path.with_name(archive_path.name + SIDECAR_SUFFIX)
    if not sidecar_path.is_file():
        raise BackupError(f"missing sidecar checksum file {sidecar_path}")
    try:
        archive_bytes = archive_path.read_bytes()
        sidecar_text = sidecar_path.read_text()
    except (OSError, UnicodeDecodeError) as error:
        raise BackupError(f"cannot read backup archive or sidecar: {error}") from error
    actual_digest = hashlib.sha256(archive_bytes).hexdigest()
    sidecar_match = re.fullmatch(r"([0-9a-f]{64})  (\S+)\n?", sidecar_text)
    if sidecar_match is None:
        raise BackupError(
            f"sidecar {sidecar_path} is not in conventional <digest>  <filename> format"
        )
    expected_digest, expected_name = sidecar_match.group(1), sidecar_match.group(2)
    if expected_name != archive_path.name:
        raise BackupError(
            f"sidecar {sidecar_path} references {expected_name!r} but archive is "
            f"{archive_path.name!r}"
        )
    if expected_digest != actual_digest:
        raise BackupError(
            f"archive sha256 {actual_digest} does not match sidecar {expected_digest}"
        )

    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            _verify_archive_contents(tar, archive_path)
    except BackupError:
        raise
    except (
        AttributeError,
        EOFError,
        KeyError,
        OSError,
        TypeError,
        UnicodeError,
        ValueError,
        tarfile.TarError,
    ) as error:
        raise BackupError(f"archive is malformed or cannot be verified: {error}") from error
