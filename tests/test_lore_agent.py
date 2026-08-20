import asyncio
from dataclasses import dataclass

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from middle_earth_travel_agency.experiment_config import (
    AgentConfig,
    ExperimentConfig,
    IndexConfig,
    ProviderConfig,
    ReportConfig,
    RetrievalConfig,
    RunnerConfig,
)
from middle_earth_travel_agency import lore_agent
from middle_earth_travel_agency.lore_agent import (
    ALL_TOOLS,
    GET_LORE_CONTEXT_SCHEMA,
    ModelTurn,
    OpenRouterModelAdapter,
    SEARCH_LORE_SCHEMA,
    SUBMIT_ANSWER_SCHEMA,
    SYSTEM_PROMPT,
    answer_case,
)
from middle_earth_travel_agency.retrieval_index import ContextResult, EvidencePassage, SearchResult


def _config(budget=4):
    return ExperimentConfig(
        index=IndexConfig("unicode61", 2),
        retrieval=RetrievalConfig("all-terms", 5, 5, 2, 1, "passage-id"),
        agent=AgentConfig(budget, 0, 1024),
        provider=ProviderConfig(1, 5, 1),
        runner=RunnerConfig(5),
        report=ReportConfig(200),
    )


PASSAGE = EvidencePassage("p-1", "article", "Gondor", ("History",), 1, "Minas Tirith.")


class Index:
    def search(self, query):
        assert query == "minas"
        return [SearchResult(PASSAGE, 0.0)]

    def context(self, passage_id):
        assert passage_id == "p-1"
        return ContextResult(PASSAGE, None, "section-edge", None, "section-edge")


class FailingIndex(Index):
    def search(self, query):
        raise ValueError("API_KEY=top-secret provider body")


@dataclass
class FakeAdapter:
    turns: list[object]
    model: str = "fake/model"

    def __post_init__(self):
        self.calls = []

    async def invoke(self, messages, tools):
        self.calls.append((list(messages), list(tools)))
        turn = self.turns.pop(0)
        if isinstance(turn, BaseException):
            raise turn
        assert isinstance(turn, AIMessage)
        return ModelTurn(turn, self.model, {"total_tokens": 3})


def _call(name, args, call_id):
    return {"name": name, "args": args, "id": call_id}


def _submit(outcome="answered", answer="A supported answer.", evidence=None):
    return AIMessage(
        content="",
        tool_calls=[
            _call(
                "submit_answer",
                {
                    "outcome": outcome,
                    "answer": answer,
                    "evidence_passage_ids": [] if evidence is None else evidence,
                },
                "submit",
            )
        ],
    )


def _run(adapter, *, index=None, enabled=True, config=None):
    return asyncio.run(
        answer_case(
            question="Where is Minas Tirith?",
            index=Index() if index is None else index,
            retrieval_enabled=enabled,
            adapter=adapter,
            config=_config() if config is None else config,
        )
    )


def _properties(schema):
    function = schema["function"]
    assert isinstance(function, dict)
    parameters = function["parameters"]
    assert isinstance(parameters, dict)
    properties = parameters["properties"]
    assert isinstance(properties, dict)
    return properties


def test_tool_schemas_expose_only_the_intended_plain_arguments():
    assert tuple(ALL_TOOLS) == (SEARCH_LORE_SCHEMA, GET_LORE_CONTEXT_SCHEMA, SUBMIT_ANSWER_SCHEMA)
    assert set(_properties(SEARCH_LORE_SCHEMA)) == {"query"}
    assert set(_properties(GET_LORE_CONTEXT_SCHEMA)) == {"passage_id"}
    assert set(_properties(SUBMIT_ANSWER_SCHEMA)) == {
        "outcome",
        "answer",
        "evidence_passage_ids",
    }


def test_enabled_attempt_searches_then_submits_grounded_answer():
    adapter = FakeAdapter(
        [
            AIMessage(content="", tool_calls=[_call("search_lore", {"query": "minas"}, "search")]),
            AIMessage(
                content="",
                tool_calls=[
                    _call(
                        "submit_answer",
                        {
                            "outcome": "answered",
                            "answer": "Minas Tirith is in Gondor.",
                            "evidence_passage_ids": ["p-1", "p-1"],
                        },
                        "submit",
                    )
                ],
            ),
        ]
    )

    record = asyncio.run(
        answer_case(
            question="Where is Minas Tirith?",
            index=Index(),
            retrieval_enabled=True,
            adapter=adapter,
            config=_config(),
        )
    )

    assert record.classification == "grounded"
    assert record.evidence_passage_ids == ("p-1",)
    assert record.tool_trace[0].budget_before == 4
    assert record.tool_trace[0].budget_after == 3
    assert adapter.calls[0][0][0].content == SYSTEM_PROMPT
    assert isinstance(adapter.calls[1][0][-1], ToolMessage)


def test_disabled_attempt_cannot_promote_memory_answer_to_grounded():
    adapter = FakeAdapter(
        [
            AIMessage(content="", tool_calls=[_call("search_lore", {"query": "minas"}, "search")]),
            AIMessage(
                content="",
                tool_calls=[
                    _call(
                        "submit_answer",
                        {
                            "outcome": "answered",
                            "answer": "Minas Tirith is in Gondor.",
                            "evidence_passage_ids": [],
                        },
                        "submit",
                    )
                ],
            ),
        ]
    )

    record = asyncio.run(
        answer_case(
            question="Where is Minas Tirith?",
            index=Index(),
            retrieval_enabled=False,
            adapter=adapter,
            config=_config(),
        )
    )

    assert record.classification == "ungrounded_answer"
    assert record.evidence == ()


def test_budget_exhaustion_uses_one_final_only_turn():
    adapter = FakeAdapter(
        [
            AIMessage(content="", tool_calls=[_call("search_lore", {"query": "minas"}, "search")]),
            AIMessage(
                content="",
                tool_calls=[
                    _call(
                        "submit_answer",
                        {
                            "outcome": "insufficient_evidence",
                            "answer": "The available evidence is insufficient.",
                            "evidence_passage_ids": [],
                        },
                        "submit",
                    )
                ],
            ),
        ]
    )

    record = asyncio.run(
        answer_case(
            question="Where is Minas Tirith?",
            index=Index(),
            retrieval_enabled=True,
            adapter=adapter,
            config=_config(1),
        )
    )

    assert record.classification == "insufficient_evidence"
    assert len(adapter.calls[1][1]) == 1
    assert adapter.calls[1][1][0]["function"]["name"] == "submit_answer"


def test_openrouter_adapter_keeps_secret_out_of_global_environment():
    captured = {}

    class Client:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    OpenRouterModelAdapter(
        model="provider/model",
        api_key="not-a-global-secret",
        config=_config(),
        client_factory=Client,
    )

    assert captured["model"] == "provider/model"
    assert captured["base_url"] == "https://openrouter.ai/api/v1"
    assert captured["api_key"] == "not-a-global-secret"
    assert captured["streaming"] is False
    assert captured["max_retries"] == 0
    assert captured["temperature"] == 0
    assert captured["max_tokens"] == 1024
    assert captured["timeout"] == 1


def test_declared_order_and_tool_message_correlation_are_preserved():
    adapter = FakeAdapter(
        [
            AIMessage(
                content="",
                tool_calls=[
                    _call("search_lore", {"query": "minas"}, "one"),
                    _call("get_lore_context", {"passage_id": "p-1"}, "two"),
                ],
            ),
            _submit(evidence=["p-1"]),
        ]
    )

    record = _run(adapter)

    assert [item.call_id for item in record.tool_trace] == ["one", "two"]
    assert [item.name for item in record.tool_trace] == ["search_lore", "get_lore_context"]
    assert [item.tool_call_id for item in adapter.calls[1][0] if isinstance(item, ToolMessage)] == [
        "one",
        "two",
    ]
    assert record.classification == "grounded"


def test_invalid_first_context_is_counted_and_returns_a_correction_message():
    adapter = FakeAdapter(
        [
            AIMessage(
                content="",
                tool_calls=[_call("get_lore_context", {"passage_id": "p-1"}, "bad")],
            ),
            _submit("insufficient_evidence", "No supporting passage was returned."),
        ]
    )

    record = _run(adapter)

    assert record.classification == "insufficient_evidence"
    assert record.tool_trace[0].valid is False
    assert record.tool_trace[0].budget_before == 4
    assert record.tool_trace[0].budget_after == 3
    assert "Invalid retrieval request" in str(adapter.calls[1][0][-1].content)


@pytest.mark.parametrize(
    "calls",
    [
        [
            _call("search_lore", {"query": "minas"}, "search"),
            _call(
                "submit_answer",
                {"outcome": "answered", "answer": "x", "evidence_passage_ids": []},
                "submit",
            ),
        ],
        [
            _call(
                "submit_answer",
                {"outcome": "answered", "answer": "x", "evidence_passage_ids": []},
                "one",
            ),
            _call(
                "submit_answer",
                {"outcome": "answered", "answer": "x", "evidence_passage_ids": []},
                "two",
            ),
        ],
    ],
)
def test_mixed_or_multiple_final_calls_fail(calls):
    record = _run(FakeAdapter([AIMessage(content="", tool_calls=calls)]))

    assert record.classification == "failed"
    assert record.error is not None
    assert record.error.code == "invalid_final_calls"


def test_excess_retrieval_calls_are_bounded_before_the_final_only_turn():
    adapter = FakeAdapter(
        [
            AIMessage(
                content="",
                tool_calls=[
                    _call("search_lore", {"query": "minas"}, "first"),
                    _call("search_lore", {"query": "minas"}, "excess"),
                ],
            ),
            _submit("insufficient_evidence", "Only one retrieval request was available."),
        ]
    )

    record = _run(adapter, config=_config(1))

    assert [(item.executed, item.message) for item in record.tool_trace] == [
        (True, None),
        (False, "budget exhausted"),
    ]
    assert [tool["function"]["name"] for tool in adapter.calls[1][1]] == ["submit_answer"]


def test_invalid_evidence_and_retrieval_errors_are_sanitized():
    invalid = _run(FakeAdapter([_submit(evidence=["not-returned"])]))
    failed = _run(
        FakeAdapter(
            [AIMessage(content="", tool_calls=[_call("search_lore", {"query": "minas"}, "x")])]
        ),
        index=FailingIndex(),
    )

    assert invalid.error is not None
    assert invalid.error.code == "invalid_submission"
    assert failed.error is not None
    assert failed.error.code == "retrieval_failed"
    assert "top-secret" not in failed.error.message
    assert "provider body" not in failed.error.message


class HttpError(Exception):
    def __init__(self, status_code):
        self.status_code = status_code


def test_transient_retries_but_authorization_errors_do_not(monkeypatch):
    async def no_sleep(_delay):
        return None

    monkeypatch.setattr(lore_agent.asyncio, "sleep", no_sleep)
    recovered = _run(
        FakeAdapter(
            [
                OSError("transport failure"),
                AIMessage(content="", tool_calls=[_call("search_lore", {"query": "minas"}, "s")]),
                _submit(evidence=["p-1"]),
            ]
        )
    )
    forbidden = _run(FakeAdapter([HttpError(401)]))

    assert (recovered.classification, recovered.provider_request_count, recovered.retry_count) == (
        "grounded",
        3,
        1,
    )
    assert forbidden.error is not None
    assert (forbidden.error.code, forbidden.provider_request_count, forbidden.retry_count) == (
        "provider_authorization_failed",
        1,
        0,
    )


def test_overall_timeout_is_terminal_and_never_retains_exception_text():
    class SlowAdapter:
        model = "slow"

        async def invoke(self, messages, tools):
            await asyncio.sleep(0.05)
            raise AssertionError("unreachable")

    config = _config()
    object.__setattr__(config, "provider", ProviderConfig(1, 0.01, 0))
    record = _run(SlowAdapter(), config=config)

    assert record.error is not None
    assert record.error.code == "attempt_timeout"
    assert record.provider_request_count == 1
    assert record.retry_count == 0
    assert "unreachable" not in record.error.message
