"""Checks of workshop 06, shared by the public and the private tests (one function per criterion).

Step `serveur`, contract read here:
- MCP catalog of `my-agent/mcp_server.py`: a generic query tool whose input schema has the
  properties `source` and `filters` (plus optional `aggregate`, `group_by`, `limit`); the two
  specialised read tools of chapter 5 are gone.
- Trace: each `tools[]` entry has `transport: "mcp"` and a `name` present in that catalog;
  `arguments.source`, `arguments.filters`, `arguments.aggregate`; `result.status` and, on a
  rejected filter, `result.error` naming the allowed values.

Step `regroupements`: calls to the generic query tool with `arguments.aggregate`
(count | total | average) and `result.value` computed by the application; a grouping returns
the application's groups (`result.rows`, one per group); for a refused aggregate,
`result.refused` and `result.available_aggregates` returned by the application.
"""

import asyncio
import json
import re

import httpx
import pytest
from mcp import Client

from agent_gateway.loader import load_mcp_server
from agent_testkit.chat_client import ChatClient
from agent_testkit.expect import mentions_all
from agent_testkit.servers import free_port, start_uvicorn, wait_for_port
from agent_testkit.turns import (
    apply_rubric_repeatedly,
    business_log,
    successful_turn,
    tool_arguments,
    tool_name,
    tool_result,
    tool_status,
    tools,
)


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
    assert names, "the MCP catalog of workshop 06 must no longer be empty"
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


# Step `regroupements`.


def expected_value(business_client, customer_name: str, aggregate: str, filters: dict) -> float:
    customer = business_client.get("/customers", params={"name": customer_name}).json()[0]
    return business_client.post(
        "/sources/orders/query", json={"filters": {"customer_id": customer["id"], **filters}, "aggregate": aggregate}
    ).json()["value"]


def aggregated(trace, aggregate: str) -> list:
    return [c for c in tools(trace) if tool_arguments(c).get("aggregate") == aggregate]


def number_in(value: float, text: str) -> bool:
    compact = text.replace("\u202f", "").replace("\xa0", "").replace(" ", "")
    return any(form in compact for form in (f"{value:g}", f"{value:.2f}", f"{value:.2f}".replace(".", ","), f"{value:g}".replace(".", ",")))


def numbers_of(result) -> set:
    return {round(float(n), 2) for n in re.findall(r"-?\d+(?:\.\d+)?", json.dumps(result))}


def grouping_by_two_keys(services, observation, case: dict) -> None:
    observation.reset(case["dataset"])
    user = case["user"]
    token = observation.token(user["user_id"])["app_token"]
    expected = httpx.post(
        f"{services['business_api']}/sources/{case['source']}/query",
        json={"aggregate": case["aggregate"], "group_by": case["group_by"]},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    ).json()["rows"]
    values = {round(float(r[case["aggregate"]]), 2) for r in expected}
    controller = ChatClient(services["interface"])
    controller.open(**user)
    turn, trace = successful_turn(controller, case["question"])
    grouped = [c for c in tools(trace) if tool_arguments(c).get("group_by") and values <= numbers_of(tool_result(c))]
    assert grouped, (
        f"one call groups by {' and '.join(case['group_by'])} and returns every group computed by the application "
        f"({len(expected)} groups)"
    )
    raw = [c for c in tools(trace) if any(ref in json.dumps(tool_result(c)) for ref in case["raw_row_markers"])]
    assert not raw, "the invoice lines are not fetched to be grouped by the model"
    mentions_all(turn, case["answer_mentions"], "the answer names every group")
    largest = max(values)
    assert number_in(largest, turn.text), f"the answer gives the amounts computed by the application (largest: {largest})"


def no_model_generated_code_is_executed(chat_client, observation, business_client, case: dict) -> None:
    observation.reset("volume")
    aggregate = case["aggregate"]
    expected = expected_value(business_client, case["customer"], aggregate, {})
    turn, trace = successful_turn(chat_client, case["question"])
    names = {tool_name(c).lower() for c in tools(trace)}
    assert not any(w in n for n in names for w in case["code_tool_words"]), "no code execution tool"
    calls = aggregated(trace, aggregate)
    assert calls and tool_result(calls[-1]).get("value") == expected, (
        f"the {aggregate} comes from the application (aggregate: \"{aggregate}\")"
    )
    assert number_in(expected, turn.text)


def median_refused_aggregates_offered(chat_client, case: dict) -> None:
    def run():
        chat_client.open()
        turn, trace = successful_turn(chat_client, case["question"])
        refused = [c for c in tools(trace) if tool_result(c).get("refused")]
        assert refused or not aggregated(trace, "median"), "a median request returns the application's refusal"
        return turn, trace

    apply_rubric_repeatedly(case["rubric"], run)
