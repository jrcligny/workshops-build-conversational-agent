"""End-to-end tests of workshop 09. They must fail on the empty shell."""

import asyncio

import pytest
from mcp import Client

from workshop_kit.shell.loader import load_mcp_server
from workshop_kit.testing.chat_client import ChatClient
from workshop_kit.testing.servers import free_port, start_uvicorn, wait_for_port
from workshop_kit.testing.turns import business_log, flat, successful_turn, tools

pytestmark = pytest.mark.workshop

# The two specialised read tools of chapter 5, replaced by the generic query tool.
REPLACED_TOOLS = {"search_customer", "search_customers", "list_orders", "list_customer_orders"}


@pytest.fixture(scope="module")
def mcp_server_url():
    module = load_mcp_server()
    port = free_port()
    server = start_uvicorn(module.application(), port)
    wait_for_port("127.0.0.1", port)
    yield f"http://127.0.0.1:{port}{module.MCP_PATH}"
    server.should_exit = True


def _catalog(url: str) -> list:
    async def _list():
        async with Client(url) as client:
            result = await client.list_tools()
            return list(result.tools)

    return asyncio.run(_list())


def test_tools_served_by_mcp(chat_client, observation):
    turn, trace = successful_turn(chat_client, "What is the total of the orders of Martin Durand?")
    assert "mcp" in flat(trace).lower() or trace.get("transport") == "mcp"
    log = business_log(observation)
    assert log, "the application must be called, through the MCP server, not from a silent local tool"
    # no more direct HTTP call from the harness: the caller must be the tool server
    assert any("mcp" in str(e).lower() or e.get("origin") == "mcp" or e.get("via") == "mcp" for e in log) or "mcp" in flat(trace).lower()


def test_two_clients_get_the_same_catalog(mcp_server_url):
    a = _catalog(mcp_server_url)
    b = _catalog(mcp_server_url)
    names = [getattr(t, "name", None) or str(t) for t in a]
    assert names, "the MCP catalog of workshop 09 must no longer be empty"
    assert [getattr(t, "name", None) or str(t) for t in b] == names
    assert not (REPLACED_TOOLS & set(names)), "the two specialised tools of chapter 5 must be gone"


def test_malformed_filter_actionable_error(chat_client):
    turn, trace = successful_turn(chat_client, "Query the orders with the filter status==DELIV (this is not a valid status).")
    text = (turn.text + flat(tools(trace))).lower()
    assert "error" in text or "invalid" in text or "fix" in text or "status" in text
    assert "deliver" in text or "label" in text or "values" in text


def test_accountant_question_through_the_generic_query(chat_client, observation):
    accountant = ChatClient(chat_client.base_url)
    accountant.open(user_id="nina-accountant", role="accountant", organization="organization-a")
    turn, trace = successful_turn(accountant, "What is the total of the pending invoices?")
    assert tools(trace)
    flat_tools = flat(tools(trace)).lower()
    assert "query" in flat_tools or "generic" in flat_tools or "aggregat" in flat_tools or "total" in flat_tools
