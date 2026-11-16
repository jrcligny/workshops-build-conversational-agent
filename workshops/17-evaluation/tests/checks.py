"""Checks of workshop 17, shared by the public and the private tests (one function per criterion).

Contract read here:
- traces: no secret (Authorization header, bearer token, API key) appears in a trace;
- trace `model.usage` and `model.duration_ms` (whole turn), `model.calls[]` (one entry per model call) and
  `tools[]` (one entry per tool call, with `duration_ms`): a turn is observable end to end.
The route tests (official and student routes, route report) have no private variant: they stay
in `test_workshop_17.py`.
"""

from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.turns import flat, successful_turn, tools


def client(services, user: dict) -> ChatClient:
    chat = ChatClient(services["interface"])
    chat.open(user_id=user["user_id"], role=user["role"], organization=user["organization"])
    return chat


def masked_and_observable_traces(chat_client, traces, case: dict) -> None:
    successful_turn(chat_client, case["question"])
    trace = traces.last()
    flat_t = flat(trace).lower()
    assert "authorization" not in flat_t and "bearer " not in flat_t
    assert "azure_openai_api_key" not in flat_t and "eyj" not in flat_t, "no secret or token in the trace"
    model = trace.get("model") or {}
    assert model.get("usage") and "duration_ms" in model and model.get("calls"), "trace.model records usage, duration_ms and calls"
    if case.get("min_model_calls"):
        assert len(model.get("calls") or []) >= case["min_model_calls"], "a chained turn records one entry per model call"
    assert len(tools(trace)) >= case["min_tool_calls"] and all("duration_ms" in c for c in tools(trace)), (
        "each tool call records duration_ms"
    )
