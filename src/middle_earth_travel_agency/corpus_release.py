"""Deterministic immutable manifests for curated corpus releases."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .corpus_curation import load_corpus
from .curation_snapshot import read_snapshot


SCHEMA_VERSION = 2
SELECTION_POLICY = "all lore-bearing articles"
LORE_CLASSIFICATION = "internal lore"
_RELEASE_ID = re.compile(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?")


@dataclass(frozen=True)
class ReleaseResult:
    release_id: str
    article_count: int
    passage_count: int
    manifest_sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_json(document: object) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _required(document: dict[str, Any], field: str, kind: type, artifact: str) -> Any:
    value = document.get(field)
    if not isinstance(value, kind) or isinstance(value, bool) or (kind is str and not value):
        raise ValueError(f"article artifact {artifact} has invalid field {field!r}")
    return value


def _article_documents(articles_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    documents: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(articles_dir.glob("*.json")):
        try:
            document = json.loads(path.read_text())
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSON artifact {path.name}: {error.msg}") from error
        if not isinstance(document, dict):
            raise ValueError(f"artifact {path.name} must contain an object")
        documents.append((path, document))
    return documents


def _effective_events(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    undone = {event["supersedes_event_id"] for event in events if event["action"] == "undo"}
    effective: dict[str, dict[str, Any]] = {}
    for event in events:
        if event["action"] in {"classify", "defer"} and event["id"] not in undone:
            effective[event["passage_id"]] = event
    return effective


def build_release_manifest(
    *, release_id: str, articles_dir: Path, curation_snapshot: Path
) -> dict[str, object]:
    """Build the canonical manifest document without writing it."""
    if _RELEASE_ID.fullmatch(release_id) is None:
        raise ValueError("release id must use lowercase letters, numbers, dots, and hyphens")

    corpus = load_corpus(articles_dir)
    metadata, events, _session = read_snapshot(curation_snapshot)
    if metadata["corpus_fingerprint"] != corpus.fingerprint:
        raise ValueError("curation snapshot belongs to an incompatible artifact set")

    passage_ids = {passage.passage_id for passage in corpus.passages}
    event_passage_ids = {event["passage_id"] for event in events}
    unknown = event_passage_ids - passage_ids
    if unknown:
        raise ValueError("curation snapshot contains an unknown passage id")

    effective = _effective_events(events)
    deferred = sum(event["action"] == "defer" for event in effective.values())
    undecided = len(passage_ids - effective.keys())
    if deferred or undecided:
        raise ValueError(
            f"curation is incomplete: {deferred} deferred and {undecided} undecided passage(s)"
        )

    lore_by_article: dict[str, list[str]] = {}
    for passage in corpus.passages:
        if effective[passage.passage_id]["classification"] == LORE_CLASSIFICATION:
            lore_by_article.setdefault(passage.article_id, []).append(passage.passage_id)
    if not lore_by_article:
        raise ValueError("refusing to create an empty corpus release")

    documents = _article_documents(articles_dir)
    source_snapshot: dict[str, Any] | None = None
    articles: list[dict[str, object]] = []
    corpus_articles: list[dict[str, object]] = []
    seen_article_ids: set[str] = set()
    for path, document in documents:
        artifact_id = _required(document, "article_artifact_id", str, path.name)
        title = _required(document, "canonical_title", str, path.name)
        page_id = _required(document, "page_id", int, path.name)
        revision_id = _required(document, "revision_id", int, path.name)
        revision_timestamp = _required(document, "revision_timestamp", str, path.name)
        artifact_source = document.get("source_snapshot")
        if not isinstance(artifact_source, dict):
            raise ValueError(f"article artifact {path.name} has invalid field 'source_snapshot'")
        if source_snapshot is None:
            source_snapshot = artifact_source
        elif artifact_source != source_snapshot:
            raise ValueError("article artifacts do not share one source snapshot")
        if artifact_id in seen_article_ids:
            raise ValueError(f"duplicate article artifact id: {artifact_id}")
        seen_article_ids.add(artifact_id)
        artifact_sha256 = _sha256(path)
        corpus_articles.append(
            {
                "article_artifact_id": artifact_id,
                "artifact_filename": path.name,
                "artifact_sha256": artifact_sha256,
            }
        )
        if artifact_id not in lore_by_article:
            continue
        articles.append(
            {
                "article_artifact_id": artifact_id,
                "artifact_sha256": artifact_sha256,
                "canonical_title": title,
                "lore_passage_ids": lore_by_article[artifact_id],
                "page_id": page_id,
                "revision_id": revision_id,
                "revision_timestamp": revision_timestamp,
            }
        )

    missing_articles = lore_by_article.keys() - seen_article_ids
    if missing_articles:
        raise ValueError("a lore passage refers to a missing article artifact")
    articles.sort(
        key=lambda item: (str(item["canonical_title"]).casefold(), item["article_artifact_id"])
    )
    lore_passage_count = sum(len(passage_ids) for passage_ids in lore_by_article.values())
    return {
        "articles": articles,
        "corpus_articles": corpus_articles,
        "counts": {"articles": len(articles), "lore_passages": lore_passage_count},
        "curation": {
            "corpus_fingerprint": corpus.fingerprint,
            "rubric_id": metadata["rubric_id"],
            "snapshot_sha256": _sha256(curation_snapshot),
        },
        "release_id": release_id,
        "schema_version": SCHEMA_VERSION,
        "selection_policy": SELECTION_POLICY,
        "source_snapshot": source_snapshot,
    }


def create_release(
    *, release_id: str, articles_dir: Path, curation_snapshot: Path, output: Path
) -> ReleaseResult:
    """Create a new immutable release manifest without overwriting an existing one."""
    release_dir = output.parent
    if release_dir.exists():
        raise FileExistsError(f"refusing to overwrite retained corpus release: {release_dir}")
    if not articles_dir.is_dir():
        raise ValueError(f"articles directory does not exist: {articles_dir}")
    if not curation_snapshot.is_file():
        raise ValueError(f"curation snapshot does not exist: {curation_snapshot}")

    release_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{release_dir.name}.", suffix=".tmp", dir=release_dir.parent
    ) as staging_name:
        staging = Path(staging_name)
        staged_articles = staging / "articles"
        staged_articles.mkdir()
        article_paths = sorted(articles_dir.glob("*.json"))
        if not article_paths:
            raise ValueError(f"no JSON article artifacts found in {articles_dir}")
        for source in article_paths:
            (staged_articles / source.name).write_bytes(source.read_bytes())
        staged_curation = staging / "curation.jsonl"
        staged_curation.write_bytes(curation_snapshot.read_bytes())
        staged_output = staging / output.name
        document = build_release_manifest(
            release_id=release_id,
            articles_dir=staged_articles,
            curation_snapshot=staged_curation,
        )
        staged_output.write_text(_canonical_json(document))
        try:
            os.rename(staging, release_dir)
        except OSError as error:
            if release_dir.exists():
                raise FileExistsError(
                    f"refusing to overwrite retained corpus release: {release_dir}"
                ) from error
            raise
    return _result(document, output)


def _capture_manifest_inventory(
    document: dict[str, Any], articles_dir: Path, destination: Path
) -> None:
    inventory = document.get("corpus_articles")
    if document.get("schema_version") != SCHEMA_VERSION or not isinstance(inventory, list):
        raise ValueError("invalid corpus release manifest schema")
    if not articles_dir.is_dir():
        raise ValueError(f"articles directory does not exist: {articles_dir}")

    seen_filenames: set[str] = set()
    seen_article_ids: set[str] = set()
    destination.mkdir()
    for item in inventory:
        if not isinstance(item, dict):
            raise ValueError("invalid corpus release manifest schema")
        filename = item.get("artifact_filename")
        artifact_id = item.get("article_artifact_id")
        expected_sha256 = item.get("artifact_sha256")
        if (
            not isinstance(filename, str)
            or not filename
            or Path(filename).name != filename
            or not isinstance(artifact_id, str)
            or not artifact_id
            or not isinstance(expected_sha256, str)
            or len(expected_sha256) != 64
            or filename in seen_filenames
            or artifact_id in seen_article_ids
        ):
            raise ValueError("invalid corpus release manifest article inventory")
        seen_filenames.add(filename)
        seen_article_ids.add(artifact_id)
        source = articles_dir / filename
        if not source.is_file():
            raise ValueError(f"released article artifact does not exist: {source}")
        content = source.read_bytes()
        if _sha256_bytes(content) != expected_sha256:
            raise ValueError(f"released article artifact digest does not match: {filename}")
        (destination / filename).write_bytes(content)
    if not seen_filenames:
        raise ValueError("invalid empty corpus release manifest article inventory")


def validate_release(
    *, manifest: Path, articles_dir: Path, curation_snapshot: Path
) -> ReleaseResult:
    """Validate a manifest against its exact artifacts and curation evidence."""
    if not manifest.is_file():
        raise ValueError(f"corpus release manifest does not exist: {manifest}")
    try:
        document = json.loads(manifest.read_text())
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid corpus release manifest: {error.msg}") from error
    if not isinstance(document, dict) or not isinstance(document.get("release_id"), str):
        raise ValueError("invalid corpus release manifest schema")
    if not curation_snapshot.is_file():
        raise ValueError(f"curation snapshot does not exist: {curation_snapshot}")
    with tempfile.TemporaryDirectory() as staging_name:
        staging = Path(staging_name)
        captured_articles = staging / "articles"
        _capture_manifest_inventory(document, articles_dir, captured_articles)
        captured_curation = staging / "curation.jsonl"
        captured_curation.write_bytes(curation_snapshot.read_bytes())
        expected = build_release_manifest(
            release_id=document["release_id"],
            articles_dir=captured_articles,
            curation_snapshot=captured_curation,
        )
    if document != expected:
        raise ValueError("corpus release manifest does not match its artifacts and curation")
    if manifest.read_text() != _canonical_json(expected):
        raise ValueError("corpus release manifest is not canonical JSON")
    return _result(expected, manifest)


def _result(document: dict[str, object], manifest: Path) -> ReleaseResult:
    counts = document["counts"]
    assert isinstance(counts, dict)
    return ReleaseResult(
        release_id=str(document["release_id"]),
        article_count=int(counts["articles"]),
        passage_count=int(counts["lore_passages"]),
        manifest_sha256=_sha256(manifest),
    )
