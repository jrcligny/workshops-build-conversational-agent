"""The agent SDK (agent_sdk): repetitive code of the student's agent, never a workshop's goal."""

import pytest


def test_http_client_reports_an_unreachable_service(monkeypatch):
    from agent_sdk import http_client as http
    monkeypatch.setenv("BUSINESS_API_URL", "http://127.0.0.1:9")
    with pytest.raises(http.ServiceError) as unreachable:
        http.business_api("t", timeout=2).get("/orders/CMD-1042")
    assert unreachable.value.status_code is None


def test_events_carry_the_field_names_the_tests_read():
    from agent_sdk import events
    assert (events.step("get_order").type, events.step("get_order").data) == ("step", {"tool": "get_order"})
    assert events.mention("Réponse partielle").data["content"] == "Réponse partielle"
    assert events.confirmation_requested("D-1", summary="achat").data == {"draft_id": "D-1", "summary": "achat"}
    assert events.memory("written", "amount_display", "including_tax").data == {
        "action": "written", "topic": "amount_display", "value": "including_tax"
    }
    assert events.sources([{"title": "Retours"}]).data == {"sources": [{"title": "Retours"}]}
    assert events.end("ok").data == {"ok": True, "text": "ok"}


def test_tool_schema_declares_an_annotated_function():
    from typing import Literal

    from agent_sdk.tool_schema import declare

    def list_orders(customer_id: str, filter: Literal["late", "all"] = "all", limit: int | None = None,
                    tags: list[str] | None = None) -> dict:
        """Lists the orders of a customer.

        More details for humans.

        Args:
            customer_id: customer identifier,
                as returned by the customer search.
            filter: which orders to keep.
        """

    function = declare(list_orders)["function"]
    assert function["name"] == "list_orders" and function["description"] == "Lists the orders of a customer."
    props = function["parameters"]["properties"]
    assert props["customer_id"] == {
        "type": "string", "description": "customer identifier, as returned by the customer search."
    }
    assert props["filter"]["enum"] == ["late", "all"] and props["limit"] == {"type": "integer"}
    assert props["tags"] == {"type": "array", "items": {"type": "string"}}
    assert function["parameters"]["required"] == ["customer_id"]


def test_tracer_records_model_calls_in_the_format_the_tests_read():
    from agent_sdk.contract import Message, TestUser
    from agent_sdk.trace import Tracer

    class FakeModel:
        def generate(self, messages, tools=None, model="default"):
            return {"model": "m1", "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12}}

    tracer = Tracer("c1", TestUser("paul-buyer", "buyer", "organization-a"), "suite")
    tracer.input(system_prompt="prompt", history=[Message("user", "bonjour")])
    assert tracer.cycle() == 1
    tracer.call_model(FakeModel(), [], tools=[{"type": "function", "function": {"name": "get_order"}}], context_size=40)
    tracer.cycle()
    tracer.call_model(FakeModel(), [], tools=[], context_size=55)
    tracer.tool_call("get_order", {"reference": "CMD-1"}, {"status": "found"}, duration_ms=3)
    tracer.output("réponse")
    trace = tracer.to_dict()
    assert trace["input"] == {"system_prompt": "prompt", "history": [{"role": "user", "content": "bonjour"}], "message": "suite"}
    assert trace["user"] == {"id": "paul-buyer", "role": "buyer", "organization": "organization-a"}
    model = trace["model"]
    assert [c["context_size"] for c in model["calls"]] == [40, 55] and [c["cycle"] for c in model["calls"]] == [1, 2]
    assert model["usage"]["total_tokens"] == 24 and model["calls"][0]["model"] == "m1" and "duration_ms" in model
    assert trace["offered_tools"] == [["get_order"], []] and trace["cycles"] == 2
    assert trace["tools"] == [{"name": "get_order", "arguments": {"reference": "CMD-1"}, "result": {"status": "found"},
                               "cycle": 2, "duration_ms": 3}]
    assert trace["output"] == "réponse" and "compaction" not in trace and "memory" not in trace


def test_tracer_returns_the_interface_events_it_traces(session_dir):
    from agent_sdk import trace_store as writer
    from agent_sdk.contract import TestUser

    from agent_sdk import trace as trace_mod
    user = TestUser("nina-accountant", "accountant", "organization-a")
    tracer = trace_mod.Tracer("c2", user, "bonjour")
    event = tracer.compaction(summarized_answers=3, kept_user_messages=4, threshold=8, summary="résumé")
    assert (event.type, event.data["summary"]) == ("compaction", "résumé") and tracer.to_dict()["compaction"]["threshold"] == 8
    entry = trace_mod.memory_entry("langue", "français", user)
    assert {"topic", "value", "origin", "recorded_at", "user", "organization"} <= set(entry)
    (memory_event,) = tracer.memory(loaded=[], written=[entry])
    assert (memory_event.type, memory_event.data["action"]) == ("memory", "written")
    assert tracer.to_dict()["memory"] == {"loaded": [], "written": [entry], "deleted": []}
    assert tracer.mention("Résultat partiel.").type == "mention"
    tracer.state({"current_customer": {"id": "C1"}})
    writer.clear()
    tracer.write()
    (written,) = writer.read_all()
    assert written["state"] == {"current_customer": {"id": "C1"}} and "timestamp" in written


def test_model_client_normalizes_outages():
    """Outages surface as ModelUnavailable, whatever the HTTP library; request errors do not."""
    from agent_sdk.model_client import ModelClient, ModelUnavailable, model_unavailable

    class _Response:
        def __init__(self, code):
            self.status_code = code

    class _StatusError(Exception):
        def __init__(self, code):
            self.response = _Response(code)

    class TransportError(Exception):  # same name as httpx/httpx2's base transport error
        pass

    assert model_unavailable(_StatusError(503)).reason == "HTTP 503"
    assert model_unavailable(_StatusError(429)).reason == "HTTP 429"
    assert model_unavailable(_StatusError(400)) is None
    assert model_unavailable(TransportError("down")).reason == "TransportError"
    assert model_unavailable(ValueError("bug")) is None
    with pytest.raises(ModelUnavailable):
        ModelClient("http://127.0.0.1:9", timeout=0.5).generate([{"role": "user", "content": "x"}])
