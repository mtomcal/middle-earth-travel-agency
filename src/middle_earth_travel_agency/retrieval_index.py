"""A disposable, release-compatible SQLite FTS index for approved lore."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .corpus_curation import load_corpus
from .corpus_release import ReleaseResult, validate_release


INDEX_SCHEMA_VERSION = 1
_INDEXED_COLUMNS = ("title", "heading", "body")
_METADATA_KEYS = frozenset(
    {
        "build_identity",
        "config_identity",
        "indexed_columns",
        "manifest_sha256",
        "passage_count",
        "release_id",
        "schema_version",
        "tokenizer",
    }
)
_WORDS = re.compile(r"\S+")


class _IndexSettings(Protocol):
    @property
    def tokenizer(self) -> str: ...

    @property
    def remove_diacritics(self) -> int: ...


class _RetrievalSettings(Protocol):
    @property
    def query_mode(self) -> str: ...

    @property
    def result_limit(self) -> int: ...

    @property
    def title_weight(self) -> float: ...

    @property
    def heading_weight(self) -> float: ...

    @property
    def body_weight(self) -> float: ...

    @property
    def tie_breaker(self) -> str: ...


class _Config(Protocol):
    @property
    def index_identity(self) -> str: ...

    @property
    def index(self) -> _IndexSettings: ...

    @property
    def retrieval(self) -> _RetrievalSettings: ...


@dataclass(frozen=True)
class IndexConfig:
    tokenizer: str = "unicode61"
    remove_diacritics: int = 2


@dataclass(frozen=True)
class RetrievalConfig:
    query_mode: str = "all-terms"
    result_limit: int = 5
    title_weight: float = 5.0
    heading_weight: float = 2.0
    body_weight: float = 1.0
    tie_breaker: str = "passage-id"


@dataclass(frozen=True)
class IndexMetadata:
    release_id: str
    manifest_sha256: str
    schema_version: int
    config_identity: str
    tokenizer: str
    indexed_columns: tuple[str, ...]
    passage_count: int
    build_identity: str


@dataclass(frozen=True)
class EvidencePassage:
    passage_id: str
    article_artifact_id: str
    title: str
    heading_path: tuple[str, ...]
    ordinal: int
    body: str

    @property
    def article_id(self) -> str:
        """Compatibility-friendly short name for the source article identity."""
        return self.article_artifact_id

    @property
    def text(self) -> str:
        return self.body


@dataclass(frozen=True)
class SearchResult:
    passage: EvidencePassage
    rank: float

    @property
    def passage_id(self) -> str:
        return self.passage.passage_id


@dataclass(frozen=True)
class ContextResult:
    target: EvidencePassage
    before: EvidencePassage | None
    before_boundary: str | None
    after: EvidencePassage | None
    after_boundary: str | None


@dataclass(frozen=True)
class IndexBuildResult:
    metadata: IndexMetadata
    output: Path


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _identity(config: _Config) -> str:
    """Use the configuration module's frozen identity; never infer mutable settings."""
    value = config.index_identity
    if not isinstance(value, str) or not value:
        raise ValueError("retrieval configuration has no valid configuration identity")
    return value


def _tokenizer(config: _Config) -> str:
    index = config.index
    if index.tokenizer not in {"unicode61", "porter-unicode61"}:
        raise ValueError("unsupported FTS tokenizer")
    if index.remove_diacritics not in {0, 1, 2}:
        raise ValueError("invalid FTS remove_diacritics setting")
    # FTS5 accepts the porter wrapper before the unicode61 tokenizer arguments.
    prefix = "porter " if index.tokenizer == "porter-unicode61" else ""
    return f"{prefix}unicode61 remove_diacritics {index.remove_diacritics}"


def _release_paths(manifest: Path) -> tuple[Path, Path]:
    return manifest.parent / "articles", manifest.parent / "curation.jsonl"


def _validated_release(manifest: Path) -> ReleaseResult:
    articles, curation = _release_paths(manifest)
    return validate_release(manifest=manifest, articles_dir=articles, curation_snapshot=curation)


def _lore_ids(manifest: Path) -> set[str]:
    try:
        document = json.loads(manifest.read_text())
        articles = document["articles"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise ValueError("invalid corpus release manifest schema") from error
    if not isinstance(articles, list):
        raise ValueError("invalid corpus release manifest schema")
    result: set[str] = set()
    for article in articles:
        if not isinstance(article, dict) or not isinstance(article.get("lore_passage_ids"), list):
            raise ValueError("invalid corpus release manifest schema")
        for passage_id in article["lore_passage_ids"]:
            if not isinstance(passage_id, str) or not passage_id or passage_id in result:
                raise ValueError("invalid corpus release manifest lore passage identity")
            result.add(passage_id)
    return result


def _metadata_from(connection: sqlite3.Connection) -> dict[str, str]:
    try:
        rows = connection.execute("SELECT key, value FROM index_metadata").fetchall()
    except sqlite3.DatabaseError as error:
        raise ValueError("malformed retrieval index") from error
    values = {str(row[0]): str(row[1]) for row in rows}
    if len(rows) != len(values) or frozenset(values) != _METADATA_KEYS:
        raise ValueError("retrieval index metadata is incomplete or malformed")
    return values


def _metadata(values: dict[str, str]) -> IndexMetadata:
    try:
        columns = tuple(json.loads(values["indexed_columns"]))
        metadata = IndexMetadata(
            release_id=values["release_id"],
            manifest_sha256=values["manifest_sha256"],
            schema_version=int(values["schema_version"]),
            config_identity=values["config_identity"],
            tokenizer=values["tokenizer"],
            indexed_columns=columns,
            passage_count=int(values["passage_count"]),
            build_identity=values["build_identity"],
        )
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("retrieval index metadata is malformed") from error
    if (
        metadata.schema_version != INDEX_SCHEMA_VERSION
        or metadata.indexed_columns != _INDEXED_COLUMNS
        or metadata.passage_count < 1
        or not metadata.build_identity
    ):
        raise ValueError("retrieval index metadata is incompatible")
    return metadata


def _expected_metadata(release: ReleaseResult, config: _Config) -> dict[str, str]:
    tokenizer = _tokenizer(config)
    config_identity = _identity(config)
    build_identity = hashlib.sha256(
        _canonical_json(
            {
                "config_identity": config_identity,
                "manifest_sha256": release.manifest_sha256,
                "release_id": release.release_id,
                "schema_version": INDEX_SCHEMA_VERSION,
            }
        ).encode()
    ).hexdigest()
    return {
        "build_identity": build_identity,
        "config_identity": config_identity,
        "indexed_columns": _canonical_json(_INDEXED_COLUMNS),
        "manifest_sha256": release.manifest_sha256,
        "passage_count": str(release.passage_count),
        "release_id": release.release_id,
        "schema_version": str(INDEX_SCHEMA_VERSION),
        "tokenizer": tokenizer,
    }


def _schema(connection: sqlite3.Connection, tokenizer: str) -> None:
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE index_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE passages (
          id INTEGER PRIMARY KEY,
          passage_id TEXT NOT NULL UNIQUE,
          article_artifact_id TEXT NOT NULL,
          title TEXT NOT NULL,
          heading_path TEXT NOT NULL,
          heading TEXT NOT NULL,
          ordinal INTEGER NOT NULL,
          body TEXT NOT NULL,
          page_id INTEGER NOT NULL,
          revision_id INTEGER NOT NULL,
          revision_timestamp TEXT NOT NULL,
          UNIQUE(article_artifact_id, heading_path, ordinal)
        );
        CREATE TABLE context_coordinates (
          article_artifact_id TEXT NOT NULL,
          heading_path TEXT NOT NULL,
          ordinal INTEGER NOT NULL,
          availability TEXT NOT NULL CHECK (availability IN ('lore', 'non-lore-or-excluded')),
          passage_id TEXT UNIQUE REFERENCES passages(passage_id),
          PRIMARY KEY(article_artifact_id, heading_path, ordinal),
          CHECK ((availability = 'lore' AND passage_id IS NOT NULL)
                 OR (availability = 'non-lore-or-excluded' AND passage_id IS NULL))
        );
        """
    )
    connection.execute(
        """CREATE VIRTUAL TABLE passages_fts USING fts5(
             title, heading, body, content='passages', content_rowid='id', tokenize='%s')"""
        % tokenizer
    )


def _heading_path(value: str) -> tuple[str, ...]:
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError("retrieval index has malformed heading coordinates") from error
    if not isinstance(loaded, list) or not all(isinstance(part, str) for part in loaded):
        raise ValueError("retrieval index has malformed heading coordinates")
    return tuple(loaded)


def _evidence(row: sqlite3.Row) -> EvidencePassage:
    return EvidencePassage(
        passage_id=str(row["passage_id"]),
        article_artifact_id=str(row["article_artifact_id"]),
        title=str(row["title"]),
        heading_path=_heading_path(str(row["heading_path"])),
        ordinal=int(row["ordinal"]),
        body=str(row["body"]),
    )


def _validate_content(
    connection: sqlite3.Connection, lore_ids: set[str], passage_count: int
) -> None:
    try:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("retrieval index integrity check failed")
        counts = {
            name: int(connection.execute(f"SELECT count(*) FROM {name}").fetchone()[0])
            for name in ("passages", "passages_fts")
        }
        if counts["passages"] != passage_count or counts["passages_fts"] != passage_count:
            raise ValueError("retrieval index passage or FTS count is incompatible")
        if (
            connection.execute(
                "SELECT rowid FROM passages_fts EXCEPT SELECT id FROM passages"
            ).fetchone()
            or connection.execute(
                "SELECT id FROM passages EXCEPT SELECT rowid FROM passages_fts"
            ).fetchone()
        ):
            raise ValueError("retrieval index FTS rows do not match passage rows")
        if connection.execute(
            """SELECT 1 FROM passages_fts fts JOIN passages passage ON passage.id = fts.rowid
               WHERE fts.title != passage.title OR fts.heading != passage.heading
                  OR fts.body != passage.body LIMIT 1"""
        ).fetchone():
            raise ValueError("retrieval index FTS content does not match passages")
        actual_ids = {str(row[0]) for row in connection.execute("SELECT passage_id FROM passages")}
        if actual_ids != lore_ids:
            raise ValueError("retrieval index passages do not match the release")
        if connection.execute(
            """SELECT 1 FROM context_coordinates coordinate
               LEFT JOIN passages passage ON passage.passage_id = coordinate.passage_id
               WHERE (coordinate.availability = 'lore' AND (coordinate.passage_id IS NULL
                      OR passage.passage_id IS NULL))
                  OR (coordinate.availability = 'non-lore-or-excluded'
                      AND coordinate.passage_id IS NOT NULL) LIMIT 1"""
        ).fetchone():
            raise ValueError("retrieval index context coordinates are malformed")
        if connection.execute(
            """SELECT 1 FROM passages passage LEFT JOIN context_coordinates coordinate
               ON coordinate.passage_id = passage.passage_id
               AND coordinate.article_artifact_id = passage.article_artifact_id
               AND coordinate.heading_path = passage.heading_path
               AND coordinate.ordinal = passage.ordinal
               WHERE coordinate.passage_id IS NULL OR coordinate.availability != 'lore' LIMIT 1"""
        ).fetchone():
            raise ValueError("retrieval index lacks a matching lore coordinate")
        if connection.execute(
            """SELECT 1 FROM context_coordinates coordinate JOIN passages passage
               ON passage.passage_id = coordinate.passage_id
               WHERE coordinate.article_artifact_id != passage.article_artifact_id
                  OR coordinate.heading_path != passage.heading_path
                  OR coordinate.ordinal != passage.ordinal LIMIT 1"""
        ).fetchone():
            raise ValueError("retrieval index coordinate disagreement")
    except sqlite3.DatabaseError as error:
        raise ValueError("malformed retrieval index") from error


def _validate_fts_integrity(connection: sqlite3.Connection) -> None:
    """Check the FTS index itself without ever exposing a writable source connection."""
    copy = sqlite3.connect(":memory:")
    try:
        connection.backup(copy)
        copy.execute("INSERT INTO passages_fts(passages_fts, rank) VALUES ('integrity-check', 1)")
    except sqlite3.DatabaseError as error:
        raise ValueError("retrieval index FTS integrity check failed") from error
    finally:
        copy.close()


class RetrievalIndex:
    """A validated read-only view of exactly one immutable corpus release."""

    def __init__(
        self, connection: sqlite3.Connection, metadata: IndexMetadata, config: _Config
    ) -> None:
        self._connection = connection
        self.metadata = metadata
        self._config = config

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> RetrievalIndex:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def _query(query: str, mode: str) -> str | None:
        if not isinstance(query, str):
            raise ValueError("search query must be plain text")
        terms = _WORDS.findall(query)
        if not terms:
            return None
        quoted = ['"' + term.replace('"', '""') + '"' for term in terms]
        separator = " AND " if mode == "all-terms" else " OR "
        return separator.join(quoted)

    def search(self, query: str) -> list[SearchResult]:
        """Search approved lore with fixed, operator-owned ranking and bounds."""
        settings = self._config.retrieval
        if settings.query_mode not in {"all-terms", "any-terms"}:
            raise ValueError("unsupported retrieval query mode")
        if not isinstance(settings.result_limit, int) or not 1 <= settings.result_limit <= 50:
            raise ValueError("invalid retrieval result limit")
        if settings.tie_breaker not in {"passage-id", "title-then-passage-id"}:
            raise ValueError("unsupported retrieval tie breaker")
        match = self._query(query, settings.query_mode)
        if match is None:
            return []
        order = (
            "rank ASC, passage.title COLLATE NOCASE ASC, passage.passage_id ASC"
            if settings.tie_breaker == "title-then-passage-id"
            else "rank ASC, passage.passage_id ASC"
        )
        rows = self._connection.execute(
            f"""SELECT passage.*, bm25(passages_fts, ?, ?, ?) AS rank
                FROM passages_fts JOIN passages passage ON passage.id = passages_fts.rowid
                WHERE passages_fts MATCH ? ORDER BY {order} LIMIT ?""",
            (
                settings.title_weight,
                settings.heading_weight,
                settings.body_weight,
                match,
                settings.result_limit,
            ),
        ).fetchall()
        return [SearchResult(_evidence(row), float(row["rank"])) for row in rows]

    def _neighbor(
        self, target: EvidencePassage, ordinal: int
    ) -> tuple[EvidencePassage | None, str | None]:
        row = self._connection.execute(
            """SELECT * FROM context_coordinates WHERE article_artifact_id = ?
               AND heading_path = ? AND ordinal = ?""",
            (target.article_artifact_id, _canonical_json(target.heading_path), ordinal),
        ).fetchone()
        if row is None:
            edges = self._connection.execute(
                """SELECT min(ordinal), max(ordinal) FROM context_coordinates
                   WHERE article_artifact_id = ? AND heading_path = ?""",
                (target.article_artifact_id, _canonical_json(target.heading_path)),
            ).fetchone()
            if edges is None or edges[0] is None or ordinal < edges[0] or ordinal > edges[1]:
                return None, "section-edge"
            return None, "ordinal-gap"
        if row["availability"] != "lore":
            return None, "non-lore-or-excluded"
        passage = self._connection.execute(
            "SELECT * FROM passages WHERE passage_id = ?", (row["passage_id"],)
        ).fetchone()
        if passage is None:
            raise ValueError("retrieval index has a dangling lore coordinate")
        return _evidence(passage), None

    def context(self, passage_id: str) -> ContextResult:
        """Return one immediate, same-section neighbor on each side when available."""
        if not isinstance(passage_id, str) or not passage_id:
            raise ValueError("passage id must be a non-empty string")
        row = self._connection.execute(
            "SELECT * FROM passages WHERE passage_id = ?", (passage_id,)
        ).fetchone()
        if row is None:
            raise ValueError("unknown lore passage id")
        target = _evidence(row)
        before, before_boundary = self._neighbor(target, target.ordinal - 1)
        after, after_boundary = self._neighbor(target, target.ordinal + 1)
        return ContextResult(target, before, before_boundary, after, after_boundary)


def _article_metadata(manifest: Path) -> dict[str, tuple[int, int, str]]:
    document = json.loads(manifest.read_text())
    result: dict[str, tuple[int, int, str]] = {}
    for article in document["articles"]:
        result[str(article["article_artifact_id"])] = (
            int(article["page_id"]),
            int(article["revision_id"]),
            str(article["revision_timestamp"]),
        )
    return result


def _project(connection: sqlite3.Connection, manifest: Path, lore_ids: set[str]) -> None:
    corpus = load_corpus(manifest.parent / "articles")
    article_metadata = _article_metadata(manifest)
    seen_coordinates: set[tuple[str, str, int]] = set()
    for passage in corpus.passages:
        heading_path = _canonical_json(passage.heading_path)
        coordinate = (passage.article_id, heading_path, passage.paragraph_ordinal)
        if coordinate in seen_coordinates:
            raise ValueError("article artifacts contain duplicate passage coordinates")
        seen_coordinates.add(coordinate)
        if passage.passage_id not in lore_ids:
            connection.execute(
                """INSERT INTO context_coordinates
                   (article_artifact_id, heading_path, ordinal, availability, passage_id)
                   VALUES (?, ?, ?, 'non-lore-or-excluded', NULL)""",
                coordinate,
            )
            continue
        try:
            page_id, revision_id, timestamp = article_metadata[passage.article_id]
        except KeyError as error:
            raise ValueError("release lore passage has no retained article metadata") from error
        cursor = connection.execute(
            """INSERT INTO passages
               (passage_id, article_artifact_id, title, heading_path, heading, ordinal, body,
                page_id, revision_id, revision_timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                passage.passage_id,
                passage.article_id,
                passage.article_title,
                heading_path,
                " > ".join(passage.heading_path),
                passage.paragraph_ordinal,
                passage.text,
                page_id,
                revision_id,
                timestamp,
            ),
        )
        connection.execute(
            """INSERT INTO context_coordinates
               (article_artifact_id, heading_path, ordinal, availability, passage_id)
               VALUES (?, ?, ?, 'lore', ?)""",
            (*coordinate, passage.passage_id),
        )
        connection.execute(
            "INSERT INTO passages_fts(rowid, title, heading, body) VALUES (?, ?, ?, ?)",
            (
                cursor.lastrowid,
                passage.article_title,
                " > ".join(passage.heading_path),
                passage.text,
            ),
        )
    missing = lore_ids - {passage.passage_id for passage in corpus.passages}
    if missing:
        raise ValueError("release contains a lore passage absent from retained artifacts")


def _open_readonly(path: Path) -> sqlite3.Connection:
    try:
        connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
    except (OSError, sqlite3.DatabaseError) as error:
        raise ValueError("cannot open retrieval index read-only") from error


def _validate_connection(
    connection: sqlite3.Connection, release: ReleaseResult, config: _Config, lore_ids: set[str]
) -> IndexMetadata:
    values = _metadata_from(connection)
    expected = _expected_metadata(release, config)
    if values != expected:
        raise ValueError("retrieval index is incompatible with the release or configuration")
    metadata = _metadata(values)
    _validate_content(connection, lore_ids, release.passage_count)
    _validate_fts_integrity(connection)
    return metadata


def _validate_staged_index(
    path: Path, release: ReleaseResult, config: _Config, lore_ids: set[str]
) -> IndexMetadata:
    connection = _open_readonly(path)
    try:
        return _validate_connection(connection, release, config, lore_ids)
    finally:
        connection.close()


def build_index(*, manifest: Path, output: Path, config: _Config) -> IndexBuildResult:
    """Validate, stage, verify, then atomically publish a new immutable index."""
    release = _validated_release(manifest)
    lore_ids = _lore_ids(manifest)
    if len(lore_ids) != release.passage_count:
        raise ValueError("release lore passage count is inconsistent")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite retrieval index: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    expected = _expected_metadata(release, config)
    with tempfile.TemporaryDirectory(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    ) as temp:
        staged = Path(temp) / output.name
        connection = sqlite3.connect(staged)
        try:
            _schema(connection, expected["tokenizer"])
            with connection:
                connection.executemany(
                    "INSERT INTO index_metadata(key, value) VALUES (?, ?)", expected.items()
                )
                _project(connection, manifest, lore_ids)
        finally:
            connection.close()
        metadata = _validate_staged_index(staged, release, config, lore_ids)
        try:
            os.link(staged, output)
        except FileExistsError as error:
            raise FileExistsError(f"refusing to overwrite retrieval index: {output}") from error
    return IndexBuildResult(metadata, output)


def open_index(*, manifest: Path, index: Path, config: _Config) -> RetrievalIndex:
    """Open a compatible published index read-only, or fail closed before retrieval."""
    release = _validated_release(manifest)
    lore_ids = _lore_ids(manifest)
    if not index.is_file():
        raise ValueError(f"retrieval index does not exist: {index}")
    connection = _open_readonly(index)
    try:
        metadata = _validate_connection(connection, release, config, lore_ids)
    except Exception:
        connection.close()
        raise
    return RetrievalIndex(connection, metadata, config)
