"""Durable, deliberately small orchestration for the grounding experiment."""
# pyright: reportArgumentType=false

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import tempfile
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from .experiment_config import (
    AgentConfig,
    ExperimentConfig,
    IndexConfig,
    ProviderConfig,
    ReportConfig,
    RetrievalConfig,
    RunnerConfig,
)
from .lore_agent import (
    SYSTEM_PROMPT,
    AttemptError,
    AttemptRecord,
    ModelAdapter,
    ToolTraceRecord,
    answer_case,
)
from .retrieval_index import EvidencePassage, RetrievalIndex


RUN_SCHEMA_VERSION = 1
REVIEW_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ExperimentCase:
    case_id: str
    difficulty: str
    question: str
    review_focus: str
    expected_evidence_passage_ids: tuple[str, ...]


CASES = (
    ExperimentCase(
        "easy-01",
        "easy",
        "Who rules Lothlórien, and from what city do they rule?",
        "Direct title/lead lookup with two names and one place.",
        ("passage_cd951a6124c61d767a60ef128cca6b70dda0f4c89c0ee105e19c2419c07392f5",),
    ),
    ExperimentCase(
        "easy-02",
        "easy",
        "Who killed Smaug, and what weakness made it possible?",
        "Direct causal fact in one plot passage.",
        ("passage_250e73944f58316003ff1267d838a55d69479385f1d82eb5ea1fc61f732f1a67",),
    ),
    ExperimentCase(
        "easy-03",
        "easy",
        "Where was Shelob's lair, and why did Sauron leave her there?",
        "Direct location and motivation in one passage.",
        ("passage_61b36ab0308d24de5ddbf55d86e2c9404372f0a4324c830a7431ad1ece67c28b",),
    ),
    ExperimentCase(
        "easy-04",
        "easy",
        "What drove Boromir to seize the Ring, and how did he respond after realizing his betrayal?",
        "Two straightforward passages connecting motivation and repentance.",
        (
            "passage_1cbc40ac40853d82cf2b93735ee4bc165e456fd095bd8d8b7fe6a905eceeff49",
            "passage_9709fe8f54b6d7b80b0939729d3d6b25793fdb843cdc7b6f040c63163065aa31",
        ),
    ),
    ExperimentCase(
        "easy-05",
        "easy",
        "What happened to Isildur and the Ring at the Gladden Fields?",
        "Direct event lookup in one passage.",
        ("passage_0e39706c45f9b4d43647d85549519ec791b69809d6a81295af93a7e5e35d5bfa",),
    ),
    ExperimentCase(
        "hard-01",
        "hard",
        "Explain how Sauron's deception contributed to Númenor's fall and the later founding of Gondor and Arnor.",
        "Multi-passage chronology and causality within the Second Age.",
        (
            "passage_2f3d4f6b4936b65ea4378ff2b685cc08acf4a4302efc8a6014068d07e4e708c1",
            "passage_039470affe9dc665c38734b224857dd3babfeb6b078006adebf317b0bc912b0e",
        ),
    ),
    ExperimentCase(
        "hard-02",
        "hard",
        "Explain why the Captains of the West marched to the Morannon after the Pelennor Fields and how their plan helped Frodo and Sam.",
        "Connects the post-battle decision to the diversion at the Black Gate.",
        (
            "passage_e2f25ce5188a7d76407225471da1033dfa6c4eb984f83cd6d2b7846780ca9560",
            "passage_2848f46126ff06c152afd2669d8b27292ade954769215e0afe8bad0d0aec5602",
        ),
    ),
    ExperimentCase(
        "hard-03",
        "hard",
        "Explain how the Ents and Huorns contributed differently to Saruman's defeats at Isengard and Helm's Deep.",
        "Cross-article comparison of two related but distinct interventions.",
        (
            "passage_42e06d8c76bf5944cd1aa20ce0efecd7105e709d0067e934a9ac9d98cb53caaa",
            "passage_1e4067a9580322f1cb2fa54465fdc7fc8dbeddaf5e4231075c556c865fb0164e",
        ),
    ),
    ExperimentCase(
        "hard-04",
        "hard",
        "Compare Sauron's influence over Saruman and Denethor through the palantíri, including the limits of that influence.",
        "Cross-article comparison requiring restraint about what the passages actually establish.",
        (
            "passage_42e06d8c76bf5944cd1aa20ce0efecd7105e709d0067e934a9ac9d98cb53caaa",
            "passage_9b1aa84909139eec31b0fa35944fcbede350bc51a521f80b4f2cd1915e1e217b",
        ),
    ),
    ExperimentCase(
        "hard-05",
        "hard",
        "Explain how the apparent Corsair fleet changed the Battle of the Pelennor Fields, who was actually aboard, and why its arrival became the turning point.",
        "Multi-passage battlefield state, reveal, and causal synthesis.",
        (
            "passage_464b301a0b822f177bcadcb56c8ff6913ef5419f9a6ffb150af03ef4930a54b5",
            "passage_bac1edca70491adbea6ebd60d8bfe3cd9dfef5231cb9f2b951a68009d31ca878",
        ),
    ),
)


@dataclass(frozen=True)
class RunEnvelope:
    run_id: str
    created_at: str
    source_revision: str
    release_id: str
    manifest_sha256: str
    index_build_identity: str
    config_identity: str
    config: dict[str, object]
    models: tuple[str, ...]
    cases: tuple[ExperimentCase, ...]
    conditions: tuple[str, ...]
    expected_attempts: int
    prompt_identity: str
    schema_version: int = RUN_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "source_revision": self.source_revision,
            "release_id": self.release_id,
            "manifest_sha256": self.manifest_sha256,
            "index_build_identity": self.index_build_identity,
            "config_identity": self.config_identity,
            "config": self.config,
            "models": list(self.models),
            "cases": [asdict(case) for case in self.cases],
            "conditions": list(self.conditions),
            "expected_attempts": self.expected_attempts,
            "prompt_identity": self.prompt_identity,
        }


@dataclass(frozen=True)
class StoredAttempt:
    attempt_id: str
    case_id: str
    difficulty: str
    condition: str
    config_identity: str
    record: AttemptRecord

    def to_dict(self) -> dict[str, object]:
        value = asdict(self.record)
        value["evidence"] = [
            {**item, "heading_path": list(item["heading_path"])} for item in value["evidence"]
        ]
        value["tool_trace"] = [
            {**item, "evidence_passage_ids": list(item["evidence_passage_ids"])}
            for item in value["tool_trace"]
        ]
        value["evidence_passage_ids"] = list(value["evidence_passage_ids"])
        return {
            "attempt_id": self.attempt_id,
            "case_id": self.case_id,
            "difficulty": self.difficulty,
            "condition": self.condition,
            "config_identity": self.config_identity,
            **value,
        }


@dataclass(frozen=True)
class RunResult:
    envelope: RunEnvelope
    attempts: tuple[StoredAttempt, ...]
    output_dir: Path


@dataclass(frozen=True)
class ReviewDecision:
    run_id: str
    decision: str
    selected_model: str | None
    rationale: str


class BatchFailure(RuntimeError):
    """A durable run failed globally and is ineligible for qualification."""


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _attempt_id(run_id: str, case_id: str, model: str, condition: str) -> str:
    return hashlib.sha256(f"{run_id}\0{case_id}\0{model}\0{condition}".encode()).hexdigest()


def _prompt_identity() -> str:
    return hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()


def _validate_cases(
    cases: Sequence[ExperimentCase], index: RetrievalIndex
) -> tuple[ExperimentCase, ...]:
    normalized = tuple(cases)
    if len(normalized) != 10 or {case.difficulty for case in normalized} != {"easy", "hard"}:
        raise ValueError("the experiment requires exactly five easy and five hard cases")
    if (
        sum(case.difficulty == "easy" for case in normalized) != 5
        or sum(case.difficulty == "hard" for case in normalized) != 5
    ):
        raise ValueError("the experiment requires exactly five easy and five hard cases")
    if (
        len({case.case_id for case in normalized}) != 10
        or len({case.question for case in normalized}) != 10
    ):
        raise ValueError("experiment case IDs and questions must be unique")
    for case in normalized:
        if not case.case_id or not case.question or not case.expected_evidence_passage_ids:
            raise ValueError("experiment cases must be complete")
        for passage_id in case.expected_evidence_passage_ids:
            index.context(passage_id)
    return normalized


def _validate_models(models: Sequence[str]) -> tuple[str, ...]:
    result = tuple(models)
    if len(result) != 5 or any(not isinstance(model, str) or not model.strip() for model in result):
        raise ValueError("exactly five non-empty models are required")
    if len(set(result)) != len(result):
        raise ValueError("experiment models must be unique")
    return result


def _validate_config(config: ExperimentConfig) -> None:
    """Validate direct construction with the same bounds as the YAML boundary."""
    if not isinstance(config, ExperimentConfig) or config.schema_version != 1:
        raise ValueError("experiment configuration is invalid")
    index, retrieval = config.index, config.retrieval
    agent, provider, runner, report = config.agent, config.provider, config.runner, config.report
    valid = (
        index.tokenizer in {"unicode61", "porter-unicode61"}
        and index.remove_diacritics in {0, 1, 2}
        and retrieval.query_mode in {"all-terms", "any-terms"}
        and isinstance(retrieval.result_limit, int)
        and 1 <= retrieval.result_limit <= 50
        and retrieval.tie_breaker in {"passage-id", "title-then-passage-id"}
        and all(
            isinstance(weight, (int, float)) and not isinstance(weight, bool) and 0 <= weight <= 100
            for weight in retrieval.weights
        )
        and any(retrieval.weights)
        and isinstance(agent.retrieval_budget, int)
        and 1 <= agent.retrieval_budget <= 20
        and isinstance(agent.temperature, (int, float))
        and not isinstance(agent.temperature, bool)
        and 0 <= agent.temperature <= 2
        and isinstance(agent.max_output_tokens, int)
        and 64 <= agent.max_output_tokens <= 8192
        and isinstance(provider.request_timeout_seconds, (int, float))
        and isinstance(provider.attempt_timeout_seconds, (int, float))
        and 1 <= provider.request_timeout_seconds <= 600
        and provider.request_timeout_seconds <= provider.attempt_timeout_seconds <= 3600
        and isinstance(provider.max_retries, int)
        and 0 <= provider.max_retries <= 3
        and isinstance(runner.max_concurrency, int)
        and 1 <= runner.max_concurrency <= 5
        and isinstance(report.evidence_excerpt_characters, int)
        and 200 <= report.evidence_excerpt_characters <= 4000
    )
    if (
        not valid
        or config.config_identity != hashlib.sha256(config.canonical_json().encode()).hexdigest()
    ):
        raise ValueError("experiment configuration is invalid")


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_json(path: Path, value: object) -> None:
    """Atomically publish a retained record before any provider work starts."""
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _sync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def _append_attempt(path: Path, attempt: StoredAttempt) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(_canonical(attempt.to_dict()) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


class ExperimentRunner:
    """Run fresh stateless model cells in stable disabled-then-enabled waves."""

    def __init__(
        self,
        *,
        index: RetrievalIndex,
        config: ExperimentConfig,
        models: Sequence[str],
        adapter_factory: Callable[[str], ModelAdapter],
        output_dir: Path,
        source_revision: str,
        cases: Sequence[ExperimentCase] = CASES,
        run_id_factory: Callable[[], str] | None = None,
    ) -> None:
        _validate_config(config)
        self._index = index
        self._config = config
        self._models = _validate_models(models)
        self._adapter_factory = adapter_factory
        self._output_dir = output_dir
        self._source_revision = source_revision
        self._cases = _validate_cases(cases, index)
        self._run_id_factory = run_id_factory or (lambda: uuid.uuid4().hex)

    def _envelope(self) -> RunEnvelope:
        metadata = self._index.metadata
        return RunEnvelope(
            run_id=self._run_id_factory(),
            created_at=datetime.now(UTC).isoformat(),
            source_revision=self._source_revision,
            release_id=metadata.release_id,
            manifest_sha256=metadata.manifest_sha256,
            index_build_identity=metadata.build_identity,
            config_identity=self._config.config_identity,
            config=self._config.to_dict(),
            models=self._models,
            cases=self._cases,
            conditions=("retrieval-disabled", "retrieval-enabled"),
            expected_attempts=100,
            prompt_identity=_prompt_identity(),
        )

    async def run(self) -> RunResult:
        if self._output_dir.exists():
            raise FileExistsError(
                f"refusing to reuse experiment output directory: {self._output_dir}"
            )
        envelope = self._envelope()
        self._output_dir.mkdir(parents=True)
        _write_json(self._output_dir / "run.json", envelope.to_dict())
        _write_json(
            self._output_dir / "review.json",
            {
                "schema_version": REVIEW_SCHEMA_VERSION,
                "run_id": envelope.run_id,
                "decision": None,
                "selected_model": None,
                "rationale": "",
            },
        )
        attempt_path = self._output_dir / "attempts.jsonl"
        semaphore = asyncio.Semaphore(self._config.runner.max_concurrency)
        checkpoint_lock = asyncio.Lock()
        completed: list[StoredAttempt] = []
        for case in self._cases:
            for retrieval_enabled in (False, True):
                condition = "retrieval-enabled" if retrieval_enabled else "retrieval-disabled"

                async def execute(model: str) -> StoredAttempt:
                    async with semaphore:
                        record = await answer_case(
                            question=case.question,
                            index=self._index if retrieval_enabled else None,
                            retrieval_enabled=retrieval_enabled,
                            adapter=self._adapter_factory(model),
                            config=self._config,
                        )
                    attempt = StoredAttempt(
                        _attempt_id(envelope.run_id, case.case_id, model, condition),
                        case.case_id,
                        case.difficulty,
                        condition,
                        envelope.config_identity,
                        record,
                    )
                    async with checkpoint_lock:
                        _append_attempt(attempt_path, attempt)
                        completed.append(attempt)
                    return attempt

                try:
                    async with asyncio.TaskGroup() as group:
                        tasks = [group.create_task(execute(model)) for model in self._models]
                except* OSError as error:
                    raise BatchFailure(
                        "could not durably checkpoint an experiment attempt"
                    ) from error
                wave = [task.result() for task in tasks]
                if any(
                    attempt.record.error
                    and attempt.record.error.code == "provider_authorization_failed"
                    for attempt in wave
                ):
                    raise BatchFailure(
                        "provider authorization failed; stopped after the durable wave"
                    )
        validate_complete_batch(envelope, completed)
        return RunResult(envelope, tuple(completed), self._output_dir)


def validate_complete_batch(envelope: RunEnvelope, attempts: Sequence[StoredAttempt]) -> None:
    if envelope.conditions != ("retrieval-disabled", "retrieval-enabled"):
        raise ValueError("experiment conditions are invalid")
    expected = {
        (case.case_id, model, condition)
        for case in envelope.cases
        for model in envelope.models
        for condition in envelope.conditions
    }
    actual = {(attempt.case_id, attempt.record.model, attempt.condition) for attempt in attempts}
    if (
        len(attempts) != envelope.expected_attempts
        or actual != expected
        or len(actual) != len(attempts)
    ):
        raise ValueError("experiment batch is incomplete or has duplicate attempt coordinates")
    for attempt in attempts:
        case = next(case for case in envelope.cases if case.case_id == attempt.case_id)
        if attempt.attempt_id != _attempt_id(
            envelope.run_id, attempt.case_id, attempt.record.model, attempt.condition
        ):
            raise ValueError("attempt ID does not match its immutable coordinate")
        if attempt.difficulty != case.difficulty:
            raise ValueError("attempt difficulty does not match the run envelope")
        if attempt.config_identity != envelope.config_identity:
            raise ValueError("attempt configuration identity does not match the run envelope")
        if attempt.record.question != case.question:
            raise ValueError("attempt question does not match the run envelope")
        if attempt.record.retrieval_enabled != (attempt.condition == "retrieval-enabled"):
            raise ValueError("attempt condition does not match its record")
        record = attempt.record
        if record.classification not in {
            "grounded",
            "ungrounded_answer",
            "insufficient_evidence",
            "failed",
        }:
            raise ValueError("attempt classification is invalid")
        if record.error is not None:
            if (
                record.classification != "failed"
                or record.outcome is not None
                or record.answer is not None
            ):
                raise ValueError("failed attempt is not terminally coherent")
        elif record.classification == "failed":
            raise ValueError("failed attempt has no error")
        elif record.classification == "grounded":
            if record.outcome != "answered" or not record.answer or not record.evidence_passage_ids:
                raise ValueError("grounded attempt is not terminally coherent")
        elif record.classification == "ungrounded_answer":
            if record.outcome != "answered" or not record.answer or record.evidence_passage_ids:
                raise ValueError("ungrounded attempt is not terminally coherent")
        elif (
            record.outcome != "insufficient_evidence"
            or not record.answer
            or not record.answer.strip()
        ):
            raise ValueError("insufficient-evidence attempt is not terminally coherent")
        if (
            record.provider_request_count < 0
            or record.retry_count < 0
            or record.duration_seconds < 0
        ):
            raise ValueError("attempt metrics are invalid")
        if len(set(record.evidence_passage_ids)) != len(record.evidence_passage_ids) or not set(
            record.evidence_passage_ids
        ).issubset({passage.passage_id for passage in record.evidence}):
            raise ValueError("attempt evidence IDs are invalid")


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid retained experiment artifact: {path}") from error


def _strict_mapping(value: object, keys: set[str], name: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{name} has an invalid schema")
    return value


def _strings(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be a string list")
    return tuple(value)


def _serialized_config(value: object) -> dict[str, object]:
    root = _strict_mapping(
        value,
        {"schema_version", "index", "retrieval", "agent", "provider", "runner", "report"},
        "run configuration",
    )
    index = _strict_mapping(
        root["index"], {"tokenizer", "remove_diacritics"}, "index configuration"
    )
    retrieval = _strict_mapping(
        root["retrieval"],
        {
            "query_mode",
            "result_limit",
            "title_weight",
            "heading_weight",
            "body_weight",
            "tie_breaker",
        },
        "retrieval configuration",
    )
    agent = _strict_mapping(
        root["agent"],
        {"retrieval_budget", "temperature", "max_output_tokens"},
        "agent configuration",
    )
    provider = _strict_mapping(
        root["provider"],
        {"request_timeout_seconds", "attempt_timeout_seconds", "max_retries"},
        "provider configuration",
    )
    runner = _strict_mapping(root["runner"], {"max_concurrency"}, "runner configuration")
    report = _strict_mapping(
        root["report"], {"evidence_excerpt_characters"}, "report configuration"
    )
    _validate_config(
        ExperimentConfig(
            IndexConfig(index["tokenizer"], index["remove_diacritics"]),
            RetrievalConfig(
                retrieval["query_mode"],
                retrieval["result_limit"],
                retrieval["title_weight"],
                retrieval["heading_weight"],
                retrieval["body_weight"],
                retrieval["tie_breaker"],
            ),
            AgentConfig(
                agent["retrieval_budget"], agent["temperature"], agent["max_output_tokens"]
            ),
            ProviderConfig(
                provider["request_timeout_seconds"],
                provider["attempt_timeout_seconds"],
                provider["max_retries"],
            ),
            RunnerConfig(runner["max_concurrency"]),
            ReportConfig(report["evidence_excerpt_characters"]),
            root["schema_version"],
        )
    )
    return root


def _load_envelope(value: object) -> RunEnvelope:
    fields = {
        "schema_version",
        "run_id",
        "created_at",
        "source_revision",
        "release_id",
        "manifest_sha256",
        "index_build_identity",
        "config_identity",
        "config",
        "models",
        "cases",
        "conditions",
        "expected_attempts",
        "prompt_identity",
    }
    document = _strict_mapping(value, fields, "run envelope")
    cases = (
        tuple(
            ExperimentCase(
                case_id=item["case_id"],
                difficulty=item["difficulty"],
                question=item["question"],
                review_focus=item["review_focus"],
                expected_evidence_passage_ids=_strings(
                    item["expected_evidence_passage_ids"], "case evidence"
                ),
            )
            for raw in document["cases"]
            for item in [
                _strict_mapping(
                    raw,
                    {
                        "case_id",
                        "difficulty",
                        "question",
                        "review_focus",
                        "expected_evidence_passage_ids",
                    },
                    "case",
                )
            ]
        )
        if isinstance(document["cases"], list)
        else ()
    )
    string_fields = (
        "run_id",
        "created_at",
        "source_revision",
        "release_id",
        "manifest_sha256",
        "index_build_identity",
        "config_identity",
        "prompt_identity",
    )
    if (
        document["schema_version"] != RUN_SCHEMA_VERSION
        or not isinstance(document["config"], dict)
        or not isinstance(document["expected_attempts"], int)
        or any(
            not isinstance(document[field], str) or not document[field] for field in string_fields
        )
    ):
        raise ValueError("run envelope has invalid values")
    envelope = RunEnvelope(
        run_id=document["run_id"],
        created_at=document["created_at"],
        source_revision=document["source_revision"],
        release_id=document["release_id"],
        manifest_sha256=document["manifest_sha256"],
        index_build_identity=document["index_build_identity"],
        config_identity=document["config_identity"],
        config=_serialized_config(document["config"]),
        models=_strings(document["models"], "models"),
        cases=cases,
        conditions=_strings(document["conditions"], "conditions"),
        expected_attempts=document["expected_attempts"],
        prompt_identity=document["prompt_identity"],
    )
    if hashlib.sha256(_canonical(envelope.config).encode()).hexdigest() != envelope.config_identity:
        raise ValueError("run envelope configuration identity is invalid")
    if (
        envelope.expected_attempts != 100
        or len(envelope.models) != 5
        or len(set(envelope.models)) != 5
    ):
        raise ValueError("run envelope has invalid experiment coordinates")
    if len(envelope.cases) != 10 or len({case.case_id for case in envelope.cases}) != 10:
        raise ValueError("run envelope has invalid cases")
    if (
        envelope.cases != CASES
        or envelope.conditions != ("retrieval-disabled", "retrieval-enabled")
        or envelope.prompt_identity != _prompt_identity()
    ):
        raise ValueError("run envelope does not match the approved experiment")
    return envelope


def _load_attempt(value: object) -> StoredAttempt:
    fields = {
        "attempt_id",
        "case_id",
        "difficulty",
        "condition",
        "config_identity",
        "question",
        "model",
        "retrieval_enabled",
        "classification",
        "outcome",
        "answer",
        "evidence_passage_ids",
        "evidence",
        "tool_trace",
        "error",
        "provider_request_count",
        "retry_count",
        "duration_seconds",
        "returned_model",
        "usage",
    }
    document = _strict_mapping(value, fields, "attempt")
    evidence = (
        tuple(
            EvidencePassage(
                item["passage_id"],
                item["article_artifact_id"],
                item["title"],
                _strings(item["heading_path"], "heading path"),
                item["ordinal"],
                item["body"],
            )
            for raw in document["evidence"]
            for item in [
                _strict_mapping(
                    raw,
                    {
                        "passage_id",
                        "article_artifact_id",
                        "title",
                        "heading_path",
                        "ordinal",
                        "body",
                    },
                    "evidence",
                )
            ]
        )
        if isinstance(document["evidence"], list)
        else ()
    )
    trace = (
        tuple(
            ToolTraceRecord(
                item["call_id"],
                item["name"],
                item["valid"],
                item["executed"],
                item["budget_before"],
                item["budget_after"],
                _strings(item["evidence_passage_ids"], "trace evidence"),
                item["message"],
            )
            for raw in document["tool_trace"]
            for item in [
                _strict_mapping(
                    raw,
                    {
                        "call_id",
                        "name",
                        "valid",
                        "executed",
                        "budget_before",
                        "budget_after",
                        "evidence_passage_ids",
                        "message",
                    },
                    "tool trace",
                )
            ]
        )
        if isinstance(document["tool_trace"], list)
        else ()
    )
    error = (
        None
        if document["error"] is None
        else AttemptError(
            **_strict_mapping(document["error"], {"code", "stage", "message"}, "attempt error")
        )
    )
    required_strings = (
        "attempt_id",
        "case_id",
        "difficulty",
        "condition",
        "config_identity",
        "question",
        "model",
        "classification",
    )
    if (
        any(not isinstance(document[field], str) for field in required_strings)
        or not isinstance(document["retrieval_enabled"], bool)
        or (document["outcome"] is not None and not isinstance(document["outcome"], str))
        or (document["answer"] is not None and not isinstance(document["answer"], str))
        or not isinstance(document["provider_request_count"], int)
        or not isinstance(document["retry_count"], int)
        or not isinstance(document["duration_seconds"], (int, float))
        or (
            document["returned_model"] is not None
            and not isinstance(document["returned_model"], str)
        )
        or (
            document["usage"] is not None
            and (
                not isinstance(document["usage"], dict)
                or any(
                    not isinstance(key, str) or not isinstance(count, int)
                    for key, count in document["usage"].items()
                )
            )
        )
    ):
        raise ValueError("attempt has invalid values")
    return StoredAttempt(
        document["attempt_id"],
        document["case_id"],
        document["difficulty"],
        document["condition"],
        document["config_identity"],
        AttemptRecord(
            document["question"],
            document["model"],
            document["retrieval_enabled"],
            document["classification"],
            document["outcome"],
            document["answer"],
            _strings(document["evidence_passage_ids"], "attempt evidence"),
            evidence,
            trace,
            error,
            document["provider_request_count"],
            document["retry_count"],
            float(document["duration_seconds"]),
            document["returned_model"],
            document["usage"],
        ),
    )


def load_run_artifacts(output_dir: Path) -> RunResult:
    """Strictly reconstruct one complete, immutable retained batch for rendering."""
    envelope = _load_envelope(_load_json(output_dir / "run.json"))
    try:
        lines = (output_dir / "attempts.jsonl").read_text(encoding="utf-8").splitlines()
        attempts = tuple(_load_attempt(json.loads(line)) for line in lines)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise ValueError("invalid retained experiment attempts") from error
    validate_complete_batch(envelope, attempts)
    return RunResult(envelope, attempts, output_dir)


def validate_review(value: Mapping[str, object], envelope: RunEnvelope) -> ReviewDecision:
    if set(value) != {"schema_version", "run_id", "decision", "selected_model", "rationale"}:
        raise ValueError("review record has an invalid schema")
    if value["schema_version"] != REVIEW_SCHEMA_VERSION or value["run_id"] != envelope.run_id:
        raise ValueError("review record does not match this run")
    decision = value["decision"]
    selected_model = value["selected_model"]
    rationale = value["rationale"]
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("review rationale is required")
    if (
        decision == "selected"
        and isinstance(selected_model, str)
        and selected_model in envelope.models
    ):
        return ReviewDecision(envelope.run_id, "selected", selected_model, rationale.strip())
    if decision == "none" and selected_model is None:
        return ReviewDecision(envelope.run_id, "none", None, rationale.strip())
    raise ValueError("review decision must select one configured model or select none")
