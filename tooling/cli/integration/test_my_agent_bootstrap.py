"""The bootstrap of my-agent/ wired to the SDK and the services: harness, MCP server, HTTP client."""

from __future__ import annotations

import asyncio

import pytest
from mcp import Client

from agent_gateway.loader import load_mcp_server
from agent_testkit.servers import free_port, start_uvicorn, wait_for_port

pytestmark = pytest.mark.shell


@pytest.fixture(scope="module")
def mcp_server_url():
    module = load_mcp_server()
    port = free_port()
    server = start_uvicorn(module.application(), port)
    wait_for_port("127.0.0.1", port)
    yield f"http://127.0.0.1:{port}{module.MCP_PATH}"
    server.should_exit = True


def test_mcp_server_starts_and_lists_zero_tools(mcp_server_url):
    async def _check():
        async with Client(mcp_server_url) as client:
            assert client.server_info is not None
            assert client.server_info.name == "workshop-tools"
            result = await client.list_tools()
            assert result.tools == []

    asyncio.run(_check())


def test_harness_model_client_reads_the_proxy_url_at_call_time(monkeypatch):
    from agent_gateway.loader import load_my_agent_module

    harness = load_my_agent_module("harness.py", "my_agent_harness_test")
    monkeypatch.setenv("PROXY_URL", "http://127.0.0.1:9/")
    assert harness.model_client().base_url == "http://127.0.0.1:9"


def test_http_client_carries_the_token_and_raises_readable_errors(services, reset_state):
    from business_api.auth import issue_token

    from agent_sdk import http_client as http
    token = issue_token("camille-renard", "customer_service", "organization-a")
    order = http.business_api(token).get("/orders/CMD-1042")
    assert "CMD-1042" in str(order)
    with pytest.raises(http.ServiceError) as denied:
        http.business_api(None).get("/orders/CMD-1042")
    assert denied.value.status_code == 401 and denied.value.detail
    with pytest.raises(http.ServiceError) as missing:
        http.business_api(token).get("/orders/CMD-0000")
    assert missing.value.status_code == 404


def test_mcp_client_lists_and_calls_the_server_tools(monkeypatch):
    from agent_gateway.loader import load_mcp_server
    from agent_testkit.servers import free_port, start_uvicorn, wait_for_port

    from agent_sdk import mcp_client as mcp
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


def test_bootstrap_converses_through_the_model_without_tool(chat_client, traces):
    first = chat_client.turn("Bonjour, je m'appelle Camille.")
    turn = chat_client.turn("Quel est le statut de la commande CMD-1042 de Martin Durand ?")
    assert turn.ok is True and first.ok is True
    assert turn.types[-1] == "end" and "text" in turn.types
    _, trace = traces.all()
    assert trace["tools"] == [] and trace["input"]["message"].startswith("Quel est le statut")
    prompt = trace["input"]["system_prompt"]
    assert prompt and "<!--" not in prompt, "system_prompt.md is loaded without its HTML comments"
    assert trace["input"]["history"] == [
        {"role": "user", "content": "Bonjour, je m'appelle Camille."},
        {"role": "assistant", "content": first.text},
    ], "the history is sent to the model"
    assert len(trace["model"]["calls"]) == 1 and trace["output"] == turn.text, "one model call, its answer relayed"

def test_bootstrap_continues_a_loaded_conversation_and_refuses_unoffered_tools(services, chat_client, traces):
    import httpx

    from agent_sdk.context import context
    from agent_testkit.conversation import to_messages

    written = [{
        "user": "Où en est la commande CMD-2010 ?",
        "tools": [{"name": "get_order", "arguments": {"reference": "CMD-2010"}, "result": {"status": "ok", "order": {"status": "shipped"}}}],
        "answer": "La commande CMD-2010 est expédiée.",
    }]
    chat_client.load(written)
    # The model tries to call the neutral tool of the written history, then answers once refused.
    call = {"id": "call_x", "type": "function", "function": {"name": "get_order", "arguments": "{\"reference\": \"CMD-2010\"}"}}
    token = httpx.post(f"{services['proxy']}/_test/token", timeout=5).json()["token"]
    httpx.post(
        f"{services['proxy']}/_test/scripts",
        headers={"Authorization": f"Bearer {token}"},
        json={"scripts": [
            {"if_last_role": "tool", "content": "Elle est expédiée, d'après la lecture précédente."},
            {"if_contains": "rappeler", "content": "", "tool": call},
        ]},
        timeout=5,
    )
    turn = chat_client.turn("Vous pouvez me rappeler son statut ?")
    assert turn.ok and "expédiée" in turn.text
    trace = traces.last()
    assert trace["tools"] == [] and len(trace["model"]["calls"]) == 2, "the unoffered call is refused, never run"
    assert trace["input"]["history"] == to_messages(written), "the loaded conversation is replayed as it was written"
    roles = [m["role"] for m in context(chat_client.conversation_id).messages]
    assert roles[-4:] == ["user", "assistant", "tool", "assistant"], "the refused call and its refusal stay in the context"
