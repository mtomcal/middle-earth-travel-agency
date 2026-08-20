"""Tests for pure, condition-specific grounding experiment reports."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from middle_earth_travel_agency.lore_agent import AttemptError, AttemptRecord, ToolTraceRecord
from middle_earth_travel_agency.lore_experiment import (
    CASES,
    RunEnvelope,
    StoredAttempt,
    _attempt_id,
)
from middle_earth_travel_agency.experiment_report import render_report, write_reports
from middle_earth_travel_agency.retrieval_index import EvidencePassage


MODELS = ("model-one", "model-two", "model-three", "model-four", "model-five")
PASSAGE = EvidencePassage(
    "passage-visible",
    "article-1",
    "<Title>",
    ("Lead", "<Heading>"),
    1,
    "é" * 201 + "<body>",
)


def _envelope() -> RunEnvelope:
    return RunEnvelope(
        run_id="run-<one>",
        created_at="2026-08-19T00:00:00Z",
        source_revision="revision",
        release_id="corpus-<v1>",
        manifest_sha256="manifest",
        index_build_identity="index",
        config_identity="config",
        config={"report": {"evidence_excerpt_characters": 200}, "label": "<config>"},
        models=MODELS,
        cases=CASES,
        conditions=("retrieval-disabled", "retrieval-enabled"),
        expected_attempts=100,
        prompt_identity="prompt",
    )


def _record(case_id: str, model: str, condition: str) -> AttemptRecord:
    case = next(case for case in CASES if case.case_id == case_id)
    enabled = condition == "retrieval-enabled"
    if case_id == "easy-01" and model == "model-one" and enabled:
        return AttemptRecord(
            question=case.question,
            model=model,
            retrieval_enabled=True,
            classification="grounded",
            outcome="answered",
            answer="First <answer>\nSecond & answer",
            evidence_passage_ids=(PASSAGE.passage_id,),
            evidence=(PASSAGE,),
            tool_trace=(
                ToolTraceRecord("call", "search_lore", True, True, 4, 3, (PASSAGE.passage_id,)),
            ),
            error=None,
            provider_request_count=1,
            retry_count=0,
            duration_seconds=0.01,
        )
    if case_id == "easy-02" and model == "model-two" and enabled:
        return AttemptRecord(
            question=case.question,
            model=model,
            retrieval_enabled=True,
            classification="failed",
            outcome=None,
            answer=None,
            evidence_passage_ids=(),
            evidence=(),
            tool_trace=(),
            error=AttemptError("bad-<code>", "provider", "<message>"),
            provider_request_count=1,
            retry_count=0,
            duration_seconds=0.01,
        )
    if case_id == "easy-03" and model == "model-three" and enabled:
        return AttemptRecord(
            question=case.question,
            model=model,
            retrieval_enabled=True,
            classification="failed",
            outcome=None,
            answer=None,
            evidence_passage_ids=(),
            evidence=(),
            tool_trace=(),
            error=AttemptError("missing_submission", "submission", "No terminal submission"),
            provider_request_count=1,
            retry_count=0,
            duration_seconds=0.01,
        )
    return AttemptRecord(
        question=case.question,
        model=model,
        retrieval_enabled=enabled,
        classification="ungrounded_answer" if not enabled else "insufficient_evidence",
        outcome="answered" if not enabled else "insufficient_evidence",
        answer="<control answer>" if not enabled else "Evidence was insufficient.",
        evidence_passage_ids=(),
        evidence=(),
        tool_trace=(),
        error=None,
        provider_request_count=1,
        retry_count=0,
        duration_seconds=0.01,
    )


def _attempts() -> tuple[StoredAttempt, ...]:
    return tuple(
        StoredAttempt(
            attempt_id=_attempt_id("run-<one>", case.case_id, model, condition),
            case_id=case.case_id,
            difficulty=case.difficulty,
            condition=condition,
            config_identity="config",
            record=_record(case.case_id, model, condition),
        )
        for condition in ("retrieval-disabled", "retrieval-enabled")
        for case in CASES
        for model in MODELS
    )


def _totals(report: str, label: str) -> dict[str, int]:
    start = report.index(f'<dl class="result-totals" aria-label="{label}">')
    end = report.index("</dl>", start)
    fragment = report[start:end]
    return {
        name: int(count)
        for name, count in re.findall(r"</span>([^<]+)</dt><dd>(\d+)</dd>", fragment)
    }


def test_rendering_is_deterministic_escaped_and_condition_specific() -> None:
    envelope = _envelope()
    attempts = _attempts()
    enabled = render_report(envelope, attempts, "retrieval-enabled")
    disabled = render_report(envelope, attempts, "retrieval-disabled")

    assert enabled == render_report(envelope, attempts, "retrieval-enabled")
    assert "Retrieval Enabled" in enabled
    assert "retrieval-disabled.html" in enabled
    assert "retrieval-enabled.html" in disabled
    assert "First &lt;answer&gt;<br>\nSecond &amp; answer" in enabled
    assert "&lt;Title&gt;" in enabled
    assert "&lt;Heading&gt;" in enabled
    assert "&lt;body&gt;" not in enabled
    assert "… [excerpt truncated]" in enabled
    assert "Sanitized failure details" in enabled
    assert "&lt;message&gt;" in enabled
    assert '<span class="badge missing_submission">No submission</span>' in enabled
    assert "<script" not in enabled.lower()
    assert "<script" not in disabled.lower()
    assert "No retrieval available." in disabled
    assert "Evidence · passage" not in disabled
    assert [enabled.index(model) for model in MODELS] == sorted(
        enabled.index(model) for model in MODELS
    )
    assert [disabled.index(model) for model in MODELS] == sorted(
        disabled.index(model) for model in MODELS
    )
    assert "score, rank, winner, or recommendation" in enabled


def test_rendering_totals_each_result_type_by_question_and_model() -> None:
    enabled = render_report(_envelope(), _attempts(), "retrieval-enabled")

    assert "Counts are terminal result totals, not scores." in enabled
    assert _totals(enabled, "Result totals for question easy-01") == {
        "Grounded": 1,
        "Ungrounded answer": 0,
        "Insufficient evidence": 4,
        "No submission": 0,
        "Failed": 0,
    }
    assert _totals(enabled, "Result totals for question easy-03") == {
        "Grounded": 0,
        "Ungrounded answer": 0,
        "Insufficient evidence": 4,
        "No submission": 1,
        "Failed": 0,
    }
    assert _totals(enabled, "Result totals for model model-one") == {
        "Grounded": 1,
        "Ungrounded answer": 0,
        "Insufficient evidence": 9,
        "No submission": 0,
        "Failed": 0,
    }
    assert _totals(enabled, "Result totals for model model-three") == {
        "Grounded": 0,
        "Ungrounded answer": 0,
        "Insufficient evidence": 9,
        "No submission": 1,
        "Failed": 0,
    }
    assert _totals(enabled, "Result totals for retrieval-enabled") == {
        "Grounded": 1,
        "Ungrounded answer": 0,
        "Insufficient evidence": 47,
        "No submission": 1,
        "Failed": 1,
    }
    assert "Result totals by question" in enabled
    assert "Result totals by model" in enabled


def test_rendering_requires_one_complete_terminal_record_per_coordinate() -> None:
    with pytest.raises(ValueError, match="incomplete"):
        render_report(_envelope(), _attempts()[:-1], "retrieval-enabled")
    with pytest.raises(ValueError, match="condition"):
        render_report(_envelope(), _attempts(), "other")


def test_reports_publish_only_after_complete_validation_and_preserve_run_artifacts(
    tmp_path: Path,
) -> None:
    (tmp_path / "run.json").write_text("retained run")
    (tmp_path / "attempts.jsonl").write_text("retained attempts\n")

    paths = write_reports(_envelope(), _attempts(), tmp_path)

    assert paths.retrieval_enabled.read_text() == render_report(
        _envelope(), _attempts(), "retrieval-enabled"
    )
    assert paths.retrieval_disabled.is_file()
    assert (tmp_path / "run.json").read_text() == "retained run"
    assert (tmp_path / "attempts.jsonl").read_text() == "retained attempts\n"
    with pytest.raises(FileExistsError, match="overwrite"):
        write_reports(_envelope(), _attempts(), tmp_path)


def test_failed_second_publication_rolls_back_the_first_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = tmp_path / "run.json"
    attempts = tmp_path / "attempts.jsonl"
    run.write_text("retained run")
    attempts.write_text("retained attempts\n")

    from middle_earth_travel_agency import experiment_report

    replace = experiment_report.os.replace

    def fail_disabled(source: Path, destination: Path) -> None:
        if destination.name == "retrieval-disabled.html":
            raise OSError("simulated publication failure")
        replace(source, destination)

    monkeypatch.setattr(experiment_report.os, "replace", fail_disabled)

    with pytest.raises(OSError, match="simulated"):
        write_reports(_envelope(), _attempts(), tmp_path)

    assert not (tmp_path / "retrieval-enabled.html").exists()
    assert not (tmp_path / "retrieval-disabled.html").exists()
    assert run.read_text() == "retained run"
    assert attempts.read_text() == "retained attempts\n"
