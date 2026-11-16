"""Helpers of the my-agent bootstrap (my-agent/agent_helpers/): repetitive code, never a workshop's goal."""

import importlib
import sys

import pytest

from workshop_kit.shell.config import repo_path, settings


@pytest.fixture(scope="module")
def helpers():
    folder = str(repo_path(settings.my_agent_dir))
    added = folder not in sys.path
    if added:
        sys.path.append(folder)
    yield lambda name: importlib.import_module(f"agent_helpers.{name}")
    if added:
        sys.path.remove(folder)


def test_kit_model_client_reads_the_proxy_url_at_call_time(helpers, monkeypatch):
    kit = helpers("kit")
    monkeypatch.setenv("PROXY_URL", "http://127.0.0.1:9/")
    assert kit.model_client().base_url == "http://127.0.0.1:9"
    assert kit.is_egress_allowed("http://example.com/") is None, "the shipped policy is inactive"

def test_http_client_carries_the_token_and_raises_readable_errors(helpers, services, reset_state):
    from workshop_kit.apps.business_api.auth import issue_token

    http = helpers("http_client")
    token = issue_token("camille-renard", "customer_service", "organization-a")
    order = http.business_api(token).get("/orders/CMD-1042")
    assert "CMD-1042" in str(order)
    with pytest.raises(http.ServiceError) as denied:
        http.business_api(None).get("/orders/CMD-1042")
    assert denied.value.status_code == 401 and denied.value.detail
    with pytest.raises(http.ServiceError) as missing:
        http.business_api(token).get("/orders/CMD-0000")
    assert missing.value.status_code == 404


def test_http_client_reports_an_unreachable_service(helpers, monkeypatch):
    http = helpers("http_client")
    monkeypatch.setenv("BUSINESS_API_URL", "http://127.0.0.1:9")
    with pytest.raises(http.ServiceError) as unreachable:
        http.business_api("t", timeout=2).get("/orders/CMD-1042")
    assert unreachable.value.status_code is None


def test_mcp_client_lists_and_calls_the_server_tools(helpers, monkeypatch):
    from workshop_kit.shell.loader import load_mcp_server
    from workshop_tests.testing.servers import free_port, start_uvicorn, wait_for_port

    mcp = helpers("mcp_client")
    module = load_mcp_server()
    server = module.create_server()

    @server.tool()
    def echo(text: str) -> str:
        """Repeats the text."""
        return text

    port = free_port()
    app = server.streamable_http_app(
        stateless_http=True, json_response=True, streamable_http_path=module.MCP_PATH, host="127.0.0.1"
    )
    running = start_uvicorn(app, port)
    try:
        wait_for_port("127.0.0.1", port)
        monkeypatch.setenv("MCP_URL", f"http://127.0.0.1:{port}{module.MCP_PATH}")
        (tool,) = mcp.list_tools()
        assert tool["name"] == "echo" and "text" in tool["input_schema"]["properties"]
        assert mcp.as_openai_tool(tool)["function"]["parameters"] == tool["input_schema"]
        result = mcp.call_tool("echo", {"text": "bonjour"})
        assert result["is_error"] is False and result["text"] == "bonjour"
    finally:
        running.should_exit = True


def test_events_carry_the_field_names_the_tests_read(helpers):
    events = helpers("events")
    assert (events.step("get_order").type, events.step("get_order").data) == ("step", {"tool": "get_order"})
    assert events.mention("Réponse partielle").data["content"] == "Réponse partielle"
    assert events.confirmation_requested("D-1", summary="achat").data == {"draft_id": "D-1", "summary": "achat"}
    assert events.memory("written", "amount_display", "including_tax").data == {
        "action": "written", "topic": "amount_display", "value": "including_tax"
    }
    assert events.sources([{"title": "Retours"}]).data == {"sources": [{"title": "Retours"}]}
    assert events.end("ok").data == {"ok": True, "text": "ok"}


def test_tool_schema_declares_an_annotated_function(helpers):
    from typing import Literal

    declare = helpers("tool_schema").declare

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


def test_base_trace_has_only_the_base_fields(helpers):
    from workshop_kit.shell.harness_contract import Message, TestUser

    trace = helpers("trace").base_trace(
        "c1", TestUser("paul-buyer", "buyer", "organization-a"), "prompt", [Message("user", "bonjour")], "suite"
    )
    assert set(trace) == {"turn_id", "conversation_id", "user", "input", "tools", "output"}
    assert trace["input"] == {
        "system_prompt": "prompt", "history": [{"role": "user", "content": "bonjour"}], "message": "suite"
    }
    assert trace["user"] == {"id": "paul-buyer", "role": "buyer", "organization": "organization-a"}
