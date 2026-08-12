"""Passage-only, terminal-based corpus curation with an append-only audit trail."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import sys
import termios
import textwrap
import time
import tty
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, TextIO


INITIAL_RUBRIC_ID = "tolkien-corpus-rubric-v1"
CLASSIFICATIONS = {
    "l": "internal lore",
    "w": "external creation history",
    "a": "analysis or reception",
    "d": "adaptation material",
    "r": "reference or administrative material",
}
ACTION_KEYS = frozenset((*CLASSIFICATIONS, "s"))


@dataclass(frozen=True)
class Passage:
    article_id: str
    article_title: str
    passage_id: str
    heading_path: tuple[str, ...]
    paragraph_ordinal: int
    text: str


@dataclass(frozen=True)
class Corpus:
    passages: tuple[Passage, ...]
    fingerprint: str


def _required(document: dict[str, object], name: str, kind: type) -> object:
    value = document.get(name)
    if not isinstance(value, kind) or (kind is str and not value.strip()):
        raise ValueError(f"artifact field {name!r} must be a non-empty {kind.__name__}")
    return value


def load_corpus(articles_dir: Path) -> Corpus:
    """Load and deterministically order immutable acquisition artifacts."""
    if not articles_dir.is_dir():
        raise ValueError(f"articles directory does not exist: {articles_dir}")
    articles: list[tuple[str, str, list[Passage]]] = []
    seen_articles: set[str] = set()
    seen_passages: set[str] = set()
    for path in sorted(articles_dir.glob("*.json")):
        try:
            document = json.loads(path.read_text())
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSON artifact {path.name}: {error.msg}") from error
        if not isinstance(document, dict):
            raise ValueError(f"artifact {path.name} must contain an object")
        article_id = _required(document, "article_artifact_id", str)
        title = _required(document, "canonical_title", str)
        raw_passages = document.get("extracted_passages")
        if not isinstance(raw_passages, list):
            raise ValueError(f"artifact {path.name} field 'extracted_passages' must be a list")
        if article_id in seen_articles:
            raise ValueError(f"duplicate article artifact id: {article_id}")
        seen_articles.add(article_id)
        loaded: list[Passage] = []
        for item in raw_passages:
            if not isinstance(item, dict):
                raise ValueError(f"artifact {path.name} has a non-object passage")
            passage_id = _required(item, "passage_id", str)
            text = _required(item, "normalized_text", str)
            ordinal = item.get("paragraph_ordinal")
            heading = item.get("heading_path")
            if not isinstance(ordinal, int) or ordinal < 0:
                raise ValueError(f"passage {passage_id} has invalid paragraph_ordinal")
            if not isinstance(heading, list) or not all(isinstance(part, str) for part in heading):
                raise ValueError(f"passage {passage_id} has invalid heading_path")
            if item.get("article_artifact_id") != article_id:
                raise ValueError(f"passage {passage_id} belongs to a different article")
            if passage_id in seen_passages:
                raise ValueError(f"duplicate passage id: {passage_id}")
            seen_passages.add(passage_id)
            loaded.append(Passage(article_id, title, passage_id, tuple(heading), ordinal, text))
        articles.append((title, article_id, loaded))
    if not articles:
        raise ValueError(f"no JSON article artifacts found in {articles_dir}")
    passages = tuple(
        passage
        for _title, _article_id, loaded in sorted(
            articles, key=lambda row: (row[0].casefold(), row[1])
        )
        # Extraction order is source order. paragraph_ordinal restarts under each heading.
        for passage in loaded
    )
    identity = [
        (
            title,
            article_id,
            [(p.passage_id, p.text, p.heading_path, p.paragraph_ordinal) for p in loaded],
        )
        for title, article_id, loaded in sorted(
            articles, key=lambda row: (row[0].casefold(), row[1])
        )
    ]
    fingerprint = hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()
    return Corpus(passages, fingerprint)


class CurationState:
    """SQLite state whose decision history is append-only, including undo."""

    def __init__(self, path: Path, corpus: Corpus, rubric_id: str = INITIAL_RUBRIC_ID) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()
        self._initialize(corpus, rubric_id)
        self.corpus = corpus
        self.rubric_id = rubric_id

    def close(self) -> None:
        self.connection.close()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS curation_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS audit_events (
              id INTEGER PRIMARY KEY, action TEXT NOT NULL, passage_id TEXT NOT NULL,
              classification TEXT, rubric_id TEXT NOT NULL, question TEXT NOT NULL,
              evidence TEXT NOT NULL, semantic_answer TEXT NOT NULL, created_at TEXT NOT NULL,
              supersedes_event_id INTEGER REFERENCES audit_events(id)
            );
            CREATE TABLE IF NOT EXISTS session_state (
              singleton INTEGER PRIMARY KEY CHECK (singleton = 1), current_passage_id TEXT,
              current_undecided_passage_id TEXT, current_deferred_passage_id TEXT
            );
            """
        )
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(session_state)")}
        for column in ("current_undecided_passage_id", "current_deferred_passage_id"):
            if column not in columns:
                self.connection.execute(f"ALTER TABLE session_state ADD COLUMN {column} TEXT")
        self.connection.execute(
            """UPDATE session_state SET current_undecided_passage_id = current_passage_id
               WHERE current_undecided_passage_id IS NULL AND current_passage_id IS NOT NULL"""
        )

    def _initialize(self, corpus: Corpus, rubric_id: str) -> None:
        existing = dict(self.connection.execute("SELECT key, value FROM curation_meta"))
        if existing:
            if existing.get("corpus_fingerprint") != corpus.fingerprint:
                raise ValueError("curation state belongs to an incompatible artifact set")
            if existing.get("rubric_id") != rubric_id:
                raise ValueError("curation state belongs to an incompatible rubric")
            return
        with self.connection:
            self.connection.executemany(
                "INSERT INTO curation_meta VALUES (?, ?)",
                (("corpus_fingerprint", corpus.fingerprint), ("rubric_id", rubric_id)),
            )
            self.connection.execute("INSERT INTO session_state (singleton) VALUES (1)")

    @staticmethod
    def _cursor_column(review_deferred: bool) -> str:
        return "current_deferred_passage_id" if review_deferred else "current_undecided_passage_id"

    def current_passage_id(self, *, review_deferred: bool = False) -> str | None:
        row = self.connection.execute(
            f"SELECT {self._cursor_column(review_deferred)} FROM session_state"
        ).fetchone()
        return row[0]

    def _active_rows(self) -> Iterable[sqlite3.Row]:
        return self.connection.execute(
            """SELECT event.* FROM audit_events event
               WHERE event.action IN ('classify', 'defer')
               AND NOT EXISTS (SELECT 1 FROM audit_events undo
                               WHERE undo.action = 'undo' AND undo.supersedes_event_id = event.id)
               ORDER BY event.id ASC"""
        )

    def effective(self) -> dict[str, sqlite3.Row]:
        # A later active decision for a passage explicitly supersedes the earlier one.
        result: dict[str, sqlite3.Row] = {}
        for row in self._active_rows():
            result[row["passage_id"]] = row
        return result

    def next_passage(
        self,
        after_id: str | None = None,
        *,
        review_deferred: bool = False,
        exclude_ids: frozenset[str] = frozenset(),
    ) -> str | None:
        ids = [passage.passage_id for passage in self.corpus.passages]
        effective = self.effective()
        start = ids.index(after_id) + 1 if after_id in ids else 0
        for passage_id in (*ids[start:], *ids[:start]):
            if passage_id in exclude_ids:
                continue
            row = effective.get(passage_id)
            if (review_deferred and row is not None and row["action"] == "defer") or (
                not review_deferred and row is None
            ):
                return passage_id
        return None

    def next_undecided(self, after_id: str | None = None) -> str | None:
        return self.next_passage(after_id)

    def current_or_resume(self, *, review_deferred: bool = False) -> str | None:
        current = self.current_passage_id(review_deferred=review_deferred)
        if current and current in {passage.passage_id for passage in self.corpus.passages}:
            return current
        return self.next_passage(review_deferred=review_deferred)

    def record(
        self,
        passage_id: str,
        key: str,
        question: str,
        evidence: str,
        *,
        review_deferred: bool = False,
        exclude_ids: frozenset[str] = frozenset(),
    ) -> str | None:
        if key not in ACTION_KEYS:
            raise ValueError(f"unsupported curation key: {key}")
        if passage_id not in {passage.passage_id for passage in self.corpus.passages}:
            raise ValueError(f"unknown corpus passage id: {passage_id}")
        action, classification = (
            ("defer", None) if key == "s" else ("classify", CLASSIFICATIONS[key])
        )
        with self.connection:
            prior = self.effective().get(passage_id)
            self.connection.execute(
                """INSERT INTO audit_events
                (action, passage_id, classification, rubric_id, question, evidence, semantic_answer,
                 created_at, supersedes_event_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    action,
                    passage_id,
                    classification,
                    self.rubric_id,
                    question,
                    evidence,
                    classification or "deferred for later review",
                    datetime.now(UTC).isoformat(),
                    prior["id"] if prior else None,
                ),
            )
            next_id = self.next_passage(
                passage_id,
                review_deferred=review_deferred,
                exclude_ids=exclude_ids | {passage_id},
            )
            self.connection.execute(
                f"UPDATE session_state SET {self._cursor_column(review_deferred)} = ? WHERE singleton = 1",
                (next_id,),
            )
        return self.current_passage_id(review_deferred=review_deferred)

    def undo(self, question: str, evidence: str, *, review_deferred: bool = False) -> str | None:
        row = self.connection.execute(
            """SELECT event.* FROM audit_events event WHERE event.action IN ('classify', 'defer')
               AND NOT EXISTS (SELECT 1 FROM audit_events undo
                               WHERE undo.action = 'undo' AND undo.supersedes_event_id = event.id)
               ORDER BY event.id DESC LIMIT 1"""
        ).fetchone()
        if row is None:
            return None
        with self.connection:
            self.connection.execute(
                """INSERT INTO audit_events
                (action, passage_id, rubric_id, question, evidence, semantic_answer, created_at,
                 supersedes_event_id) VALUES ('undo', ?, ?, ?, ?, ?, ?, ?)""",
                (
                    row["passage_id"],
                    self.rubric_id,
                    question,
                    evidence,
                    f"undo {row['action']}",
                    datetime.now(UTC).isoformat(),
                    row["id"],
                ),
            )
            self.connection.execute(
                f"UPDATE session_state SET {self._cursor_column(review_deferred)} = ? WHERE singleton = 1",
                (row["passage_id"],),
            )
        return row["passage_id"]

    def counts(self) -> dict[str, int]:
        values = {name: 0 for name in CLASSIFICATIONS.values()}
        values.update(deferred=0, undecided=0, total=len(self.corpus.passages))
        for row in self.effective().values():
            if row["action"] == "defer":
                values["deferred"] += 1
            else:
                values[row["classification"]] += 1
        values["undecided"] = (
            values["total"]
            - sum(values[name] for name in CLASSIFICATIONS.values())
            - values["deferred"]
        )
        return values


def question_for(passage: Passage) -> str:
    return "Classify this passage under the current corpus-curation rubric."


def _context(
    passage: Passage, corpus: Corpus, more_context: bool
) -> tuple[list[Passage], list[Passage]]:
    article = [item for item in corpus.passages if item.article_id == passage.article_id]
    article_index = article.index(passage)
    nearby = 2 if more_context else 1
    before = article[max(0, article_index - nearby) : article_index]
    after = article[article_index + 1 : article_index + 1 + nearby]
    return before, after


def _snippet(text: str, more_context: bool, width: int = 80) -> str:
    """Return exactly the context text that can be shown in the current frame."""
    if more_context:
        return text
    limit = max(16, min(160, width - 14))
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 16)].rstrip() + "... [truncated]"


def evidence_snapshot(
    passage: Passage,
    corpus: Corpus,
    *,
    rubric_id: str,
    more_context: bool,
    width: int = 80,
) -> str:
    """A deterministic snapshot of precisely the evidence frame visible to the operator."""
    before, after = _context(passage, corpus, more_context)
    frame_width = max(1, width - 1)
    return json.dumps(
        {
            "rubric_id": rubric_id,
            "article": {"id": passage.article_id, "title": passage.article_title},
            "target": {
                "id": passage.passage_id,
                "heading_path": passage.heading_path,
                "paragraph_ordinal": passage.paragraph_ordinal,
                "text": passage.text,
            },
            "context_mode": "expanded" if more_context else "compact",
            "preceding": [
                {"id": item.passage_id, "text": _snippet(item.text, more_context, frame_width)}
                for item in before
            ],
            "following": [
                {"id": item.passage_id, "text": _snippet(item.text, more_context, frame_width)}
                for item in after
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _wrap(text: str, width: int) -> list[str]:
    """Wrap even long unspaced identifiers so the terminal never wraps for us."""
    return textwrap.wrap(
        text,
        width=max(1, width),
        break_long_words=True,
        break_on_hyphens=False,
        replace_whitespace=True,
    ) or [""]


def _field(label: str, value: str, width: int) -> list[str]:
    prefix = f"{label} · "
    if len(prefix) >= width:
        return _wrap(prefix + value, width)
    wrapped = _wrap(value, width - len(prefix))
    return [prefix + wrapped[0], *(" " * len(prefix) + line for line in wrapped[1:])]


def _styled(text: str, code: str, enabled: bool) -> str:
    return f"\x1b[{code}m{text}\x1b[0m" if enabled else text


def render(
    passage: Passage,
    corpus: Corpus,
    *,
    rubric_id: str,
    more_context: bool,
    status: str,
    width: int = 80,
    style: bool = False,
) -> str:
    """Render a complete frame within ``width - 1`` columns.

    Reserving a column avoids terminal auto-wrap, which is especially important
    while raw mode has disabled the terminal's normal output processing.
    """
    frame_width = max(1, width - 1)
    before, after = _context(passage, corpus, more_context)
    index = corpus.passages.index(passage)
    article = [item for item in corpus.passages if item.article_id == passage.article_id]
    article_index = article.index(passage)
    article_ids = list(dict.fromkeys(item.article_id for item in corpus.passages))
    article_number = article_ids.index(passage.article_id) + 1
    heading = " › ".join(passage.heading_path) or "Lead"
    progress = (
        f"Article {article_number}/{len(article_ids)} · Passage {article_index + 1}/{len(article)}"
        f" · Overall {index + 1}/{len(corpus.passages)}"
    )
    status_code = (
        "1;31"
        if status.startswith("SAVE FAILED")
        else "1;32"
        if status.startswith("SAVED")
        else "1;36"
    )
    lines = [_styled(line, "1", style) for line in _wrap("CORPUS CURATION", frame_width)]
    lines += _field("Progress", progress, frame_width)
    lines += _field("Rubric", rubric_id, frame_width)
    lines += _field("Source", f"{passage.article_title} › {heading}", frame_width)
    status_lines = _field("STATUS", status, frame_width)
    lines += [_styled(line, status_code, style) for line in status_lines]
    lines += _field("Question", question_for(passage), frame_width)
    lines.append("─" * frame_width)
    lines += [_styled("TARGET PASSAGE", "1;33", style)]
    lines += ["│ " + line for line in _wrap(passage.text, frame_width - 2)]
    lines.append("─" * frame_width)

    for item in before:
        snippet = _snippet(item.text, more_context, frame_width)
        lines += [_styled(line, "2", style) for line in _field("Before", snippet, frame_width)]
    for item in after:
        snippet = _snippet(item.text, more_context, frame_width)
        lines += [_styled(line, "2", style) for line in _field("After", snippet, frame_width)]
    lines += _wrap("[L] Lore  [W] Writing  [A] Analysis  [D] Adaptation", frame_width)
    lines += _wrap(
        "[R] Reference  [S] Defer  [U] Undo  [Space] Context  [?] Help  [Q] Quit", frame_width
    )
    return "\n".join(lines)


def _write_terminal(output: TextIO, text: str) -> None:
    """Write CRLF frames because raw mode disables ONLCR conversion."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
    output.write(normalized)


def _terminal_width(output: TextIO) -> int:
    try:
        columns = os.get_terminal_size(output.fileno()).columns
    except (AttributeError, OSError):
        columns = shutil.get_terminal_size(fallback=(80, 24)).columns
    return max(40, columns)


def _color_enabled() -> bool:
    return not bool(os.environ.get("NO_COLOR"))


class KeyGuard:
    """Drops OS key-repeat for a just-handled decision without slowing distinct keys."""

    def __init__(self, interval: float = 1.25) -> None:
        self.interval = interval
        self.key: str | None = None
        self.at = 0.0

    def accept(self, key: str, at: float | None = None) -> bool:
        now = time.monotonic() if at is None else at
        repeated = key in ACTION_KEYS and key == self.key and now - self.at < self.interval
        self.key, self.at = key, now
        return not repeated


def _flush_input(stream: TextIO) -> None:
    try:
        termios.tcflush(stream.fileno(), termios.TCIFLUSH)
    except termios.error:
        pass


def summary(counts: dict[str, int]) -> str:
    return "\n".join(
        ["CURATION SUMMARY (deferred and undecided are excluded)"]
        + [f"{key}: {value}" for key, value in counts.items()]
    )


def run_terminal(
    state: CurationState,
    *,
    review_deferred: bool = False,
    input_stream: TextIO = sys.stdin,
    output: TextIO = sys.stdout,
) -> None:
    """Run the raw-terminal cockpit, restoring the terminal for every exit path."""
    if not input_stream.isatty() or not output.isatty():
        raise ValueError("corpus curation requires an interactive TTY")
    original = termios.tcgetattr(input_stream.fileno())
    context = False
    visited: set[str] = set()
    status = "Ready — choose L/W/A/D/R, or S to defer."
    guard = KeyGuard()
    raw_enabled = False
    try:
        tty.setraw(input_stream.fileno())
        raw_enabled = True
        _write_terminal(output, "\x1b[?25l")
        passage_id = state.current_or_resume(review_deferred=review_deferred)
        while passage_id:
            visited.add(passage_id)
            passage = next(item for item in state.corpus.passages if item.passage_id == passage_id)
            width = _terminal_width(output)
            _write_terminal(
                output,
                "\x1b[2J\x1b[H"
                + render(
                    passage,
                    state.corpus,
                    rubric_id=state.rubric_id,
                    more_context=context,
                    status=status,
                    width=width,
                    style=_color_enabled(),
                ),
            )
            output.flush()
            raw_key = input_stream.read(1)
            if not raw_key:
                return
            key = raw_key.casefold()
            if not guard.accept(key):
                continue
            if key in ACTION_KEYS:
                try:
                    passage_id = state.record(
                        passage_id,
                        key,
                        question_for(passage),
                        evidence_snapshot(
                            passage,
                            state.corpus,
                            rubric_id=state.rubric_id,
                            more_context=context,
                            width=width,
                        ),
                        review_deferred=review_deferred,
                        exclude_ids=frozenset(visited),
                    )
                except sqlite3.Error as error:
                    status = f"SAVE FAILED — still on this passage: {error}"
                else:
                    status = f"SAVED: {CLASSIFICATIONS.get(key, 'deferred')}"
                    _flush_input(input_stream)
            elif key == "u":
                undone_id = state.undo(
                    question_for(passage),
                    evidence_snapshot(
                        passage,
                        state.corpus,
                        rubric_id=state.rubric_id,
                        more_context=context,
                        width=width,
                    ),
                    review_deferred=review_deferred,
                )
                if undone_id is None:
                    status = "Nothing to undo."
                else:
                    passage_id = undone_id
                    status = "UNDO SAVED — returned to the previous decision."
            elif key == " ":
                context = not context
                status = "More context shown." if context else "Compact context shown."
            elif key == "?":
                status = "L=in-world claims; W=creation history; A=analysis/reception; D=adaptation; R=reference/admin; S=defer."
            elif key in ("q", "\x03", "\x04"):
                return
        _write_terminal(output, "\x1b[2J\x1b[H" + summary(state.counts()) + "\n")
        output.flush()
    finally:
        try:
            if raw_enabled:
                termios.tcsetattr(input_stream.fileno(), termios.TCSADRAIN, original)
        finally:
            _write_terminal(output, "\x1b[?25h")
            output.flush()
