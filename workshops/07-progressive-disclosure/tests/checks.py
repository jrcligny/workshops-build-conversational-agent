"""Checks of workshop 07, shared by the public and the private tests (one function per criterion).

Contract read here (`tools[].result` of the order-list tool, jeu `volume`):
- a summarized, bounded list: `orders` (at most 20 rows, each without detail fields such as `amount`,
  `delivery_city`, `customer_id`), `returned` (rows in this portion), `total`, `total_status`
  (`"exact"` or `"minimum"` when the application's retrieval cap is reached) and `truncated`;
- the next portion through a position: rows not already received;
- count mode: `arguments.mode == "count"` and `result.count`, without rows;
- the detail of one order through the consultation tool (business API `GET /orders/<reference>`);
- `model.calls[].context_size` for every cycle.

An expected total given by a case is checked as is; a case without one reads it from the business API.
"""

from workshop_tests.testing.turns import (
    apply_rubric,
    business_log,
    successful_turn,
    tool_arguments,
    tool_result,
    tools,
)

DISPLAY_LIMIT = 20
DETAIL_KEYS = ("amount", "delivery_city", "delivery_date", "customer_id", "organization_id", "deleted")


def listings(trace) -> list[dict]:
    return [tool_result(c) for c in tools(trace) if isinstance(tool_result(c).get("orders"), list)]


def references(listing: dict) -> list[str]:
    return [str(row.get("reference")) for row in listing["orders"] if isinstance(row, dict)]


def late_total(business_client) -> int:
    customer = business_client.get("/customers", params={"name": "Transports Morel"}).json()[0]
    return business_client.get(f"/customers/{customer['id']}/orders", params={"filter": "late"}).json()["total"]


def expected_late_total(case: dict, business_client) -> int:
    return case["total"] if case.get("total") is not None else late_total(business_client)


def bounded_summary_list_with_declared_total(chat_client, observation, business_client, case: dict) -> None:
    observation.reset("volume")
    expected = expected_late_total(case, business_client)
    turn, trace = successful_turn(chat_client, case["question"])
    found = listings(trace)
    assert found, "a list of orders is expected in a tool result (result.orders)"
    result = found[-1]
    rows = result["orders"]
    assert 0 < len(rows) <= DISPLAY_LIMIT, f"at most {DISPLAY_LIMIT} rows are shown to the model"
    assert result.get("returned") == len(rows), "result.returned gives the number of rows in this portion"
    assert (result.get("total"), result.get("total_status"), result.get("truncated")) == (expected, "exact", True), (
        "result.total, result.total_status and result.truncated declare the cut"
    )
    if case.get("references_are_order_numbers"):
        assert all(str(r).startswith("CMD-") for r in references(result)) and len(references(result)) == len(rows)
    leaked = sorted({k for row in rows if isinstance(row, dict) for k in row if k in DETAIL_KEYS})
    assert not leaked, f"the rows are summarized, without detail fields: {leaked}"
    assert str(expected) in turn.text, f"the answer gives the total ({expected})"
    sizes = [c.get("context_size") for c in (trace.get("model") or {}).get("calls") or []]
    assert len(sizes) >= 2 and all(isinstance(s, int) and s > 0 for s in sizes), "model.calls[].context_size at each cycle"
    apply_rubric(case["rubric"], turn, trace)


def next_portions_without_repeating_rows(chat_client, observation, case: dict) -> None:
    observation.reset("volume")
    _, first = successful_turn(chat_client, case["question"])
    assert listings(first), "the first portion comes from the order-list tool"
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
    assert found, "a list of orders is expected in a tool result (result.orders)"
    result = found[-1]
    minimum = case["minimum_total"]
    assert (result.get("total"), result.get("total_status")) == (minimum, "minimum"), (
        "beyond the retrieval cap, the total is declared a minimum"
    )
    text = turn.text.lower()
    assert str(minimum) in text and any(p in text for p in case["minimum_words"]), (
        f"the answer says the total is at least {minimum}"
    )


def count_mode(chat_client, observation, business_client, case: dict) -> None:
    observation.reset("volume")
    expected = expected_late_total(case, business_client)
    turn, trace = successful_turn(chat_client, case["question"])
    counted = [c for c in tools(trace) if tool_result(c).get("count") == expected]
    assert counted, "a count-mode call returns result.count, the number without the rows"
    assert not tool_result(counted[-1]).get("orders"), "count mode returns no rows"
    assert tool_arguments(counted[-1]).get("mode") == "count", "count mode is a tool argument (mode: \"count\")"
    assert str(expected) in turn.text


def detail_through_the_consultation_tool(chat_client, observation, business_client, case: dict) -> None:
    observation.reset("volume")
    _, first = successful_turn(chat_client, case["question"])
    assert listings(first), "the list comes from the order-list tool"
    reference = references(listings(first)[-1])[case["row"]]
    amount = business_client.get(f"/orders/{reference}").json()["amount"]
    turn, _ = successful_turn(chat_client, case["detail_question"].format(reference=reference))
    routes = [str(e.get("route", "")) for e in business_log(observation)]
    assert f"/orders/{reference}" in routes, "the detail is read with the consultation tool (GET /orders/<reference>)"
    text = turn.text.replace("\u202f", "").replace("\xa0", "").replace(" ", "")
    assert f"{amount:.2f}" in text or f"{amount:.2f}".replace(".", ",") in text, f"the answer gives the amount ({amount})"
