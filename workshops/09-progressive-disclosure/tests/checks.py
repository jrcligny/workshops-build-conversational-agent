"""Checks of workshop 09, shared by the public and the private tests (one function per criterion).

The workshop bounds the generic query tool of workshop 06 (`source`, `filters`, …). Contract read here
(`tools[]` of that tool, dataset `volume`):
- a summarized, bounded list: a call with `arguments.source == "orders"` whose `result.rows` holds at
  most 20 rows, each without detail fields such as `amount`, `delivery_city`, `customer_id`; next to it
  `result.returned` (rows in this portion), `result.total`, `result.total_status` (`"exact"`, or
  `"minimum"` when the application's retrieval cap is reached) and `result.truncated`;
- the next portion through a position (free name and form, e.g. `arguments.offset`): rows not already received;
- count: `arguments.aggregate == "count"` and `result.value`, without rows;
- a grouping (`arguments.group_by`) is bounded and declared the same way (private test);
- the detail of one order through the consultation tool (business API `GET /orders/<reference>` read during
  the turn), after a loaded conversation in which the list was already shown (`case["conversation"]`, only
  the detail question is played);
- `model.calls[].context_size` for every cycle.

An expected total given by a case is checked as is; a case without one reads it from the business API.
"""

from agent_testkit.conversation import tool_results
from agent_testkit.expect import mentions, mentions_any
from agent_testkit.turns import (
    apply_rubric,
    business_log,
    successful_turn,
    tool_arguments,
    tool_result,
    tools,
)

DISPLAY_LIMIT = 20
DETAIL_KEYS = ("amount", "delivery_city", "delivery_date", "customer_id", "organization_id", "deleted")


def is_listing(result) -> bool:
    rows = result.get("rows") if isinstance(result, dict) else None
    return isinstance(rows, list) and all(isinstance(r, dict) and "group" not in r for r in rows)


def listings(trace) -> list[dict]:
    """Results of the generic query on the orders, as rows (neither a count nor a grouping)."""
    return [
        tool_result(c)
        for c in tools(trace)
        if tool_arguments(c).get("source") == "orders" and not tool_arguments(c).get("group_by") and is_listing(tool_result(c))
    ]


def references(listing: dict) -> list[str]:
    return [str(row.get("reference")) for row in listing["rows"] if isinstance(row, dict)]


def morel_query(business_client, **body) -> dict:
    customer = business_client.get("/customers", params={"name": "Transports Morel"}).json()[0]
    filters = {"customer_id": customer["id"], **body.pop("filters", {})}
    return business_client.post("/sources/orders/query", json={"filters": filters, **body}).json()


def late_total(business_client) -> int:
    return morel_query(business_client, filters={"late": True}, aggregate="count")["value"]


def expected_late_total(case: dict, business_client) -> int:
    return case["total"] if case.get("total") is not None else late_total(business_client)


def bounded_and_declared(result: dict, total: int) -> None:
    rows = result["rows"]
    assert 0 < len(rows) <= DISPLAY_LIMIT, f"at most {DISPLAY_LIMIT} rows are shown to the model"
    assert result.get("returned") == len(rows), "result.returned gives the number of rows in this portion"
    assert (result.get("total"), result.get("total_status"), result.get("truncated")) == (total, "exact", True), (
        "result.total, result.total_status and result.truncated declare the cut"
    )


def bounded_summary_list_with_declared_total(chat_client, observation, business_client, case: dict) -> None:
    observation.reset("volume")
    expected = expected_late_total(case, business_client)
    turn, trace = successful_turn(chat_client, case["question"])
    found = listings(trace)
    assert found, 'a list of orders is expected from the generic query (arguments.source "orders", result.rows)'
    result = found[-1]
    rows = result["rows"]
    bounded_and_declared(result, expected)
    if case.get("references_are_order_numbers"):
        assert all(str(r).startswith("CMD-") for r in references(result)) and len(references(result)) == len(rows)
    leaked = sorted({k for row in rows if isinstance(row, dict) for k in row if k in DETAIL_KEYS})
    assert not leaked, f"the rows are summarized, without detail fields: {leaked}"
    mentions_any(turn, str(expected), "the answer gives the total", strict=True)
    sizes = [c.get("context_size") for c in (trace.get("model") or {}).get("calls") or []]
    assert len(sizes) >= 2 and all(isinstance(s, int) and s > 0 for s in sizes), "model.calls[].context_size at each cycle"
    apply_rubric(case["rubric"], turn, trace)


def next_portions_without_repeating_rows(chat_client, observation, case: dict) -> None:
    observation.reset("volume")
    _, first = successful_turn(chat_client, case["question"])
    assert listings(first), "the first portion comes from the generic query"
    seen = set(references(listings(first)[-1]))
    for follow_up in case["follow_ups"]:
        _, trace = successful_turn(chat_client, follow_up)
        found = listings(trace)
        assert found, "the next portion is read again from the tool, not invented"
        following = references(found[-1])
        assert following, "the next portion holds rows"
        assert seen.isdisjoint(following), "the next portion does not repeat the rows already received"
        seen |= set(following)


def total_is_a_minimum_at_the_retrieval_cap(chat_client, observation, case: dict) -> None:
    observation.reset("volume")
    turn, trace = successful_turn(chat_client, case["question"])
    found = listings(trace)
    assert found, 'a list of orders is expected from the generic query (arguments.source "orders", result.rows)'
    result = found[-1]
    minimum = case["minimum_total"]
    assert (result.get("total"), result.get("total_status")) == (minimum, "minimum"), (
        "beyond the retrieval cap, the total is declared a minimum"
    )
    assert mentions(turn, str(minimum), strict=True) and mentions(turn, case["minimum_words"]), (
        f"the answer says the total is at least {minimum}"
    )


def count_mode(chat_client, observation, business_client, case: dict) -> None:
    observation.reset("volume")
    expected = expected_late_total(case, business_client)
    turn, trace = successful_turn(chat_client, case["question"])
    counted = [c for c in tools(trace) if tool_arguments(c).get("aggregate") == "count" and tool_result(c).get("value") == expected]
    assert counted, 'a count is asked to the generic query (arguments.aggregate "count", result.value), not computed from rows'
    assert not tool_result(counted[-1]).get("rows"), "the count returns no rows"
    mentions_any(turn, str(expected), "the answer gives the count", strict=True)


def large_grouping_is_bounded_and_declared(chat_client, observation, business_client, case: dict) -> None:
    observation.reset("volume")
    expected = morel_query(business_client, group_by=case["group_by"])["total"]
    assert expected > DISPLAY_LIMIT, "the case asks for more groups than the display limit"
    turn, trace = successful_turn(chat_client, case["question"])
    grouped = [c for c in tools(trace) if tool_arguments(c).get("source") == "orders" and tool_arguments(c).get("group_by")]
    assert grouped, 'the grouping is asked to the generic query (arguments.group_by)'
    bounded_and_declared(tool_result(grouped[-1]), expected)
    mentions_any(turn, str(expected), "the answer gives the number of groups", strict=True)


def detail_through_the_consultation_tool(chat_client, observation, business_client, case: dict) -> None:
    observation.reset("volume")
    chat_client.load(case["conversation"])
    shown = [c["result"] for c in tool_results(case["conversation"]) if is_listing(c["result"])][-1]
    reference = references(shown)[case["row"]]
    amount = business_client.get(f"/orders/{reference}").json()["amount"]
    # The read above is logged too: only a read made during the agent's turn counts.
    before = [str(e.get("route", "")) for e in business_log(observation)].count(f"/orders/{reference}")
    turn, _ = successful_turn(chat_client, case["detail_question"].format(reference=reference))
    routes = [str(e.get("route", "")) for e in business_log(observation)]
    assert routes.count(f"/orders/{reference}") > before, (
        "the detail is read with the consultation tool (GET /orders/<reference>) during the turn"
    )
    text = turn.text.replace("\u202f", "").replace("\xa0", "").replace(" ", "")
    assert f"{amount:.2f}" in text or f"{amount:.2f}".replace(".", ",") in text, f"the answer gives the amount ({amount})"
