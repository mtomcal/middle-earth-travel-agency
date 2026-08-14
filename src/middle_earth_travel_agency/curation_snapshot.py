"""Deterministic JSONL snapshots of auditable corpus-curation state."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .corpus_curation import CLASSIFICATIONS, CURATION_SCHEMA_SQL


SCHEMA_VERSION = 1
META_KEYS = frozenset({"corpus_fingerprint", "rubric_id"})
AUDIT_COLUMNS = (
    "id",
    "action",
    "passage_id",
    "classification",
    "rubric_id",
    "question",
    "evidence",
    "semantic_answer",
    "created_at",
    "supersedes_event_id",
)
SESSION_COLUMNS = (
    "singleton",
    "current_passage_id",
    "current_undecided_passage_id",
    "current_deferred_passage_id",
)
TABLE_COLUMNS = {
    "curation_meta": ("key", "value"),
    "audit_events": AUDIT_COLUMNS,
    "session_state": SESSION_COLUMNS,
}


@dataclass(frozen=True)
class SnapshotResult:
    metadata_records: int
    audit_events: int


def _canonical_line(record: dict[str, object]) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _read_only_connection(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ValueError(f"curation state database does not exist: {path}")
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _validate_database_schema(connection: sqlite3.Connection) -> None:
    for table, expected in TABLE_COLUMNS.items():
        actual = tuple(row[1] for row in connection.execute(f"PRAGMA table_info({table})"))
        if actual != expected:
            raise ValueError(f"curation state table {table!r} has unsupported columns: {actual!r}")


def export_snapshot(state_db: Path, output: Path) -> SnapshotResult:
    """Write a byte-deterministic JSONL snapshot, replacing an older snapshot atomically."""
    connection = _read_only_connection(state_db)
    try:
        connection.execute("BEGIN")
        _validate_database_schema(connection)
        metadata = list(connection.execute("SELECT key, value FROM curation_meta ORDER BY key"))
        events = list(connection.execute("SELECT * FROM audit_events ORDER BY id"))
        sessions = list(connection.execute("SELECT * FROM session_state ORDER BY singleton"))
    finally:
        connection.close()

    metadata_keys = {row["key"] for row in metadata}
    if metadata_keys != META_KEYS:
        raise ValueError(f"curation metadata keys must be exactly {sorted(META_KEYS)!r}")
    if len(sessions) != 1 or sessions[0]["singleton"] != 1:
        raise ValueError("curation state must contain exactly the singleton session row")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(
                _canonical_line(
                    {"record_type": "curation_snapshot", "schema_version": SCHEMA_VERSION}
                )
            )
            for row in metadata:
                stream.write(
                    _canonical_line(
                        {"record_type": "metadata", "key": row["key"], "value": row["value"]}
                    )
                )
            for row in events:
                record = {column: row[column] for column in AUDIT_COLUMNS}
                record["record_type"] = "audit_event"
                stream.write(_canonical_line(record))
            session = {column: sessions[0][column] for column in SESSION_COLUMNS}
            session["record_type"] = "session_state"
            stream.write(_canonical_line(session))
        _parse_snapshot(temporary)
        temporary.replace(output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return SnapshotResult(len(metadata), len(events))


def _require_exact_keys(record: dict[str, Any], expected: set[str], line_number: int) -> None:
    if set(record) != expected:
        raise ValueError(f"snapshot line {line_number} has unexpected fields")


def _require_string(value: object, field: str, line_number: int) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"snapshot line {line_number} field {field!r} must be a non-empty string")
    return value


def _parse_snapshot(path: Path) -> tuple[dict[str, str], list[dict[str, Any]], dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"curation snapshot does not exist: {path}")
    metadata: dict[str, str] = {}
    events: list[dict[str, Any]] = []
    session: dict[str, Any] | None = None
    prior_events: dict[int, dict[str, Any]] = {}

    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                raise ValueError(f"snapshot line {line_number} must not be blank")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"snapshot line {line_number} is invalid JSON: {error.msg}"
                ) from error
            if not isinstance(record, dict):
                raise ValueError(f"snapshot line {line_number} must contain an object")
            record_type = record.get("record_type")
            if line_number == 1:
                _require_exact_keys(record, {"record_type", "schema_version"}, line_number)
                if record_type != "curation_snapshot" or record["schema_version"] != SCHEMA_VERSION:
                    raise ValueError("unsupported curation snapshot schema")
                continue
            if record_type == "metadata":
                if events or session is not None:
                    raise ValueError(
                        "snapshot metadata records must precede audit events and session state"
                    )
                _require_exact_keys(record, {"record_type", "key", "value"}, line_number)
                key = _require_string(record["key"], "key", line_number)
                value = _require_string(record["value"], "value", line_number)
                if key in metadata:
                    raise ValueError(f"snapshot contains duplicate metadata key {key!r}")
                metadata[key] = value
                continue
            if record_type == "audit_event":
                if session is not None:
                    raise ValueError("snapshot audit events must precede session state")
                _require_exact_keys(record, {"record_type", *AUDIT_COLUMNS}, line_number)
                event = {column: record[column] for column in AUDIT_COLUMNS}
                event_id = event["id"]
                if (
                    not isinstance(event_id, int)
                    or isinstance(event_id, bool)
                    or event_id <= 0
                    or event_id in prior_events
                    or (events and event_id <= events[-1]["id"])
                ):
                    raise ValueError(f"snapshot line {line_number} has an invalid audit event id")
                action = event["action"]
                if action not in {"classify", "defer", "undo"}:
                    raise ValueError(f"snapshot line {line_number} has an invalid audit action")
                passage_id = _require_string(event["passage_id"], "passage_id", line_number)
                rubric_id = _require_string(event["rubric_id"], "rubric_id", line_number)
                for field in ("question", "evidence", "semantic_answer", "created_at"):
                    _require_string(event[field], field, line_number)
                classification = event["classification"]
                if action == "classify" and classification not in CLASSIFICATIONS.values():
                    raise ValueError(f"snapshot line {line_number} has an invalid classification")
                if action != "classify" and classification is not None:
                    raise ValueError(
                        f"snapshot line {line_number} classification must be null for {action}"
                    )
                supersedes = event["supersedes_event_id"]
                if supersedes is not None:
                    if not isinstance(supersedes, int) or isinstance(supersedes, bool):
                        raise ValueError(
                            f"snapshot line {line_number} has an invalid supersedes_event_id"
                        )
                    prior = prior_events.get(supersedes)
                    if (
                        prior is None
                        or prior["action"] not in {"classify", "defer"}
                        or prior["passage_id"] != passage_id
                    ):
                        raise ValueError(
                            f"snapshot line {line_number} supersedes an invalid audit event"
                        )
                if action == "undo" and supersedes is None:
                    raise ValueError(
                        f"snapshot line {line_number} undo must supersede an audit event"
                    )
                if metadata.get("rubric_id") is not None and rubric_id != metadata["rubric_id"]:
                    raise ValueError(f"snapshot line {line_number} has an incompatible rubric id")
                events.append(event)
                prior_events[event_id] = event
                continue
            if record_type == "session_state":
                if session is not None:
                    raise ValueError("snapshot contains multiple session-state records")
                _require_exact_keys(record, {"record_type", *SESSION_COLUMNS}, line_number)
                session = {column: record[column] for column in SESSION_COLUMNS}
                if session["singleton"] != 1:
                    raise ValueError("snapshot session singleton must equal 1")
                for field in SESSION_COLUMNS[1:]:
                    if session[field] is not None and not isinstance(session[field], str):
                        raise ValueError(
                            f"snapshot line {line_number} field {field!r} must be a string or null"
                        )
                continue
            raise ValueError(f"snapshot line {line_number} has unknown record_type {record_type!r}")

    if set(metadata) != META_KEYS:
        raise ValueError(f"snapshot metadata keys must be exactly {sorted(META_KEYS)!r}")
    if session is None:
        raise ValueError("snapshot is missing session state")
    if any(event["rubric_id"] != metadata["rubric_id"] for event in events):
        raise ValueError("snapshot audit event has an incompatible rubric id")
    return metadata, events, session


def load_snapshot(snapshot: Path, state_db: Path) -> SnapshotResult:
    """Validate a JSONL snapshot and atomically create a new SQLite working database."""
    if state_db.exists():
        raise FileExistsError(f"refusing to overwrite curation state database: {state_db}")
    metadata, events, session = _parse_snapshot(snapshot)
    state_db.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{state_db.name}.", suffix=".tmp", dir=state_db.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        connection = sqlite3.connect(temporary)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(CURATION_SCHEMA_SQL)
            with connection:
                connection.executemany(
                    "INSERT INTO curation_meta (key, value) VALUES (?, ?)", metadata.items()
                )
                connection.executemany(
                    f"INSERT INTO audit_events ({', '.join(AUDIT_COLUMNS)}) "
                    f"VALUES ({', '.join('?' for _ in AUDIT_COLUMNS)})",
                    ([event[column] for column in AUDIT_COLUMNS] for event in events),
                )
                connection.execute(
                    f"INSERT INTO session_state ({', '.join(SESSION_COLUMNS)}) "
                    f"VALUES ({', '.join('?' for _ in SESSION_COLUMNS)})",
                    [session[column] for column in SESSION_COLUMNS],
                )
            if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise ValueError("loaded curation state has a foreign-key violation")
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("loaded curation state failed SQLite integrity checking")
        finally:
            connection.close()
        os.link(temporary, state_db)
        temporary.unlink()
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return SnapshotResult(len(metadata), len(events))
