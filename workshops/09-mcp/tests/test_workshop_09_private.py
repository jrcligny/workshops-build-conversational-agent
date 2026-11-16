"""Private tests of workshop 09 (not given to students): same criteria, other inputs.

Another question served by MCP, another malformed filter value, another aggregate for the
accountant (average, expected value read from the business API). The catalog test has no input
to vary and has no private variant.
"""

import asyncio

import httpx
import pytest
from mcp import Client

from workshop_kit.shell.loader import load_mcp_server
from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.servers import free_port, start_uvicorn, wait_for_port
from workshop_tests.testing.turns import business_log, successful_turn, tool_arguments, tool_name, tool_result, tool_status, tools

pytestmark = pytest.mark.workshop


@pytest.fixture(scope="module")
def mcp_server_url():
    module = load_mcp_server()
    port = free_port()
    server = start_uvicorn(module.application(), port)
    wait_for_port("127.0.0.1", port)
    url = f"http://127.0.0.1:{port}{module.MCP_PATH}"
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


def test_tools_served_by_mcp(chat_client, observation, mcp_server_url):
    catalog = {t.name for t in _catalog(mcp_server_url)}
    turn, trace = successful_turn(chat_client, "Quelles commandes la cliente Léa Martin de Lille a-t-elle passées ?")
    calls = tools(trace)
    assert calls, "the question needs a tool call"
    assert all(c.get("transport") == "mcp" for c in calls), "each tools[] entry records transport: \"mcp\""
    assert {tool_name(c) for c in calls} <= catalog, "the harness calls the tools of the MCP catalog, by name"
    assert any(e.get("route", "").startswith("/sources/") for e in business_log(observation))
    assert "CMD-2010" in turn.text


def test_malformed_filter_actionable_error(chat_client):
    turn, trace = successful_turn(chat_client, "Je veux les commandes au statut SHIPED, exactement cette valeur.")
    rejected = [c for c in tools(trace) if tool_status(c) == "error"]
    assert rejected, "a filter value outside the coded values is rejected with result.status \"error\""
    error = str(tool_result(rejected[0]).get("error") or tool_result(rejected[0])).lower()
    assert "delivered" in error and "in_preparation" in error, "result.error lists the allowed values (read from /sources/orders)"
    retried = [c for c in tools(trace) if tool_status(c) == "ok"]
    assert retried or "?" in turn.text, "the agent corrects its filter or asks the user which status they mean"


def test_accountant_average_through_the_generic_query(services, observation):
    token = observation.token("nina-accountant")["app_token"]
    expected = httpx.post(
        f"{services['business_api']}/sources/invoices/query",
        json={"filters": {"status": "pending"}, "aggregate": "average"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    ).json()["value"]
    accountant = ChatClient(services["interface"])
    accountant.open(user_id="nina-accountant", role="accountant", organization="organization-a")
    turn, trace = successful_turn(accountant, "En moyenne, combien vaut une facture en attente d'approbation ?")
    queries = [c for c in tools(trace) if tool_arguments(c).get("source") == "invoices"]
    assert queries, "the generic query is called with source \"invoices\""
    assert tool_arguments(queries[-1]).get("aggregate") == "average", "the average is computed by the application"
    assert tool_result(queries[-1]).get("value") == expected
    text = turn.text.replace(" ", "").replace("\u202f", "").replace("\xa0", "")
    assert f"{expected:g}".replace(".", ",") in text or f"{expected:g}" in text, f"the answer gives the average ({expected})"
