"""A small, application-owned tool loop for one lore-answering attempt.

The experiment deliberately does not use LangChain's agent runtime.  Keeping the
loop here makes the only authority exposed to a model explicit and makes a fake
adapter sufficient for tests and offline qualification work.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from .experiment_config import ExperimentConfig
from .retrieval_index import ContextResult, EvidencePassage, SearchResult


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_MAX_ERROR_MESSAGE = 240
SYSTEM_PROMPT = (
    "Answer the user's question using approved lore tools when useful. "
    "Finish only by calling submit_answer. Use insufficient_evidence when the "
    "available evidence cannot support an answer."
)


SEARCH_LORE_SCHEMA: dict[str, object] = {
    "type": "function",
    "function": {
        "name": "search_lore",
        "description": "Search the approved lore passages for a plain-text query.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["query"],
            "properties": {"query": {"type": "string", "minLength": 1}},
        },
    },
}
GET_LORE_CONTEXT_SCHEMA: dict[str, object] = {
    "type": "function",
    "function": {
        "name": "get_lore_context",
        "description": "Get immediate approved context for a passage returned by search_lore.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["passage_id"],
            "properties": {"passage_id": {"type": "string", "minLength": 1}},
        },
    },
}
SUBMIT_ANSWER_SCHEMA: dict[str, object] = {
    "type": "function",
    "function": {
        "name": "submit_answer",
        "description": "Submit the one final answer or an honest insufficient-evidence result.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["outcome", "answer", "evidence_passage_ids"],
            "properties": {
                "outcome": {"type": "string", "enum": ["answered", "insufficient_evidence"]},
                "answer": {"type": "string"},
                "evidence_passage_ids": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                },
            },
        },
    },
}

RETRIEVAL_TOOLS = (SEARCH_LORE_SCHEMA, GET_LORE_CONTEXT_SCHEMA)
ALL_TOOLS = (*RETRIEVAL_TOOLS, SUBMIT_ANSWER_SCHEMA)


@dataclass(frozen=True)
class FinalSubmission:
    outcome: str
    answer: str
    evidence_passage_ids: tuple[str, ...]


@dataclass(frozen=True)
class ToolTraceRecord:
    call_id: str
    name: str
    valid: bool
    executed: bool
    budget_before: int
    budget_after: int
    evidence_passage_ids: tuple[str, ...] = ()
    message: str | None = None


@dataclass(frozen=True)
class AttemptError:
    code: str
    stage: str
    message: str


@dataclass(frozen=True)
class AttemptRecord:
    """Terminal, secret-free result for a single model/question/condition cell."""

    question: str
    model: str
    retrieval_enabled: bool
    classification: str
    outcome: str | None
    answer: str | None
    evidence_passage_ids: tuple[str, ...]
    evidence: tuple[EvidencePassage, ...]
    tool_trace: tuple[ToolTraceRecord, ...]
    error: AttemptError | None
    provider_request_count: int
    retry_count: int
    duration_seconds: float
    returned_model: str | None = None
    usage: Mapping[str, int] | None = None


@dataclass(frozen=True)
class ModelTurn:
    """Provider-neutral normalized model response used by deterministic fakes."""

    message: AIMessage
    model: str | None = None
    usage: Mapping[str, int] | None = None


class ModelAdapter(Protocol):
    model: str

    async def invoke(
        self, messages: Sequence[BaseMessage], tools: Sequence[Mapping[str, object]]
    ) -> ModelTurn: ...


class LoreRetrieval(Protocol):
    """The narrow read-only retrieval capability required by one attempt."""

    def search(self, query: str) -> list[SearchResult]: ...

    def context(self, passage_id: str) -> ContextResult: ...


class OpenRouterModelAdapter:
    """Minimal OpenRouter transport; orchestration stays in :func:`answer_case`."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        config: ExperimentConfig,
        client_factory: Any = ChatOpenAI,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("OpenRouter API key is required")
        self.model = model
        self._client = client_factory(
            model=model,
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            temperature=config.agent.temperature,
            max_tokens=config.agent.max_output_tokens,
            timeout=config.provider.request_timeout_seconds,
            max_retries=0,
            streaming=False,
        )

    async def invoke(
        self, messages: Sequence[BaseMessage], tools: Sequence[Mapping[str, object]]
    ) -> ModelTurn:
        response = await self._client.bind_tools(list(tools)).ainvoke(list(messages))
        if not isinstance(response, AIMessage):
            raise ValueError("provider returned an unsupported response")
        metadata = (
            response.response_metadata if isinstance(response.response_metadata, dict) else {}
        )
        usage_metadata = (
            response.usage_metadata if isinstance(response.usage_metadata, dict) else {}
        )
        usage = {
            str(key): value
            for key, value in usage_metadata.items()
            if isinstance(value, int) and not isinstance(value, bool)
        }
        returned_model = metadata.get("model_name") or metadata.get("model")
        return ModelTurn(response, str(returned_model) if returned_model else None, usage or None)


def _safe_message(value: object, fallback: str) -> str:
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    if not text:
        return fallback
    # Exception messages are not provider artifacts.  Keep only a concise category-safe hint.
    return text[:_MAX_ERROR_MESSAGE]


def _tool_message(call_id: str, content: object) -> ToolMessage:
    return ToolMessage(content=str(content), tool_call_id=call_id)


def _passage_payload(passage: EvidencePassage) -> dict[str, object]:
    return {
        "passage_id": passage.passage_id,
        "title": passage.title,
        "heading_path": list(passage.heading_path),
        "body": passage.body,
    }


def _search_payload(results: Sequence[SearchResult]) -> dict[str, object]:
    return {"passages": [_passage_payload(result.passage) for result in results]}


def _context_payload(result: ContextResult) -> dict[str, object]:
    return {
        "target": _passage_payload(result.target),
        "before": _passage_payload(result.before) if result.before else None,
        "before_boundary": result.before_boundary,
        "after": _passage_payload(result.after) if result.after else None,
        "after_boundary": result.after_boundary,
    }


def _tool_calls(message: AIMessage) -> list[dict[str, object]]:
    calls = message.tool_calls
    if not isinstance(calls, list):
        return []
    normalized: list[dict[str, object]] = []
    for call in calls:
        if not isinstance(call, dict):
            normalized.append({"name": "", "args": {}, "id": ""})
            continue
        normalized.append(
            {
                "name": call.get("name", ""),
                "args": call.get("args", {}),
                "id": call.get("id", ""),
            }
        )
    return normalized


def _submission(args: object, allowed_ids: set[str]) -> FinalSubmission | None:
    if not isinstance(args, dict) or set(args) != {"outcome", "answer", "evidence_passage_ids"}:
        return None
    outcome, answer, evidence = args["outcome"], args["answer"], args["evidence_passage_ids"]
    if (
        outcome not in {"answered", "insufficient_evidence"}
        or not isinstance(answer, str)
        or not answer.strip()
    ):
        return None
    if not isinstance(evidence, list) or any(
        not isinstance(item, str) or not item for item in evidence
    ):
        return None
    deduplicated = tuple(dict.fromkeys(evidence))
    if any(item not in allowed_ids for item in deduplicated):
        return None
    return FinalSubmission(outcome, answer.strip(), deduplicated)


def _provider_status(error: BaseException) -> int | None:
    status = getattr(error, "status_code", None)
    if isinstance(status, int):
        return status
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    return status if isinstance(status, int) else None


def _retry_after(error: BaseException) -> float | None:
    headers = getattr(getattr(error, "response", None), "headers", None)
    value = headers.get("retry-after") if headers is not None else None
    if not isinstance(value, (str, int, float)):
        return None
    try:
        delay = float(value)
    except (TypeError, ValueError):
        return None
    return delay if delay >= 0 else None


def _is_transient(error: BaseException) -> bool:
    status = _provider_status(error)
    return (
        isinstance(error, (TimeoutError, OSError))
        or status == 429
        or (status is not None and status >= 500)
    )


async def _invoke_with_retry(
    adapter: ModelAdapter,
    messages: Sequence[BaseMessage],
    tools: Sequence[Mapping[str, object]],
    config: ExperimentConfig,
    deadline: float,
    stats: _ProviderCallStats,
) -> ModelTurn:
    while True:
        try:
            stats.requests += 1
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("attempt deadline exceeded")
            async with asyncio.timeout(min(remaining, config.provider.request_timeout_seconds)):
                return await adapter.invoke(messages, tools)
        except asyncio.CancelledError:
            raise
        except BaseException as error:
            if not _is_transient(error) or stats.retries >= config.provider.max_retries:
                raise _ProviderCallError(error) from None
            stats.retries += 1
            delay = _retry_after(error)
            if delay is None:
                delay = min(1.0 * (2 ** (stats.retries - 1)) + random.uniform(0.0, 0.25), 2.0)
            if time.monotonic() + delay >= deadline:
                raise _ProviderCallError(TimeoutError("attempt deadline exceeded")) from None
            await asyncio.sleep(delay)


class _ProviderCallError(Exception):
    def __init__(self, source: BaseException) -> None:
        self.source = source


@dataclass
class _ProviderCallStats:
    requests: int = 0
    retries: int = 0


def _failure(
    *,
    question: str,
    adapter: ModelAdapter,
    retrieval_enabled: bool,
    trace: Sequence[ToolTraceRecord],
    evidence: Mapping[str, EvidencePassage],
    code: str,
    stage: str,
    message: str,
    started: float,
    requests: int,
    retries: int,
) -> AttemptRecord:
    return AttemptRecord(
        question=question,
        model=adapter.model,
        retrieval_enabled=retrieval_enabled,
        classification="failed",
        outcome=None,
        answer=None,
        evidence_passage_ids=(),
        evidence=tuple(evidence.values()),
        tool_trace=tuple(trace),
        error=AttemptError(code, stage, _safe_message(message, "attempt failed")),
        provider_request_count=requests,
        retry_count=retries,
        duration_seconds=time.monotonic() - started,
    )


async def answer_case(
    *,
    question: str,
    index: LoreRetrieval | None,
    retrieval_enabled: bool,
    adapter: ModelAdapter,
    config: ExperimentConfig,
) -> AttemptRecord:
    """Run one fresh, bounded attempt and return a terminal, sanitized record."""
    started = time.monotonic()
    deadline = started + config.provider.attempt_timeout_seconds
    trace: list[ToolTraceRecord] = []
    returned: dict[str, EvidencePassage] = {}
    searched_ids: set[str] = set()
    budget = config.agent.retrieval_budget
    provider_calls = _ProviderCallStats()
    messages: list[BaseMessage] = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=question),
    ]
    final_only = False
    # Each non-final turn must consume a retrieval slot or terminate.  The extra two
    # calls cover the initial response and the required final-only invocation.
    turn_ceiling = budget + 2
    try:
        async with asyncio.timeout(config.provider.attempt_timeout_seconds):
            for _ in range(turn_ceiling):
                tools: tuple[Mapping[str, object], ...] = (
                    (SUBMIT_ANSWER_SCHEMA,) if final_only else ALL_TOOLS
                )
                turn = await _invoke_with_retry(
                    adapter, messages, tools, config, deadline, provider_calls
                )
                calls = _tool_calls(turn.message)
                if not calls:
                    return _failure(
                        question=question,
                        adapter=adapter,
                        retrieval_enabled=retrieval_enabled,
                        trace=trace,
                        evidence=returned,
                        code="missing_submission",
                        stage="submission",
                        message="model did not submit a terminal answer",
                        started=started,
                        requests=provider_calls.requests,
                        retries=provider_calls.retries,
                    )
                final_calls = [call for call in calls if call["name"] == "submit_answer"]
                if final_calls:
                    if len(calls) != 1 or len(final_calls) != 1:
                        return _failure(
                            question=question,
                            adapter=adapter,
                            retrieval_enabled=retrieval_enabled,
                            trace=trace,
                            evidence=returned,
                            code="invalid_final_calls",
                            stage="submission",
                            message="a turn must contain exactly one final submission or retrieval calls",
                            started=started,
                            requests=provider_calls.requests,
                            retries=provider_calls.retries,
                        )
                    submission = _submission(final_calls[0]["args"], set(returned))
                    if submission is None:
                        return _failure(
                            question=question,
                            adapter=adapter,
                            retrieval_enabled=retrieval_enabled,
                            trace=trace,
                            evidence=returned,
                            code="invalid_submission",
                            stage="submission",
                            message="submit_answer must have a valid typed outcome and in-scope evidence IDs",
                            started=started,
                            requests=provider_calls.requests,
                            retries=provider_calls.retries,
                        )
                    grounded = submission.outcome == "answered" and bool(
                        submission.evidence_passage_ids
                    )
                    classification = (
                        "grounded"
                        if grounded
                        else "insufficient_evidence"
                        if submission.outcome == "insufficient_evidence"
                        else "ungrounded_answer"
                    )
                    selected = tuple(returned[item] for item in submission.evidence_passage_ids)
                    return AttemptRecord(
                        question=question,
                        model=adapter.model,
                        retrieval_enabled=retrieval_enabled,
                        classification=classification,
                        outcome=submission.outcome,
                        answer=submission.answer or None,
                        evidence_passage_ids=submission.evidence_passage_ids,
                        evidence=selected,
                        tool_trace=tuple(trace),
                        error=None,
                        provider_request_count=provider_calls.requests,
                        retry_count=provider_calls.retries,
                        duration_seconds=time.monotonic() - started,
                        returned_model=turn.model,
                        usage=turn.usage,
                    )
                if final_only:
                    return _failure(
                        question=question,
                        adapter=adapter,
                        retrieval_enabled=retrieval_enabled,
                        trace=trace,
                        evidence=returned,
                        code="missing_submission",
                        stage="submission",
                        message="model did not submit a terminal answer after retrieval ended",
                        started=started,
                        requests=provider_calls.requests,
                        retries=provider_calls.retries,
                    )

                messages.append(turn.message)
                for position, call in enumerate(calls):
                    call_id = (
                        call["id"]
                        if isinstance(call["id"], str) and call["id"]
                        else f"call-{position}"
                    )
                    name = call["name"] if isinstance(call["name"], str) else ""
                    before = budget
                    if budget <= 0:
                        trace.append(
                            ToolTraceRecord(
                                call_id,
                                name,
                                False,
                                False,
                                before,
                                before,
                                message="budget exhausted",
                            )
                        )
                        messages.append(
                            _tool_message(call_id, "No further retrieval is available.")
                        )
                        continue
                    budget -= 1
                    args = call["args"]
                    if (
                        name == "search_lore"
                        and isinstance(args, dict)
                        and set(args) == {"query"}
                        and isinstance(args.get("query"), str)
                        and args["query"].strip()
                    ):
                        results = (
                            index.search(args["query"].strip())
                            if retrieval_enabled and index
                            else []
                        )
                        ids = tuple(result.passage_id for result in results)
                        for result in results:
                            returned[result.passage_id] = result.passage
                            searched_ids.add(result.passage_id)
                        trace.append(
                            ToolTraceRecord(call_id, name, True, True, before, budget, ids)
                        )
                        messages.append(_tool_message(call_id, _search_payload(results)))
                    elif (
                        name == "get_lore_context"
                        and isinstance(args, dict)
                        and set(args) == {"passage_id"}
                        and isinstance(args.get("passage_id"), str)
                        and args["passage_id"] in searched_ids
                    ):
                        if retrieval_enabled and index:
                            context = index.context(args["passage_id"])
                            passages = [context.target, context.before, context.after]
                            ids = tuple(item.passage_id for item in passages if item is not None)
                            for item in passages:
                                if item is not None:
                                    returned[item.passage_id] = item
                            payload: object = _context_payload(context)
                        else:
                            ids = ()
                            payload = {"passages": []}
                        trace.append(
                            ToolTraceRecord(call_id, name, True, True, before, budget, ids)
                        )
                        messages.append(_tool_message(call_id, payload))
                    else:
                        trace.append(
                            ToolTraceRecord(
                                call_id,
                                name,
                                False,
                                False,
                                before,
                                budget,
                                message="use search_lore(query) or context for a returned passage ID",
                            )
                        )
                        messages.append(
                            _tool_message(
                                call_id,
                                "Invalid retrieval request. Use search_lore(query), or get_lore_context for a passage ID returned by search_lore.",
                            )
                        )
                if budget == 0:
                    final_only = True
                    messages.append(
                        HumanMessage(
                            content="No further retrieval is available. Submit the final answer now."
                        )
                    )
    except asyncio.TimeoutError:
        return _failure(
            question=question,
            adapter=adapter,
            retrieval_enabled=retrieval_enabled,
            trace=trace,
            evidence=returned,
            code="attempt_timeout",
            stage="provider",
            message="attempt deadline exceeded",
            started=started,
            requests=provider_calls.requests,
            retries=provider_calls.retries,
        )
    except _ProviderCallError as error:
        status = _provider_status(error.source)
        code = (
            "provider_timeout"
            if isinstance(error.source, TimeoutError)
            else "provider_request_failed"
        )
        if status in {401, 403}:
            code = "provider_authorization_failed"
        return _failure(
            question=question,
            adapter=adapter,
            retrieval_enabled=retrieval_enabled,
            trace=trace,
            evidence=returned,
            code=code,
            stage="provider",
            message="provider request did not complete",
            started=started,
            requests=provider_calls.requests,
            retries=provider_calls.retries,
        )
    except (ValueError, RuntimeError):
        return _failure(
            question=question,
            adapter=adapter,
            retrieval_enabled=retrieval_enabled,
            trace=trace,
            evidence=returned,
            code="retrieval_failed",
            stage="retrieval",
            message="retrieval operation failed",
            started=started,
            requests=provider_calls.requests,
            retries=provider_calls.retries,
        )
    return _failure(
        question=question,
        adapter=adapter,
        retrieval_enabled=retrieval_enabled,
        trace=trace,
        evidence=returned,
        code="turn_limit_exceeded",
        stage="orchestration",
        message="model did not reach a terminal submission within the configured bound",
        started=started,
        requests=provider_calls.requests,
        retries=provider_calls.retries,
    )
