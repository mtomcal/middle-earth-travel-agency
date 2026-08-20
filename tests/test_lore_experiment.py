"""Focused tests for the disposable, human-reviewed experiment runner."""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from middle_earth_travel_agency.experiment_config import (
    AgentConfig,
    ExperimentConfig,
    IndexConfig,
    ProviderConfig,
    ReportConfig,
    RetrievalConfig,
    RunnerConfig,
)
from middle_earth_travel_agency.lore_agent import SYSTEM_PROMPT, AttemptError, AttemptRecord
from middle_earth_travel_agency.lore_experiment import (
    CASES,
    BatchFailure,
    ExperimentRunner,
    ReviewDecision,
    StoredAttempt,
    _attempt_id,
    load_run_artifacts,
    _prompt_identity,
    validate_complete_batch,
    validate_review,
)


class _Index:
    metadata = SimpleNamespace(
        release_id="corpus-v1-rc1",
        manifest_sha256="manifest-digest",
        build_identity="index-build",
    )

    def context(self, passage_id: str) -> object:
        if not passage_id.startswith("passage_"):
            raise ValueError("unknown lore passage id")
        return object()


class _Adapter:
    def __init__(self, model: str) -> None:
        self.model = model


@pytest.fixture
def config() -> ExperimentConfig:
    return ExperimentConfig(
        index=IndexConfig("unicode61", 2),
        retrieval=RetrievalConfig("all-terms", 5, 5.0, 2.0, 1.0, "passage-id"),
        agent=AgentConfig(4, 0.0, 1024),
        provider=ProviderConfig(60.0, 300.0, 1),
        runner=RunnerConfig(5),
        report=ReportConfig(1200),
    )


def _record(
    *, question: str, model: str, enabled: bool, error: AttemptError | None = None
) -> AttemptRecord:
    return AttemptRecord(
        question=question,
        model=model,
        retrieval_enabled=enabled,
        classification="failed" if error else "insufficient_evidence",
        outcome=None if error else "insufficient_evidence",
        answer=None if error else "Insufficient evidence.",
        evidence_passage_ids=(),
        evidence=(),
        tool_trace=(),
        error=error,
        provider_request_count=1,
        retry_count=0,
        duration_seconds=0.01,
    )


def _runner(tmp_path: Path, config: ExperimentConfig) -> ExperimentRunner:
    return ExperimentRunner(
        index=_Index(),  # type: ignore[arg-type]
        config=config,
        models=("model-1", "model-2", "model-3", "model-4", "model-5"),
        adapter_factory=_Adapter,  # type: ignore[arg-type]
        output_dir=tmp_path / "run",
        source_revision="deadbeef",
        run_id_factory=lambda: "run-1",
    )


def test_catalog_is_exact_and_human_only_fields_do_not_enter_attempts() -> None:
    assert [case.case_id for case in CASES] == [
        "easy-01",
        "easy-02",
        "easy-03",
        "easy-04",
        "easy-05",
        "hard-01",
        "hard-02",
        "hard-03",
        "hard-04",
        "hard-05",
    ]
    assert [case.difficulty for case in CASES].count("easy") == 5
    assert [case.difficulty for case in CASES].count("hard") == 5
    assert CASES[0].question == "Who rules Lothlórien, and from what city do they rule?"
    assert CASES[-1].question.startswith("Explain how the apparent Corsair fleet")
    assert all(case.review_focus and case.expected_evidence_passage_ids for case in CASES)


def test_prompt_identity_matches_the_exact_agent_system_prompt() -> None:
    assert _prompt_identity() == hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()


def test_runner_persists_100_terminal_cells_in_disabled_then_enabled_waves(
    tmp_path: Path, config: ExperimentConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, bool, str]] = []

    async def fake_answer_case(**kwargs: object) -> AttemptRecord:
        adapter = kwargs["adapter"]
        assert isinstance(adapter, _Adapter)
        question = kwargs["question"]
        enabled = kwargs["retrieval_enabled"]
        assert isinstance(question, str) and isinstance(enabled, bool)
        calls.append((question, enabled, adapter.model))
        return _record(question=question, model=adapter.model, enabled=enabled)

    monkeypatch.setattr("middle_earth_travel_agency.lore_experiment.answer_case", fake_answer_case)
    result = asyncio.run(_runner(tmp_path, config).run())

    assert len(result.attempts) == 100
    assert len(calls) == 100
    assert [enabled for _, enabled, _ in calls[:5]] == [False] * 5
    assert [enabled for _, enabled, _ in calls[5:10]] == [True] * 5
    assert (tmp_path / "run" / "run.json").is_file()
    assert (tmp_path / "run" / "review.json").is_file()
    lines = (tmp_path / "run" / "attempts.jsonl").read_text().splitlines()
    assert len(lines) == 100
    assert len({json.loads(line)["attempt_id"] for line in lines}) == 100
    envelope = json.loads((tmp_path / "run" / "run.json").read_text())
    assert envelope["expected_attempts"] == 100
    assert envelope["models"] == ["model-1", "model-2", "model-3", "model-4", "model-5"]
    assert envelope["conditions"] == ["retrieval-disabled", "retrieval-enabled"]
    assert "review_focus" in envelope["cases"][0]
    assert "review_focus" not in json.loads(lines[0])


def test_runner_stops_after_durable_authorization_failure(
    tmp_path: Path, config: ExperimentConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_answer_case(**kwargs: object) -> AttemptRecord:
        adapter = kwargs["adapter"]
        question = kwargs["question"]
        enabled = kwargs["retrieval_enabled"]
        assert (
            isinstance(adapter, _Adapter)
            and isinstance(question, str)
            and isinstance(enabled, bool)
        )
        error = AttemptError("provider_authorization_failed", "provider", "authorization failed")
        return _record(question=question, model=adapter.model, enabled=enabled, error=error)

    monkeypatch.setattr("middle_earth_travel_agency.lore_experiment.answer_case", fake_answer_case)
    with pytest.raises(BatchFailure, match="authorization"):
        asyncio.run(_runner(tmp_path, config).run())
    assert len((tmp_path / "run" / "attempts.jsonl").read_text().splitlines()) == 5
    assert (tmp_path / "run" / "review.json").is_file()


def test_runner_rejects_existing_output_and_invalid_models(
    tmp_path: Path, config: ExperimentConfig
) -> None:
    destination = tmp_path / "run"
    destination.mkdir()
    runner = _runner(tmp_path, config)
    with pytest.raises(FileExistsError):
        asyncio.run(runner.run())
    with pytest.raises(ValueError, match="exactly five"):
        ExperimentRunner(
            index=_Index(),  # type: ignore[arg-type]
            config=config,
            models=("one",),
            adapter_factory=_Adapter,  # type: ignore[arg-type]
            output_dir=tmp_path / "other",
            source_revision="deadbeef",
        )


def test_complete_batch_and_review_gate_validation(
    tmp_path: Path, config: ExperimentConfig
) -> None:
    runner = _runner(tmp_path, config)
    envelope = runner._envelope()
    attempts = tuple(
        StoredAttempt(
            attempt_id=_attempt_id(envelope.run_id, case.case_id, model, condition),
            case_id=case.case_id,
            difficulty=case.difficulty,
            condition=condition,
            config_identity=envelope.config_identity,
            record=_record(
                question=case.question,
                model=model,
                enabled=condition == "retrieval-enabled",
            ),
        )
        for case in CASES
        for condition in ("retrieval-disabled", "retrieval-enabled")
        for model in envelope.models
    )
    validate_complete_batch(envelope, attempts)
    with pytest.raises(ValueError, match="incomplete"):
        validate_complete_batch(envelope, attempts[:-1])

    selected = validate_review(
        {
            "schema_version": 1,
            "run_id": "run-1",
            "decision": "selected",
            "selected_model": "model-1",
            "rationale": "The evidence use was faithful.",
        },
        envelope,
    )
    assert selected == ReviewDecision(
        "run-1", "selected", "model-1", "The evidence use was faithful."
    )
    none = validate_review(
        {
            "schema_version": 1,
            "run_id": "run-1",
            "decision": "none",
            "selected_model": None,
            "rationale": "No candidate qualified.",
        },
        envelope,
    )
    assert none.decision == "none"
    for invalid in (
        {
            "schema_version": 1,
            "run_id": "run-1",
            "decision": None,
            "selected_model": None,
            "rationale": "",
        },
        {
            "schema_version": 1,
            "run_id": "other",
            "decision": "none",
            "selected_model": None,
            "rationale": "reason",
        },
        {
            "schema_version": 1,
            "run_id": "run-1",
            "decision": "selected",
            "selected_model": "other",
            "rationale": "reason",
        },
    ):
        with pytest.raises(ValueError):
            validate_review(invalid, envelope)


def test_complete_batch_detects_condition_mismatch(
    tmp_path: Path, config: ExperimentConfig
) -> None:
    envelope = _runner(tmp_path, config)._envelope()
    attempt = StoredAttempt(
        "id",
        CASES[0].case_id,
        "easy",
        "retrieval-enabled",
        envelope.config_identity,
        _record(question=CASES[0].question, model="model-1", enabled=False),
    )
    with pytest.raises(ValueError, match="incomplete"):
        validate_complete_batch(envelope, (attempt,))


def test_loader_reconstructs_complete_artifacts_and_rejects_changed_attempts(
    tmp_path: Path, config: ExperimentConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_answer_case(**kwargs: object) -> AttemptRecord:
        adapter = kwargs["adapter"]
        question = kwargs["question"]
        enabled = kwargs["retrieval_enabled"]
        assert (
            isinstance(adapter, _Adapter)
            and isinstance(question, str)
            and isinstance(enabled, bool)
        )
        return _record(question=question, model=adapter.model, enabled=enabled)

    monkeypatch.setattr("middle_earth_travel_agency.lore_experiment.answer_case", fake_answer_case)
    result = asyncio.run(_runner(tmp_path, config).run())
    loaded = load_run_artifacts(result.output_dir)
    assert loaded.envelope == result.envelope
    assert loaded.attempts == result.attempts
    lines = (result.output_dir / "attempts.jsonl").read_text().splitlines()
    changed = json.loads(lines[0])
    changed["config_identity"] = "changed"
    lines[0] = json.dumps(changed)
    (result.output_dir / "attempts.jsonl").write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match="attempt"):
        load_run_artifacts(result.output_dir)
