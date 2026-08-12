import json
import io
import re
import sqlite3

import pytest

import middle_earth_travel_agency.corpus_curation as curation
from middle_earth_travel_agency.corpus_curation import (
    CLASSIFICATIONS,
    CurationState,
    KeyGuard,
    evidence_snapshot,
    load_corpus,
    render,
    summary,
)


def _artifact(article_id="article-one", title="Zeta", passages=None):
    return {
        "article_artifact_id": article_id,
        "canonical_title": title,
        "extracted_passages": passages
        if passages is not None
        else [
            {
                "article_artifact_id": article_id,
                "passage_id": f"{article_id}-two",
                "heading_path": ["History"],
                "paragraph_ordinal": 2,
                "normalized_text": "Second paragraph.",
            },
            {
                "article_artifact_id": article_id,
                "passage_id": f"{article_id}-one",
                "heading_path": ["Lead"],
                "paragraph_ordinal": 1,
                "normalized_text": "First paragraph.",
            },
        ],
    }


def _write(directory, name, document):
    directory.mkdir(exist_ok=True)
    (directory / name).write_text(json.dumps(document))


def test_loads_valid_artifacts_in_deterministic_article_and_passage_order(tmp_path):
    articles = tmp_path / "articles"
    _write(articles, "z.json", _artifact())
    _write(articles, "a.json", _artifact("article-two", "Alpha"))

    corpus = load_corpus(articles)

    assert [passage.passage_id for passage in corpus.passages] == [
        "article-two-two",
        "article-two-one",
        "article-one-two",
        "article-one-one",
    ]


def test_preserves_source_order_when_heading_ordinals_restart(tmp_path):
    articles = tmp_path / "articles"
    _write(
        articles,
        "one.json",
        _artifact(
            passages=[
                {
                    "article_artifact_id": "article-one",
                    "passage_id": "lead",
                    "heading_path": ["Lead"],
                    "paragraph_ordinal": 1,
                    "normalized_text": "Lead.",
                },
                {
                    "article_artifact_id": "article-one",
                    "passage_id": "history",
                    "heading_path": ["History"],
                    "paragraph_ordinal": 1,
                    "normalized_text": "History.",
                },
                {
                    "article_artifact_id": "article-one",
                    "passage_id": "later",
                    "heading_path": ["History"],
                    "paragraph_ordinal": 2,
                    "normalized_text": "Later.",
                },
            ],
        ),
    )

    assert [passage.passage_id for passage in load_corpus(articles).passages] == [
        "lead",
        "history",
        "later",
    ]


@pytest.mark.parametrize("change", ["missing-text", "wrong-article", "duplicate"])
def test_rejects_invalid_artifact_fields(tmp_path, change):
    articles = tmp_path / "articles"
    document = _artifact()
    if change == "missing-text":
        del document["extracted_passages"][0]["normalized_text"]
    elif change == "wrong-article":
        document["extracted_passages"][0]["article_artifact_id"] = "other"
    else:
        document["extracted_passages"].append(document["extracted_passages"][0].copy())
    _write(articles, "bad.json", document)

    with pytest.raises(ValueError):
        load_corpus(articles)


def test_records_auditable_decision_and_exact_resume(tmp_path):
    articles = tmp_path / "articles"
    _write(articles, "one.json", _artifact())
    corpus = load_corpus(articles)
    database = tmp_path / "curation.sqlite"
    state = CurationState(database, corpus)
    first = corpus.passages[0]

    assert (
        state.record(first.passage_id, "l", "the question", first.text)
        == corpus.passages[1].passage_id
    )
    event = state.connection.execute("SELECT * FROM audit_events").fetchone()
    assert event["action"] == "classify"
    assert event["classification"] == CLASSIFICATIONS["l"]
    assert event["question"] == "the question"
    assert event["evidence"] == first.text
    state.close()

    resumed = CurationState(database, corpus)
    assert resumed.current_or_resume() == corpus.passages[1].passage_id
    resumed.close()


def test_evidence_snapshot_records_the_visible_target_and_context(tmp_path):
    articles = tmp_path / "articles"
    _write(articles, "one.json", _artifact())
    corpus = load_corpus(articles)
    state = CurationState(tmp_path / "state.sqlite", corpus)
    target = corpus.passages[1]
    snapshot = evidence_snapshot(target, corpus, rubric_id=state.rubric_id, more_context=False)

    state.record(target.passage_id, "l", "question", snapshot)

    stored = json.loads(state.connection.execute("SELECT evidence FROM audit_events").fetchone()[0])
    assert stored["rubric_id"] == "tolkien-corpus-rubric-v1"
    assert stored["article"] == {"id": target.article_id, "title": target.article_title}
    assert stored["target"]["id"] == target.passage_id
    assert stored["target"]["heading_path"] == list(target.heading_path)
    assert stored["preceding"][0]["id"] == corpus.passages[0].passage_id
    state.close()


def test_save_failure_rolls_back_audit_and_cursor(tmp_path):
    articles = tmp_path / "articles"
    _write(articles, "one.json", _artifact())
    corpus = load_corpus(articles)
    state = CurationState(tmp_path / "state.sqlite", corpus)
    first = corpus.passages[0]
    state.connection.execute(
        """CREATE TRIGGER reject_decision BEFORE INSERT ON audit_events
           WHEN NEW.action = 'classify' BEGIN SELECT RAISE(ABORT, 'disk full'); END"""
    )

    with pytest.raises(Exception, match="disk full"):
        state.record(first.passage_id, "l", "question", first.text)

    assert state.connection.execute("SELECT count(*) FROM audit_events").fetchone()[0] == 0
    assert state.current_passage_id() is None
    state.close()


def test_undo_is_append_only_and_restores_prior_decision(tmp_path):
    articles = tmp_path / "articles"
    _write(articles, "one.json", _artifact())
    corpus = load_corpus(articles)
    state = CurationState(tmp_path / "state.sqlite", corpus)
    first = corpus.passages[0]
    state.record(first.passage_id, "l", "question", first.text)
    state.record(first.passage_id, "a", "revised question", first.text)

    state.undo("undo question", first.text)

    events = state.connection.execute("SELECT * FROM audit_events ORDER BY id").fetchall()
    assert [event["action"] for event in events] == ["classify", "classify", "undo"]
    assert events[-1]["supersedes_event_id"] == events[-2]["id"]
    assert state.effective()[first.passage_id]["classification"] == CLASSIFICATIONS["l"]
    assert state.current_or_resume() == first.passage_id
    state.close()


def test_defer_is_not_a_classification_and_completion_counts_it(tmp_path):
    articles = tmp_path / "articles"
    _write(articles, "one.json", _artifact())
    corpus = load_corpus(articles)
    state = CurationState(tmp_path / "state.sqlite", corpus)
    state.record(corpus.passages[0].passage_id, "s", "question", corpus.passages[0].text)
    state.record(corpus.passages[1].passage_id, "r", "question", corpus.passages[1].text)

    counts = state.counts()
    assert counts["deferred"] == 1
    assert counts["reference or administrative material"] == 1
    assert counts["undecided"] == 0
    assert "deferred and undecided are excluded" in summary(counts)
    state.close()


def test_final_answer_completes_and_deferred_review_revisits_without_looping(tmp_path):
    articles = tmp_path / "articles"
    _write(articles, "one.json", _artifact())
    corpus = load_corpus(articles)
    state = CurationState(tmp_path / "state.sqlite", corpus)
    first, final = corpus.passages
    state.record(first.passage_id, "s", "question", first.text)
    assert state.record(final.passage_id, "r", "question", final.text) is None
    assert state.current_or_resume() is None
    assert state.current_or_resume(review_deferred=True) == first.passage_id
    assert state.record(first.passage_id, "s", "question", first.text, review_deferred=True) is None
    assert state.current_or_resume(review_deferred=True) == first.passage_id
    state.record(first.passage_id, "l", "question", first.text, review_deferred=True)
    assert state.current_or_resume(review_deferred=True) is None
    events = state.connection.execute("SELECT * FROM audit_events ORDER BY id").fetchall()
    assert events[-1]["supersedes_event_id"] == events[-2]["id"]
    state.close()


def test_refuses_incompatible_corpus(tmp_path):
    articles = tmp_path / "articles"
    _write(articles, "one.json", _artifact())
    corpus = load_corpus(articles)
    database = tmp_path / "state.sqlite"
    CurationState(database, corpus).close()
    _write(articles, "two.json", _artifact("article-two", "Two"))

    with pytest.raises(ValueError, match="incompatible artifact"):
        CurationState(database, load_corpus(articles))


def test_zero_passage_artifact_is_part_of_the_bound_corpus_identity(tmp_path):
    articles = tmp_path / "articles"
    _write(articles, "one.json", _artifact())
    database = tmp_path / "state.sqlite"
    CurationState(database, load_corpus(articles)).close()
    _write(articles, "empty.json", _artifact("empty-article", "Empty", passages=[]))

    with pytest.raises(ValueError, match="incompatible artifact"):
        CurationState(database, load_corpus(articles))

    changed_database = tmp_path / "changed.sqlite"
    CurationState(changed_database, load_corpus(articles)).close()
    _write(articles, "empty.json", _artifact("empty-article", "Renamed empty", passages=[]))
    with pytest.raises(ValueError, match="incompatible artifact"):
        CurationState(changed_database, load_corpus(articles))

    removed_database = tmp_path / "removed.sqlite"
    _write(articles, "empty.json", _artifact("empty-article", "Empty", passages=[]))
    CurationState(removed_database, load_corpus(articles)).close()
    (articles / "empty.json").unlink()
    with pytest.raises(ValueError, match="incompatible artifact"):
        CurationState(removed_database, load_corpus(articles))


def test_modes_keep_independent_resume_positions(tmp_path):
    articles = tmp_path / "articles"
    _write(articles, "one.json", _artifact())
    corpus = load_corpus(articles)
    state = CurationState(tmp_path / "state.sqlite", corpus)
    first, second = corpus.passages
    state.record(first.passage_id, "s", "question", first.text)
    assert state.current_passage_id() == second.passage_id
    assert state.current_passage_id(review_deferred=True) is None
    assert state.current_or_resume(review_deferred=True) == first.passage_id
    state.record(first.passage_id, "s", "question", first.text, review_deferred=True)
    assert state.current_passage_id(review_deferred=True) is None
    assert state.current_passage_id() == second.passage_id
    state.close()


def test_terminal_deferred_session_visits_each_redeferred_passage_once(tmp_path, monkeypatch):
    articles = tmp_path / "articles"
    _write(articles, "one.json", _artifact())
    corpus = load_corpus(articles)
    state = CurationState(tmp_path / "state.sqlite", corpus)
    for passage in corpus.passages:
        state.record(passage.passage_id, "s", "question", passage.text)

    class Input:
        def __init__(self):
            self.keys = iter(("s", "s"))

        def isatty(self):
            return True

        def fileno(self):
            return 0

        def read(self, _size):
            return next(self.keys)

    class Output(io.StringIO):
        def isatty(self):
            return True

    class Guard:
        def accept(self, _key):
            return True

    output = Output()
    monkeypatch.setattr(curation.termios, "tcgetattr", lambda _fd: ["terminal"])
    monkeypatch.setattr(curation.termios, "tcsetattr", lambda *_args: None)
    monkeypatch.setattr(curation.tty, "setraw", lambda _fd: None)
    monkeypatch.setattr(curation, "_flush_input", lambda _stream: None)
    monkeypatch.setattr(curation, "KeyGuard", Guard)

    curation.run_terminal(state, review_deferred=True, input_stream=Input(), output=output)

    assert output.getvalue().count("TARGET PASSAGE") == 2
    assert "CURATION SUMMARY" in output.getvalue()
    state.close()


def test_terminal_disconnect_returns_without_changing_state(tmp_path, monkeypatch):
    articles = tmp_path / "articles"
    _write(articles, "one.json", _artifact())
    state = CurationState(tmp_path / "state.sqlite", load_corpus(articles))

    class Input:
        def isatty(self):
            return True

        def fileno(self):
            return 0

        def read(self, _size):
            return ""

    class Output(io.StringIO):
        def isatty(self):
            return True

    restored = []
    monkeypatch.setattr(curation.termios, "tcgetattr", lambda _fd: ["terminal"])
    monkeypatch.setattr(curation.termios, "tcsetattr", lambda *_args: restored.append(True))
    monkeypatch.setattr(curation.tty, "setraw", lambda _fd: None)

    output = Output()
    curation.run_terminal(state, input_stream=Input(), output=output)

    assert state.connection.execute("SELECT count(*) FROM audit_events").fetchone()[0] == 0
    assert restored == [True]
    assert "\r\n" in output.getvalue()
    assert output.getvalue().startswith("\x1b[?25l")
    assert output.getvalue().endswith("\x1b[?25h")
    state.close()


def test_render_has_context_progress_and_unmistakable_status(tmp_path):
    articles = tmp_path / "articles"
    _write(articles, "one.json", _artifact())
    corpus = load_corpus(articles)
    frame = render(
        corpus.passages[0],
        corpus,
        rubric_id="test-rubric",
        more_context=False,
        status="SAVED: internal lore",
    )

    assert "Article 1/1" in frame
    assert "Passage 1/2" in frame
    assert "Overall 1/2" in frame
    assert "Rubric · test-rubric" in frame
    assert "Question · Classify this passage under the current corpus-curation rubric." in frame
    assert "Source · Zeta › History" in frame
    assert "TARGET PASSAGE" in frame
    assert "STATUS · SAVED: internal lore" in frame
    assert "After · First paragraph." in frame


def test_compact_context_is_snippeted_but_expanded_context_is_not(tmp_path):
    articles = tmp_path / "articles"
    long = "x" * 300
    _write(
        articles,
        "one.json",
        _artifact(
            passages=[
                {
                    "article_artifact_id": "article-one",
                    "passage_id": "one",
                    "heading_path": [],
                    "paragraph_ordinal": 1,
                    "normalized_text": long,
                },
                {
                    "article_artifact_id": "article-one",
                    "passage_id": "two",
                    "heading_path": [],
                    "paragraph_ordinal": 2,
                    "normalized_text": "Target.",
                },
            ]
        ),
    )
    corpus = load_corpus(articles)

    compact = render(
        corpus.passages[1], corpus, rubric_id="rubric", more_context=False, status="Ready"
    )
    expanded = render(
        corpus.passages[1], corpus, rubric_id="rubric", more_context=True, status="Ready"
    )

    assert "... [truncated]" in compact
    assert "... [truncated]" not in expanded
    assert long[:70] in expanded
    assert long[-70:] in expanded


def test_render_reserves_a_column_wraps_target_and_bounds_compact_context(tmp_path):
    articles = tmp_path / "articles"
    target = "target " * 45
    context = "context " * 45
    _write(
        articles,
        "one.json",
        _artifact(
            passages=[
                {
                    "article_artifact_id": "article-one",
                    "passage_id": "before",
                    "heading_path": [],
                    "paragraph_ordinal": 1,
                    "normalized_text": context,
                },
                {
                    "article_artifact_id": "article-one",
                    "passage_id": "target",
                    "heading_path": [],
                    "paragraph_ordinal": 2,
                    "normalized_text": target,
                },
            ]
        ),
    )
    corpus = load_corpus(articles)
    frame = render(
        corpus.passages[1], corpus, rubric_id="rubric", more_context=False, status="Ready", width=40
    )

    plain = re.sub(r"\x1b\[[0-9;]*m", "", frame)
    assert all(len(line) <= 39 for line in plain.splitlines())
    assert "target target" in frame
    assert frame.count("Before ·") == 1
    snapshot = json.loads(
        evidence_snapshot(
            corpus.passages[1], corpus, rubric_id="rubric", more_context=False, width=40
        )
    )
    assert snapshot["preceding"][0]["text"].endswith("... [truncated]")


def test_render_style_is_opt_in_and_no_color_disables_terminal_style(tmp_path, monkeypatch):
    articles = tmp_path / "articles"
    _write(articles, "one.json", _artifact())
    corpus = load_corpus(articles)
    plain = render(
        corpus.passages[0], corpus, rubric_id="rubric", more_context=False, status="Ready"
    )
    styled = render(
        corpus.passages[0],
        corpus,
        rubric_id="rubric",
        more_context=False,
        status="Ready",
        style=True,
    )
    assert "\x1b[" not in plain
    assert "\x1b[" in styled
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert curation._color_enabled()
    monkeypatch.setenv("NO_COLOR", "1")
    assert not curation._color_enabled()


def test_terminal_width_defends_against_a_bogus_tiny_report(monkeypatch):
    class Output:
        def fileno(self):
            return 1

    monkeypatch.setattr(
        curation.os, "get_terminal_size", lambda _fd: curation.os.terminal_size((1, 24))
    )

    assert curation._terminal_width(Output()) == 40


def test_key_guard_drops_only_held_repeated_action_key():
    guard = KeyGuard()
    assert guard.accept("l", 1.0)
    assert not guard.accept("l", 1.5)
    assert guard.accept("a", 1.51)
    assert guard.accept("l", 2.8)


def test_loader_reports_structural_artifact_errors(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        load_corpus(tmp_path / "missing")

    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValueError, match="no JSON"):
        load_corpus(empty)

    cases = {
        "invalid-json": ("{", "invalid JSON"),
        "not-object": (json.dumps([]), "must contain an object"),
        "missing-id": (json.dumps({}), "article_artifact_id"),
        "missing-passages": (
            json.dumps({"article_artifact_id": "article", "canonical_title": "Title"}),
            "extracted_passages",
        ),
        "non-object-passage": (
            json.dumps(_artifact(passages=["paragraph"])),
            "non-object passage",
        ),
    }
    for name, (content, message) in cases.items():
        directory = tmp_path / name
        directory.mkdir()
        (directory / "article.json").write_text(content)
        with pytest.raises(ValueError, match=message):
            load_corpus(directory)

    duplicate_articles = tmp_path / "duplicate-articles"
    _write(duplicate_articles, "one.json", _artifact(passages=[]))
    _write(duplicate_articles, "two.json", _artifact(passages=[]))
    with pytest.raises(ValueError, match="duplicate article"):
        load_corpus(duplicate_articles)

    invalid_ordinal = _artifact()
    invalid_ordinal["extracted_passages"][0]["paragraph_ordinal"] = -1
    ordinal_dir = tmp_path / "ordinal"
    _write(ordinal_dir, "article.json", invalid_ordinal)
    with pytest.raises(ValueError, match="paragraph_ordinal"):
        load_corpus(ordinal_dir)

    invalid_heading = _artifact()
    invalid_heading["extracted_passages"][0]["heading_path"] = [1]
    heading_dir = tmp_path / "heading"
    _write(heading_dir, "article.json", invalid_heading)
    with pytest.raises(ValueError, match="heading_path"):
        load_corpus(heading_dir)


def test_state_migrates_legacy_cursor_and_validates_operator_actions(tmp_path):
    articles = tmp_path / "articles"
    _write(articles, "one.json", _artifact())
    corpus = load_corpus(articles)
    database = tmp_path / "legacy.sqlite"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE curation_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE audit_events (
          id INTEGER PRIMARY KEY, action TEXT NOT NULL, passage_id TEXT NOT NULL,
          classification TEXT, rubric_id TEXT NOT NULL, question TEXT NOT NULL,
          evidence TEXT NOT NULL, semantic_answer TEXT NOT NULL, created_at TEXT NOT NULL,
          supersedes_event_id INTEGER REFERENCES audit_events(id)
        );
        CREATE TABLE session_state (
          singleton INTEGER PRIMARY KEY CHECK (singleton = 1), current_passage_id TEXT
        );
        """
    )
    connection.executemany(
        "INSERT INTO curation_meta VALUES (?, ?)",
        (("corpus_fingerprint", corpus.fingerprint), ("rubric_id", "tolkien-corpus-rubric-v1")),
    )
    connection.execute("INSERT INTO session_state VALUES (1, ?)", (corpus.passages[0].passage_id,))
    connection.commit()
    connection.close()

    state = CurationState(database, corpus)
    assert state.current_passage_id() == corpus.passages[0].passage_id
    assert state.next_undecided() == corpus.passages[0].passage_id
    assert state.undo("question", "evidence") is None
    with pytest.raises(ValueError, match="unsupported curation key"):
        state.record(corpus.passages[0].passage_id, "x", "question", "evidence")
    with pytest.raises(ValueError, match="unknown corpus passage"):
        state.record("missing", "l", "question", "evidence")
    state.close()

    with pytest.raises(ValueError, match="incompatible rubric"):
        CurationState(database, corpus, rubric_id="replacement-rubric")


def test_terminal_controls_and_save_failure_status(tmp_path, monkeypatch):
    articles = tmp_path / "articles"
    _write(articles, "one.json", _artifact())
    state = CurationState(tmp_path / "state.sqlite", load_corpus(articles))

    class Input:
        def __init__(self, keys):
            self.keys = iter(keys)

        def isatty(self):
            return True

        def fileno(self):
            return 0

        def read(self, _size):
            return next(self.keys, "")

    class Output(io.StringIO):
        def isatty(self):
            return True

    class Guard:
        def accept(self, _key):
            return True

    monkeypatch.setattr(curation.termios, "tcgetattr", lambda _fd: ["terminal"])
    monkeypatch.setattr(curation.termios, "tcsetattr", lambda *_args: None)
    monkeypatch.setattr(curation.tty, "setraw", lambda _fd: None)
    monkeypatch.setattr(curation, "_flush_input", lambda _stream: None)
    monkeypatch.setattr(curation, "KeyGuard", Guard)

    output = Output()
    curation.run_terminal(
        state,
        input_stream=Input((" ", "?", "u", "l", "u", "d")),
        output=output,
    )
    frame_history = output.getvalue()
    assert "More context shown." in frame_history
    assert "L=in-world claims" in frame_history
    assert "Nothing to undo." in frame_history
    assert "UNDO SAVED" in frame_history
    assert "CURATION SUMMARY" in frame_history
    state.close()

    failing_state = CurationState(tmp_path / "failing.sqlite", load_corpus(articles))
    failing_state.connection.execute(
        """CREATE TRIGGER reject_decision BEFORE INSERT ON audit_events
           WHEN NEW.action = 'classify' BEGIN SELECT RAISE(ABORT, 'disk full'); END"""
    )
    failure_output = Output()
    curation.run_terminal(
        failing_state,
        input_stream=Input(("l", "q")),
        output=failure_output,
    )
    assert "SAVE FAILED" in failure_output.getvalue()
    failing_state.close()

    with pytest.raises(ValueError, match="interactive TTY"):
        curation.run_terminal(state, input_stream=io.StringIO(), output=Output())


def test_flush_input_ignores_unsupported_stream(monkeypatch):
    class Stream:
        def fileno(self):
            return 7

    monkeypatch.setattr(
        curation.termios,
        "tcflush",
        lambda *_args: (_ for _ in ()).throw(curation.termios.error("unsupported")),
    )

    curation._flush_input(Stream())
