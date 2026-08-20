"""Pure, local HTML projections of complete grounding-experiment batches."""

from __future__ import annotations

import html
import json
import os
import tempfile
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .lore_experiment import RunEnvelope, StoredAttempt, validate_complete_batch
from .retrieval_index import EvidencePassage


_CONDITIONS = ("retrieval-disabled", "retrieval-enabled")
_TRUNCATION_MARKER = "… [excerpt truncated]"
_RESULT_TYPES = (
    ("grounded", "Grounded"),
    ("ungrounded_answer", "Ungrounded answer"),
    ("insufficient_evidence", "Insufficient evidence"),
    ("missing_submission", "No submission"),
    ("failed", "Failed"),
)


@dataclass(frozen=True)
class ReportPaths:
    retrieval_enabled: Path
    retrieval_disabled: Path


def _text(value: object) -> str:
    return html.escape(str(value), quote=True)


def _paragraphs(value: str) -> str:
    return _text(value).replace("\n", "<br>\n")


def _excerpt(body: str, limit: int) -> str:
    return body if len(body) <= limit else body[:limit] + _TRUNCATION_MARKER


def _excerpt_limit(envelope: RunEnvelope) -> int:
    report = envelope.config.get("report")
    if not isinstance(report, Mapping):
        raise ValueError("run configuration has no report settings")
    limit = report.get("evidence_excerpt_characters")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 200 <= limit <= 4000:
        raise ValueError("run configuration has an invalid evidence excerpt limit")
    return limit


def _condition_label(condition: str) -> str:
    if condition not in _CONDITIONS:
        raise ValueError("report condition is invalid")
    return condition.replace("retrieval-", "Retrieval ").replace("-", " ").title()


def _status(record: StoredAttempt) -> str:
    if record.record.error is not None:
        if record.record.error.code == "missing_submission":
            return "missing_submission"
        return "failed"
    return record.record.classification


def _result_totals(attempts: Sequence[StoredAttempt], label: str) -> str:
    counts = Counter(_status(attempt) for attempt in attempts)
    items = "".join(
        '<div class="result-total">'
        f'<dt><span class="result-swatch {_text(status)}" aria-hidden="true"></span>'
        f"{_text(display)}</dt><dd>{counts[status]}</dd></div>"
        for status, display in _RESULT_TYPES
    )
    return f'<dl class="result-totals" aria-label="{_text(label)}">{items}</dl>'


def _ordered_evidence(attempt: StoredAttempt) -> tuple[EvidencePassage, ...]:
    """Keep cited evidence in tool-call order when that trace records it."""
    by_id = {passage.passage_id: passage for passage in attempt.record.evidence}
    ordered_ids: list[str] = []
    for call in attempt.record.tool_trace:
        for passage_id in call.evidence_passage_ids:
            if passage_id in by_id and passage_id not in ordered_ids:
                ordered_ids.append(passage_id)
    ordered_ids.extend(passage_id for passage_id in by_id if passage_id not in ordered_ids)
    return tuple(by_id[passage_id] for passage_id in ordered_ids)


def _evidence(attempt: StoredAttempt, excerpt_limit: int) -> str:
    blocks = []
    for passage in _ordered_evidence(attempt):
        heading = " › ".join(passage.heading_path)
        blocks.append(
            '<details class="evidence"><summary>Evidence · passage</summary>'
            "<dl>"
            f"<dt>Title</dt><dd>{_text(passage.title)}</dd>"
            f"<dt>Complete section path</dt><dd>{_text(heading)}</dd>"
            f'<dt>Passage ID</dt><dd class="passage">{_text(passage.passage_id)}</dd>'
            f'<dt>Excerpt</dt><dd class="excerpt">{_text(_excerpt(passage.body, excerpt_limit))}</dd>'
            "</dl></details>"
        )
    return "".join(blocks)


def _diagnostics(attempt: StoredAttempt) -> str:
    error = attempt.record.error
    if error is None:
        return ""
    return (
        '<details class="diagnostics"><summary>Sanitized failure details</summary><dl>'
        f"<dt>Code</dt><dd>{_text(error.code)}</dd>"
        f"<dt>Stage</dt><dd>{_text(error.stage)}</dd>"
        f"<dt>Message</dt><dd>{_text(error.message)}</dd>"
        "</dl></details>"
    )


def _cell(attempt: StoredAttempt, condition: str, excerpt_limit: int) -> str:
    status = _status(attempt)
    label = dict(_RESULT_TYPES)[status]
    parts = [f'<span class="badge {_text(status)}">{_text(label)}</span>']
    if attempt.record.error is None and attempt.record.answer:
        parts.append(f'<p class="answer">{_paragraphs(attempt.record.answer)}</p>')
    if condition == "retrieval-disabled":
        parts.append('<p class="cell-note">No retrieval available.</p>')
    elif attempt.record.error is None and attempt.record.evidence:
        parts.append(_evidence(attempt, excerpt_limit))
    parts.append(_diagnostics(attempt))
    return "".join(parts)


def _style() -> str:
    return """<style>
:root { color-scheme: light; --paper:#f4edda; --ink:#28271f; --muted:#665f4d; --forest:#23483a; --line:#c6b892; }
* { box-sizing:border-box; } body { margin:0; padding:1.5rem; color:var(--ink); background:var(--paper); font:15px/1.5 Georgia,serif; }
main { max-width:1540px; margin:auto; } header, section, details.config { margin:1rem 0; padding:1rem; background:#fffaf0; border:1px solid var(--line); }
h1,h2 { color:var(--forest); } .condition { color:var(--forest); } .companion { color:#fff; background:var(--forest); padding:.6rem .8rem; text-decoration:none; }
.meta { display:flex; flex-wrap:wrap; gap:1rem; font: .82rem/1.35 ui-monospace,monospace; } .notice { border-left:5px solid #a8792b; padding:.8rem; background:#fff9e9; }
.models, .inventory { padding-left:1.2rem; } .models { font-family:ui-monospace,monospace; overflow-wrap:anywhere; } .case-notes { margin-top:.7rem; }
.table-wrap { overflow:auto; max-height:78vh; border:1px solid var(--line); } table { min-width:2150px; width:100%; border-collapse:separate; border-spacing:0; table-layout:fixed; }
th,td { padding:.8rem; vertical-align:top; border-right:1px solid var(--line); border-bottom:1px solid var(--line); background:#fffaf0; } thead th { position:sticky; top:0; z-index:2; color:#fff; background:var(--forest); font-family:ui-monospace,monospace; } tbody th { position:sticky; left:0; z-index:1; width:330px; background:#efe4c8; text-align:left; } td { width:302px; }
.case-id { display:block; color:var(--forest); font:700 .75rem/1.2 ui-monospace,monospace; } .badge { display:inline-block; padding:.25rem .45rem; border-radius:999px; font:700 .68rem/1 system-ui,sans-serif; text-transform:uppercase; } .badge.grounded,.result-swatch.grounded { background:#cfe3d2; } .badge.ungrounded_answer,.result-swatch.ungrounded_answer { background:#f3e6bd; } .badge.insufficient_evidence,.result-swatch.insufficient_evidence { background:#e5dfeb; } .badge.missing_submission,.result-swatch.missing_submission { background:#ead8c5; } .badge.failed,.result-swatch.failed { background:#f1ded8; }
.totals-heading,.totals-cell { width:250px; } .totals-cell,tfoot th,tfoot td { background:#f7efd9; } tfoot th { position:sticky; left:0; z-index:1; text-align:left; color:var(--forest); } .result-totals { display:grid; grid-template-columns:1fr auto; gap:.25rem .65rem; margin:0; font: .72rem/1.3 system-ui,sans-serif; } .result-total { display:contents; } .result-total dt { display:flex; align-items:center; gap:.35rem; color:var(--ink); font:inherit; text-transform:none; } .result-total dd { margin:0; font-weight:800; text-align:right; } .result-swatch { width:.7rem; height:.7rem; border:1px solid rgb(40 39 31 / 25%); border-radius:50%; flex:none; } .matrix-note { color:var(--muted); }
.evidence,.diagnostics { margin-top:.65rem; border-top:1px dashed var(--line); } summary { cursor:pointer; } dl { margin:.5rem 0; } dt { color:var(--muted); font:700 .68rem/1.2 system-ui,sans-serif; text-transform:uppercase; } dd { margin:.15rem 0 .5rem; overflow-wrap:anywhere; } .passage { font-family:ui-monospace,monospace; } .excerpt { font-style:italic; } .cell-note { color:var(--muted); }
@media (max-width:900px) { body { padding:.5rem; } } @media print { .table-wrap { max-height:none; overflow:visible; } thead th,tbody th { position:static; } table { min-width:0; font-size:8pt; } }
</style>"""


def render_report(envelope: RunEnvelope, attempts: Sequence[StoredAttempt], condition: str) -> str:
    """Render one condition from a complete, previously retained batch."""
    _condition_label(condition)
    validate_complete_batch(envelope, attempts)
    excerpt_limit = _excerpt_limit(envelope)
    attempts_by_coordinate = {
        (attempt.case_id, attempt.record.model, attempt.condition): attempt for attempt in attempts
    }
    companion = (
        "retrieval-disabled.html" if condition == "retrieval-enabled" else "retrieval-enabled.html"
    )
    rows = []
    for case in envelope.cases:
        row_attempts = [
            attempts_by_coordinate[(case.case_id, model, condition)] for model in envelope.models
        ]
        cells = "".join(
            "<td>" + _cell(attempt, condition, excerpt_limit) + "</td>" for attempt in row_attempts
        )
        totals = _result_totals(row_attempts, f"Result totals for question {case.case_id}")
        rows.append(
            '<tr><th scope="row"><span class="case-id">'
            f"{_text(case.difficulty)} · {_text(case.case_id)}</span>{_text(case.question)}</th>"
            f'{cells}<td class="totals-cell">{totals}</td></tr>'
        )
    inventory = "".join(
        "<li><strong>"
        f"{_text(case.difficulty)} · {_text(case.case_id)}</strong> — {_text(case.question)}"
        '<details class="case-notes"><summary>Human review notes</summary>'
        f"<p>{_text(case.review_focus)}</p><p>Expected evidence: {_text(', '.join(case.expected_evidence_passage_ids))}</p>"
        "</details></li>"
        for case in envelope.cases
    )
    headers = "".join(f'<th scope="col">{_text(model)}</th>' for model in envelope.models)
    column_totals = "".join(
        "<td>"
        + _result_totals(
            [attempts_by_coordinate[(case.case_id, model, condition)] for case in envelope.cases],
            f"Result totals for model {model}",
        )
        + "</td>"
        for model in envelope.models
    )
    condition_attempts = [
        attempts_by_coordinate[(case.case_id, model, condition)]
        for case in envelope.cases
        for model in envelope.models
    ]
    all_totals = _result_totals(condition_attempts, f"Result totals for {condition}")
    config = _text(json.dumps(envelope.config, ensure_ascii=False, sort_keys=True, indent=2))
    label = _condition_label(condition)
    return "\n".join(
        (
            "<!doctype html>",
            '<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{_text(label)} model comparison</title>{_style()}</head><body><main>",
            "<header><p>Phase 0 · human grounding review</p>"
            f'<h1><span class="condition">{_text(label)}</span><br>model comparison</h1>'
            "<p>Answers are shown for human review; this report computes no score, rank, winner, or recommendation.</p>"
            f'<a class="companion" href="{companion}">View companion condition report</a></header>',
            '<section class="meta">'
            f"<span>Condition: {_text(condition)}</span><span>Batch: {_text(envelope.run_id)}</span>"
            f"<span>Release: {_text(envelope.release_id)}</span><span>Config: {_text(envelope.config_identity)}</span></section>",
            '<aside class="notice"><strong>Review, do not rank.</strong> Statuses describe attempt shape, not factual quality.</aside>',
            '<section><h2>Declared model order</h2><ol class="models">'
            + "".join(f"<li>{_text(model)}</li>" for model in envelope.models)
            + "</ol></section>",
            f'<details class="config"><summary>Run configuration · non-secret</summary><pre>{config}</pre></details>',
            f'<section><h2>Question inventory</h2><ol class="inventory">{inventory}</ol></section>',
            "<section><h2>Comparison matrix</h2>"
            '<p class="matrix-note">Counts are terminal result totals, not scores. No submission is the '
            "<code>missing_submission</code> failure subtype; Failed contains all other failures.</p>"
            '<div class="table-wrap"><table><caption>'
            f"{_text(label)} responses and result totals by question and model</caption>"
            f'<thead><tr><th scope="col">Question</th>{headers}<th scope="col" class="totals-heading">Result totals by question</th></tr></thead><tbody>'
            + "".join(rows)
            + '</tbody><tfoot><tr><th scope="row">Result totals by model</th>'
            + column_totals
            + f'<td class="totals-cell">{all_totals}</td></tr></tfoot></table></div></section>',
            "</main></body></html>",
        )
    )


def write_reports(
    envelope: RunEnvelope, attempts: Sequence[StoredAttempt], output_dir: Path
) -> ReportPaths:
    """Validate, stage, then publish both condition reports without touching run data."""
    enabled = output_dir / "retrieval-enabled.html"
    disabled = output_dir / "retrieval-disabled.html"
    if enabled.exists() or disabled.exists():
        raise FileExistsError("refusing to overwrite experiment reports")
    enabled_html = render_report(envelope, attempts, "retrieval-enabled")
    disabled_html = render_report(envelope, attempts, "retrieval-disabled")
    with tempfile.TemporaryDirectory(prefix=".reports-", dir=output_dir) as directory:
        staged = Path(directory)
        staged_enabled = staged / enabled.name
        staged_disabled = staged / disabled.name
        staged_enabled.write_text(enabled_html, encoding="utf-8")
        staged_disabled.write_text(disabled_html, encoding="utf-8")
        published: list[Path] = []
        try:
            os.replace(staged_enabled, enabled)
            published.append(enabled)
            os.replace(staged_disabled, disabled)
            published.append(disabled)
        except OSError:
            for path in published:
                path.unlink(missing_ok=True)
            raise
    return ReportPaths(retrieval_enabled=enabled, retrieval_disabled=disabled)
