"""Checks of workshop 09, shared by the public and the private tests (one function per criterion).

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
from testkit.chat_client import ChatClient
from testkit.expect import mentions_all
from testkit.servers import free_port, start_uvicorn, wait_for_port
from testkit.turns import business_log, successful_turn, tool_arguments, tool_name, tool_result, tool_status, tools


def serve_mcp_server():
    """Body of the `mcp_server_url` fixture: serves `my-agent/mcp_server.py`, yields its URL."""
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


def catalog(url: str) -> list:
    async def _list():
        async with Client(url) as client:
            result = await client.list_tools()
            return list(result.tools)

    return asyncio.run(_list())


def schema_properties(tool) -> set:
    schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None) or {}
    return set((schema or {}).get("properties", {}))


def two_clients_get_the_same_catalog(mcp_server_url, case: dict) -> None:
    a, b = catalog(mcp_server_url), catalog(mcp_server_url)
    names = [t.name for t in a]
    assert names, "the MCP catalog of workshop 09 must no longer be empty"
    assert [t.name for t in b] == names, "two clients get the same catalog"
    assert not (set(case["replaced_tools"]) & set(names)), "the two specialised tools of chapter 5 must be gone"
    assert any(set(case["generic_properties"]) <= schema_properties(t) for t in a), (
        "a generic query tool takes `source` and `filters`"
    )


def tools_served_by_mcp(chat_client, observation, mcp_server_url, case: dict) -> None:
    served = {t.name for t in catalog(mcp_server_url)}
    turn, trace = successful_turn(chat_client, case["question"])
    calls = tools(trace)
    assert calls, "the question needs a tool call"
    assert all(c.get("transport") == "mcp" for c in calls), "each tools[] entry records transport: \"mcp\""
    assert {tool_name(c) for c in calls} <= served, "the harness calls the tools of the MCP catalog, by name"
    assert any(e.get("route", "").startswith("/sources/") for e in business_log(observation)), (
        "the application is called through its generic query route"
    )
    mentions_all(turn, case.get("answer_contains", []), "the answer gives what the tools read", strict=True)


def malformed_filter_actionable_error(chat_client, case: dict) -> None:
    turn, trace = successful_turn(chat_client, case["question"])
    rejected = [c for c in tools(trace) if tool_status(c) == "error"]
    assert rejected, "a filter value outside the coded values is rejected with result.status \"error\""
    error = str(tool_result(rejected[0]).get("error") or tool_result(rejected[0])).lower()
    assert all(v in error for v in case["allowed_values"]), "result.error lists the allowed values (read from /sources/orders)"
    retried = [c for c in tools(trace) if tool_status(c) == "ok"]
    assert retried or "?" in turn.text, "the agent corrects its filter or asks the user which status they mean"


def accountant_aggregate_through_the_generic_query(services, observation, case: dict) -> None:
    user = case["user"]
    token = observation.token(user["user_id"])["app_token"]
    expected = httpx.post(
        f"{services['business_api']}/sources/{case['source']}/query",
        json={"filters": case["filters"], "aggregate": case["aggregate"]},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    ).json()["value"]
    accountant = ChatClient(services["interface"])
    accountant.open(**user)
    turn, trace = successful_turn(accountant, case["question"])
    queries = [c for c in tools(trace) if tool_arguments(c).get("source") == case["source"]]
    assert queries, f"the generic query is called with source \"{case['source']}\""
    assert tool_arguments(queries[-1]).get("aggregate") == case["aggregate"], case["aggregate_message"]
    assert tool_result(queries[-1]).get("value") == expected
    text = turn.text
    for space in case["ignored_spaces"]:
        text = text.replace(space, "")
    dot_form_text = turn.text if case["dot_form_in_raw_text"] else text
    assert f"{expected:g}".replace(".", ",") in text or f"{expected:g}" in dot_form_text, (
        f"the answer gives the {case['aggregate']} ({expected})"
    )
