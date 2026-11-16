"""End-to-end tests of workshop 09. They must fail on the empty shell.

Contract read here:
- MCP catalog of `my-agent/mcp_server.py`: a generic query tool whose input schema has the
  properties `source` and `filters` (plus optional `aggregate`, `group_by`, `limit`); the two
  specialised read tools of chapter 5 are gone.
- Trace: each `tools[]` entry has `transport: "mcp"` and a `name` present in that catalog;
  `arguments.source`, `arguments.filters`, `arguments.aggregate`; `result.status` and, on a
  rejected filter, `result.error` naming the allowed values.
"""

import asyncio

import httpx
import pytest
from mcp import Client

from agent_gateway.loader import load_mcp_server
from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.servers import free_port, start_uvicorn, wait_for_port
from workshop_tests.testing.turns import business_log, successful_turn, tool_arguments, tool_name, tool_result, tool_status, tools

pytestmark = pytest.mark.workshop

REPLACED_TOOLS = {"search_customer", "search_customers", "list_orders", "list_customer_orders"}


@pytest.fixture(scope="module")
def mcp_server_url():
    module = load_mcp_server()
    port = free_port()
    server = start_uvicorn(module.application(), port)
    wait_for_port("127.0.0.1", port)
    url = f"http://127.0.0.1:{port}{module.MCP_PATH}"
    # Same variable as `workshop serve`: the harness reaches this server through MCP_URL.
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("MCP_URL", url)
        yield url
    server.should_exit = True


def _catalog(url: str) -> list:
    async def _list():
        async with Client(url) as client:
            result = await client.list_tools()
            return list(result.tools)

    return asyncio.run(_list())


def _schema_properties(tool) -> set:
    schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None) or {}
    return set((schema or {}).get("properties", {}))


def test_two_clients_get_the_same_catalog(mcp_server_url):
    a, b = _catalog(mcp_server_url), _catalog(mcp_server_url)
    names = [t.name for t in a]
    assert names, "the MCP catalog of workshop 09 must no longer be empty"
    assert [t.name for t in b] == names, "two clients get the same catalog"
    assert not (REPLACED_TOOLS & set(names)), "the two specialised tools of chapter 5 must be gone"
    assert any({"source", "filters"} <= _schema_properties(t) for t in a), (
        "a generic query tool takes `source` and `filters`"
    )


def test_tools_served_by_mcp(chat_client, observation, mcp_server_url):
    catalog = {t.name for t in _catalog(mcp_server_url)}
    _, trace = successful_turn(chat_client, "Combien de commandes a Martin Durand ?")
    calls = tools(trace)
    assert calls, "the question needs a tool call"
    assert all(c.get("transport") == "mcp" for c in calls), "each tools[] entry records transport: \"mcp\""
    assert {tool_name(c) for c in calls} <= catalog, "the harness calls the tools of the MCP catalog, by name"
    assert any(e.get("route", "").startswith("/sources/") for e in business_log(observation)), (
        "the application is called through its generic query route"
    )


def test_malformed_filter_actionable_error(chat_client):
    turn, trace = successful_turn(chat_client, "Listez les commandes dont le statut vaut DELIV.")
    rejected = [c for c in tools(trace) if tool_status(c) == "error"]
    assert rejected, "a filter value outside the coded values is rejected with result.status \"error\""
    error = str(tool_result(rejected[0]).get("error") or tool_result(rejected[0])).lower()
    assert "delivered" in error and "shipped" in error, "result.error lists the allowed values (read from /sources/orders)"
    retried = [c for c in tools(trace) if tool_status(c) == "ok"]
    assert retried or "?" in turn.text, "the agent corrects its filter or asks the user which status they mean"


def test_accountant_question_through_the_generic_query(services, observation):
    token = observation.token("nina-accountant")["app_token"]
    expected = httpx.post(
        f"{services['business_api']}/sources/invoices/query",
        json={"filters": {"status": "pending"}, "aggregate": "total"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    ).json()["value"]
    accountant = ChatClient(services["interface"])
    accountant.open(user_id="nina-accountant", role="accountant", organization="organization-a")
    turn, trace = successful_turn(accountant, "Quel est le montant total des factures en attente d'approbation ?")
    queries = [c for c in tools(trace) if tool_arguments(c).get("source") == "invoices"]
    assert queries, "the generic query is called with source \"invoices\""
    assert tool_arguments(queries[-1]).get("aggregate") == "total", "the total is computed by the application (aggregate: total)"
    assert tool_result(queries[-1]).get("value") == expected
    assert f"{expected:g}".replace(".", ",") in turn.text.replace(" ", "").replace("\u202f", "") or f"{expected:g}" in turn.text
