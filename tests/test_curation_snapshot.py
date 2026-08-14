import json
import sqlite3
from pathlib import Path

import pytest

from middle_earth_travel_agency.corpus_curation import Corpus, CurationState, Passage
from middle_earth_travel_agency.curation_snapshot import export_snapshot, load_snapshot


def _corpus() -> Corpus:
    return Corpus(
        (
            Passage("article-1", "Áragorn", "passage-1", ("Lead",), 1, "First evidence"),
            Passage("article-1", "Áragorn", "passage-2", ("History",), 2, "Second evidence"),
        ),
        "f" * 64,
    )


def _state_database(path: Path) -> None:
    state = CurationState(path, _corpus())
    try:
        state.record("passage-1", "l", "Question one", "First evidence")
        state.record("passage-1", "w", "Question two", "First evidence")
        state.undo("Undo question", "First evidence")
        state.record("passage-2", "s", "Question three", "Second evidence")
    finally:
        state.close()


def _table_rows(path: Path, table: str) -> list[tuple]:
    connection = sqlite3.connect(path)
    try:
        return list(connection.execute(f"SELECT * FROM {table} ORDER BY rowid"))
    finally:
        connection.close()


def test_export_is_deterministic_and_load_round_trips_every_table(tmp_path):
    source = tmp_path / "source.sqlite"
    snapshot = tmp_path / "curation.jsonl"
    restored = tmp_path / "restored.sqlite"
    _state_database(source)

    exported = export_snapshot(source, snapshot)
    first_bytes = snapshot.read_bytes()
    exported_again = export_snapshot(source, snapshot)
    loaded = load_snapshot(snapshot, restored)

    assert exported.audit_events == 4
    assert exported.metadata_records == 2
    assert exported_again == exported
    assert loaded == exported
    assert snapshot.read_bytes() == first_bytes
    assert "Áragorn" not in snapshot.read_text()  # evidence is stored, not article display context
    assert snapshot.read_text().splitlines()[0] == (
        '{"record_type":"curation_snapshot","schema_version":1}'
    )
    for table in ("curation_meta", "audit_events", "session_state"):
        assert _table_rows(restored, table) == _table_rows(source, table)

    state = CurationState(restored, _corpus())
    try:
        assert state.counts()["internal lore"] == 1
        assert state.counts()["deferred"] == 1
    finally:
        state.close()


def test_load_refuses_to_overwrite_existing_database(tmp_path):
    source = tmp_path / "source.sqlite"
    snapshot = tmp_path / "curation.jsonl"
    destination = tmp_path / "destination.sqlite"
    _state_database(source)
    export_snapshot(source, snapshot)
    destination.write_text("retain me")

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        load_snapshot(snapshot, destination)

    assert destination.read_text() == "retain me"


def test_export_rejects_missing_or_incompatible_database(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        export_snapshot(tmp_path / "missing.sqlite", tmp_path / "snapshot.jsonl")

    invalid = tmp_path / "invalid.sqlite"
    connection = sqlite3.connect(invalid)
    connection.execute("CREATE TABLE curation_meta (wrong TEXT)")
    connection.close()
    with pytest.raises(ValueError, match="unsupported columns"):
        export_snapshot(invalid, tmp_path / "snapshot.jsonl")

    corrupt = tmp_path / "corrupt.sqlite"
    _state_database(corrupt)
    connection = sqlite3.connect(corrupt)
    connection.execute("UPDATE audit_events SET classification = 'bad' WHERE id = 1")
    connection.commit()
    connection.close()
    with pytest.raises(ValueError, match="invalid classification"):
        export_snapshot(corrupt, tmp_path / "snapshot.jsonl")
    assert not (tmp_path / "snapshot.jsonl").exists()


def _write_records(path: Path, records: list[object]) -> None:
    path.write_text("".join(json.dumps(record) + "\n" for record in records))


def _header() -> dict[str, object]:
    return {"record_type": "curation_snapshot", "schema_version": 1}


def _metadata() -> list[dict[str, object]]:
    return [
        {"record_type": "metadata", "key": "corpus_fingerprint", "value": "fingerprint"},
        {"record_type": "metadata", "key": "rubric_id", "value": "rubric-v1"},
    ]


def _event(**changes) -> dict[str, object]:
    value = {
        "record_type": "audit_event",
        "id": 1,
        "action": "classify",
        "passage_id": "passage-1",
        "classification": "internal lore",
        "rubric_id": "rubric-v1",
        "question": "Question",
        "evidence": "Evidence",
        "semantic_answer": "internal lore",
        "created_at": "2026-08-13T12:00:00+00:00",
        "supersedes_event_id": None,
    }
    value.update(changes)
    return value


def _session(**changes) -> dict[str, object]:
    value = {
        "record_type": "session_state",
        "singleton": 1,
        "current_passage_id": None,
        "current_undecided_passage_id": None,
        "current_deferred_passage_id": None,
    }
    value.update(changes)
    return value


@pytest.mark.parametrize(
    ("records", "message"),
    [
        ([], "metadata keys"),
        ([[]], "must contain an object"),
        ([{"record_type": "curation_snapshot", "schema_version": 2}], "unsupported"),
        ([{**_header(), "extra": True}], "unexpected fields"),
        ([*_metadata(), _header()], "unexpected fields"),
        ([_header(), *_metadata(), {"record_type": "mystery"}], "unknown record_type"),
        ([_header(), *_metadata()], "missing session"),
        ([_header(), *_metadata(), _session(), _session()], "multiple session"),
        ([_header(), *_metadata(), _session(singleton=2)], "singleton"),
        (
            [_header(), *_metadata(), _session(current_passage_id=4)],
            "must be a string or null",
        ),
        (
            [_header(), *_metadata(), _session(), _event()],
            "audit events must precede session",
        ),
        (
            [_header(), _metadata()[0], _metadata()[0], _metadata()[1], _session()],
            "duplicate metadata",
        ),
        (
            [_header(), *_metadata(), _event(), _metadata()[0], _session()],
            "metadata records must precede",
        ),
        (
            [_header(), *_metadata(), _event(id=0), _session()],
            "invalid audit event id",
        ),
        (
            [_header(), *_metadata(), _event(action="bad"), _session()],
            "invalid audit action",
        ),
        (
            [_header(), *_metadata(), _event(passage_id=""), _session()],
            "passage_id.*non-empty",
        ),
        (
            [_header(), *_metadata(), _event(classification="bad"), _session()],
            "invalid classification",
        ),
        (
            [
                _header(),
                *_metadata(),
                _event(action="defer", classification="internal lore"),
                _session(),
            ],
            "classification must be null",
        ),
        (
            [
                _header(),
                *_metadata(),
                _event(action="undo", classification=None),
                _session(),
            ],
            "undo must supersede",
        ),
        (
            [_header(), *_metadata(), _event(rubric_id="other"), _session()],
            "incompatible rubric",
        ),
    ],
)
def test_load_rejects_invalid_snapshot_records(tmp_path, records, message):
    snapshot = tmp_path / "bad.jsonl"
    _write_records(snapshot, records)

    with pytest.raises(ValueError, match=message):
        load_snapshot(snapshot, tmp_path / "state.sqlite")

    assert not (tmp_path / "state.sqlite").exists()


def test_load_rejects_invalid_json_blank_lines_and_missing_file(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        load_snapshot(tmp_path / "missing.jsonl", tmp_path / "state.sqlite")

    snapshot = tmp_path / "bad.jsonl"
    snapshot.write_text("not json\n")
    with pytest.raises(ValueError, match="invalid JSON"):
        load_snapshot(snapshot, tmp_path / "state.sqlite")

    snapshot.write_text(json.dumps(_header()) + "\n\n")
    with pytest.raises(ValueError, match="must not be blank"):
        load_snapshot(snapshot, tmp_path / "state.sqlite")


def test_load_validates_supersession_relationships(tmp_path):
    snapshot = tmp_path / "bad.jsonl"
    invalid_supersessions = [
        _event(id=2, supersedes_event_id="1"),
        _event(id=2, supersedes_event_id=1),
        _event(id=1),
        _event(id=1),
    ]
    messages = ["invalid supersedes_event_id", "supersedes an invalid", "invalid audit event id"]

    _write_records(snapshot, [_header(), *_metadata(), invalid_supersessions[0], _session()])
    with pytest.raises(ValueError, match=messages[0]):
        load_snapshot(snapshot, tmp_path / "one.sqlite")

    _write_records(snapshot, [_header(), *_metadata(), invalid_supersessions[1], _session()])
    with pytest.raises(ValueError, match=messages[1]):
        load_snapshot(snapshot, tmp_path / "two.sqlite")

    _write_records(
        snapshot,
        [_header(), *_metadata(), invalid_supersessions[2], invalid_supersessions[3], _session()],
    )
    with pytest.raises(ValueError, match=messages[2]):
        load_snapshot(snapshot, tmp_path / "three.sqlite")
