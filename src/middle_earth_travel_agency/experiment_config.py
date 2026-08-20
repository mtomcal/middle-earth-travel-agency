"""Strict, non-secret configuration for the disposable grounding experiment."""

from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml


SCHEMA_VERSION = 1


class _StrictSafeLoader(yaml.SafeLoader):
    """Safe loader which also rejects duplicate keys and YAML merges."""

    def flatten_mapping(self, node: yaml.MappingNode) -> None:
        if any(key_node.tag == "tag:yaml.org,2002:merge" for key_node, _ in node.value):
            raise ValueError("YAML merge keys are not supported")
        super().flatten_mapping(node)

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[object, object]:
        mapping: dict[object, object] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError(f"duplicate YAML key: {key!r}")
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


@dataclass(frozen=True)
class IndexConfig:
    tokenizer: str
    remove_diacritics: int


@dataclass(frozen=True)
class RetrievalConfig:
    query_mode: str
    result_limit: int
    title_weight: float
    heading_weight: float
    body_weight: float
    tie_breaker: str

    @property
    def weights(self) -> tuple[float, float, float]:
        """BM25 weights in FTS column order: title, heading, body."""
        return (self.title_weight, self.heading_weight, self.body_weight)


@dataclass(frozen=True)
class AgentConfig:
    retrieval_budget: int
    temperature: float
    max_output_tokens: int


@dataclass(frozen=True)
class ProviderConfig:
    request_timeout_seconds: float
    attempt_timeout_seconds: float
    max_retries: int


@dataclass(frozen=True)
class RunnerConfig:
    max_concurrency: int


@dataclass(frozen=True)
class ReportConfig:
    evidence_excerpt_characters: int


@dataclass(frozen=True)
class ExperimentEnvironment:
    """Validated process-local provider credentials and candidate model order."""

    openrouter_api_key: str = field(repr=False)
    models: tuple[str, ...]


@dataclass(frozen=True)
class ExperimentConfig:
    """Validated, immutable configuration with no credentials or model identifiers."""

    index: IndexConfig
    retrieval: RetrievalConfig
    agent: AgentConfig
    provider: ProviderConfig
    runner: RunnerConfig
    report: ReportConfig
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return normalized values suitable for index and run metadata."""
        return {
            "schema_version": self.schema_version,
            "index": {
                "tokenizer": self.index.tokenizer,
                "remove_diacritics": self.index.remove_diacritics,
            },
            "retrieval": {
                "query_mode": self.retrieval.query_mode,
                "result_limit": self.retrieval.result_limit,
                "title_weight": self.retrieval.title_weight,
                "heading_weight": self.retrieval.heading_weight,
                "body_weight": self.retrieval.body_weight,
                "tie_breaker": self.retrieval.tie_breaker,
            },
            "agent": {
                "retrieval_budget": self.agent.retrieval_budget,
                "temperature": self.agent.temperature,
                "max_output_tokens": self.agent.max_output_tokens,
            },
            "provider": {
                "request_timeout_seconds": self.provider.request_timeout_seconds,
                "attempt_timeout_seconds": self.provider.attempt_timeout_seconds,
                "max_retries": self.provider.max_retries,
            },
            "runner": {"max_concurrency": self.runner.max_concurrency},
            "report": {"evidence_excerpt_characters": self.report.evidence_excerpt_characters},
        }

    def canonical_json(self) -> str:
        """Return the canonical serialization used for configuration identity."""
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @property
    def config_identity(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    @property
    def index_identity(self) -> str:
        """Identify only settings that require a new retrieval index."""
        values = self.to_dict()
        serialized = json.dumps(
            {
                "schema_version": self.schema_version,
                "index": values["index"],
                "retrieval": values["retrieval"],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _mapping(value: object, name: str, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise ValueError(f"{name} contains a non-string key")
    keys = set(value)
    missing = fields - keys
    unknown = keys - fields
    if missing:
        raise ValueError(f"{name} is missing required field(s): {', '.join(sorted(missing))}")
    if unknown:
        raise ValueError(f"{name} contains unknown field(s): {', '.join(sorted(unknown))}")
    return value


def _integer(value: object, name: str, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _number(value: object, name: str, minimum: float, maximum: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    normalized = float(value)
    if not math.isfinite(normalized) or not minimum <= normalized <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return normalized


def _choice(value: object, name: str, choices: set[str]) -> str:
    if not isinstance(value, str) or value not in choices:
        options = ", ".join(sorted(choices))
        raise ValueError(f"{name} must be one of: {options}")
    return value


def _load_document(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as stream:
            document = yaml.load(stream, Loader=_StrictSafeLoader)
    except (OSError, yaml.YAMLError, ValueError) as error:
        raise ValueError(f"invalid experiment configuration {path}: {error}") from error
    return _mapping(
        document,
        "configuration",
        {"schema_version", "index", "retrieval", "agent", "provider", "runner", "report"},
    )


def load_experiment_config(path: Path) -> ExperimentConfig:
    """Load and validate the complete Phase 0 experiment YAML document."""
    document = _load_document(path)
    schema_version = _integer(
        document["schema_version"], "schema_version", SCHEMA_VERSION, SCHEMA_VERSION
    )

    index = _mapping(document["index"], "index", {"tokenizer", "remove_diacritics"})
    retrieval = _mapping(
        document["retrieval"],
        "retrieval",
        {
            "query_mode",
            "result_limit",
            "title_weight",
            "heading_weight",
            "body_weight",
            "tie_breaker",
        },
    )
    agent = _mapping(
        document["agent"], "agent", {"retrieval_budget", "temperature", "max_output_tokens"}
    )
    provider = _mapping(
        document["provider"],
        "provider",
        {"request_timeout_seconds", "attempt_timeout_seconds", "max_retries"},
    )
    runner = _mapping(document["runner"], "runner", {"max_concurrency"})
    report = _mapping(document["report"], "report", {"evidence_excerpt_characters"})

    index_config = IndexConfig(
        tokenizer=_choice(index["tokenizer"], "tokenizer", {"unicode61", "porter-unicode61"}),
        remove_diacritics=_integer(index["remove_diacritics"], "remove_diacritics", 0, 2),
    )
    retrieval_config = RetrievalConfig(
        query_mode=_choice(retrieval["query_mode"], "query_mode", {"all-terms", "any-terms"}),
        result_limit=_integer(retrieval["result_limit"], "result_limit", 1, 50),
        title_weight=_number(retrieval["title_weight"], "title_weight", 0, 100),
        heading_weight=_number(retrieval["heading_weight"], "heading_weight", 0, 100),
        body_weight=_number(retrieval["body_weight"], "body_weight", 0, 100),
        tie_breaker=_choice(
            retrieval["tie_breaker"], "tie_breaker", {"passage-id", "title-then-passage-id"}
        ),
    )
    if not any(retrieval_config.weights):
        raise ValueError("at least one retrieval weight must be greater than zero")

    agent_config = AgentConfig(
        retrieval_budget=_integer(agent["retrieval_budget"], "retrieval_budget", 1, 20),
        temperature=_number(agent["temperature"], "temperature", 0, 2),
        max_output_tokens=_integer(agent["max_output_tokens"], "max_output_tokens", 64, 8192),
    )
    provider_config = ProviderConfig(
        request_timeout_seconds=_number(
            provider["request_timeout_seconds"], "request_timeout_seconds", 1, 600
        ),
        attempt_timeout_seconds=_number(
            provider["attempt_timeout_seconds"], "attempt_timeout_seconds", 1, 3600
        ),
        max_retries=_integer(provider["max_retries"], "max_retries", 0, 3),
    )
    if provider_config.attempt_timeout_seconds < provider_config.request_timeout_seconds:
        raise ValueError("attempt_timeout_seconds must not be less than request_timeout_seconds")

    return ExperimentConfig(
        schema_version=schema_version,
        index=index_config,
        retrieval=retrieval_config,
        agent=agent_config,
        provider=provider_config,
        runner=RunnerConfig(
            max_concurrency=_integer(runner["max_concurrency"], "max_concurrency", 1, 5)
        ),
        report=ReportConfig(
            evidence_excerpt_characters=_integer(
                report["evidence_excerpt_characters"], "evidence_excerpt_characters", 200, 4000
            )
        ),
    )


def load_experiment_environment(
    environment: Mapping[str, str] | None = None,
) -> ExperimentEnvironment:
    """Read the two Phase 0 environment values without mutating process state."""
    values = os.environ if environment is None else environment
    api_key = values.get("META_OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise ValueError("META_OPENROUTER_API_KEY is absent")

    raw_models = values.get("META_EXPERIMENT_MODELS", "")
    models = tuple(model.strip() for model in raw_models.split(","))
    if len(models) != 5 or any(not model for model in models) or len(set(models)) != len(models):
        raise ValueError("META_EXPERIMENT_MODELS must contain exactly five unique non-empty models")
    return ExperimentEnvironment(openrouter_api_key=api_key, models=models)
