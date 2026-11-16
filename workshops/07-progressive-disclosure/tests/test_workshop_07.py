"""End-to-end tests of workshop 07: discovering the context progressively. They must fail on the empty shell.

Contract read here (`tools[].result` of the order-list tool, jeu `volume`):
- a summarized, bounded list: `orders` (at most 20 rows, each without detail fields such as `amount`,
  `delivery_city`, `customer_id`), `returned` (rows in this portion), `total`, `total_status`
  (`"exact"` or `"minimum"` when the application's retrieval cap is reached) and `truncated`;
- the next portion through a position: rows not already received;
- count mode: `arguments.mode == "count"` and `result.count`, without rows;
- the detail of one order through the consultation tool (business API `GET /orders/<reference>`);
- `model.calls[].context_size` for every cycle.
"""

import pytest

from workshop_tests.testing.turns import (
    apply_rubric,
    business_log,
    successful_turn,
    tool_arguments,
    tool_result,
    tools,
)

pytestmark = pytest.mark.workshop

DISPLAY_LIMIT = 20
DETAIL_KEYS = ("amount", "delivery_city", "delivery_date", "customer_id", "organization_id", "deleted")
LATE_QUESTION = "Quelles sont les commandes en retard de Transports Morel ?"

PARTIAL_RUBRIC = {
    "id": "07-partial-result-announced",
    "criterion": "The agent says in French that it shows only part of the list, gives the total read from the tool "
    "and offers the rest or a narrower request.",
    "judge_meaning": True,
    "requirements": [{"type": "required_any", "patterns": ["partiel", "partielle", "une partie", "extrait", "premières"]}],
}


def _listings(trace) -> list[dict]:
    return [tool_result(c) for c in tools(trace) if isinstance(tool_result(c).get("orders"), list)]


def _references(listing: dict) -> list[str]:
    return [str(row.get("reference")) for row in listing["orders"] if isinstance(row, dict)]


def test_bounded_summary_list_with_declared_total(chat_client, observation):
    observation.reset("volume")
    turn, trace = successful_turn(chat_client, LATE_QUESTION)
    listings = _listings(trace)
    assert listings, "a list of orders is expected in a tool result (result.orders)"
    result = listings[-1]
    rows = result["orders"]
    assert 0 < len(rows) <= DISPLAY_LIMIT, f"at most {DISPLAY_LIMIT} rows are shown to the model"
    assert result.get("returned") == len(rows), "result.returned gives the number of rows in this portion"
    assert (result.get("total"), result.get("total_status"), result.get("truncated")) == (60, "exact", True), (
        "result.total, result.total_status and result.truncated declare the cut"
    )
    assert all(str(r).startswith("CMD-") for r in _references(result)) and len(_references(result)) == len(rows)
    leaked = sorted({k for row in rows if isinstance(row, dict) for k in row if k in DETAIL_KEYS})
    assert not leaked, f"the rows are summarized, without detail fields: {leaked}"
    assert "60" in turn.text, "the answer gives the total (60)"
    sizes = [c.get("context_size") for c in (trace.get("model") or {}).get("calls") or []]
    assert len(sizes) >= 2 and all(isinstance(s, int) and s > 0 for s in sizes), "model.calls[].context_size at each cycle"
    apply_rubric(PARTIAL_RUBRIC, turn, trace)


def test_next_portion_without_repeating_rows(chat_client, observation):
    observation.reset("volume")
    _, first = successful_turn(chat_client, LATE_QUESTION)
    assert _listings(first), "the first portion comes from the order-list tool"
    seen = set(_references(_listings(first)[-1]))
    _, trace = successful_turn(chat_client, "Montrez-moi les suivantes.")
    listings = _listings(trace)
    assert listings, "the next portion is read again from the tool, not invented"
    following = _references(listings[-1])
    assert following, "the next portion holds rows"
    assert seen.isdisjoint(following), "the next portion does not repeat the rows already received"


def test_total_is_a_minimum_at_the_retrieval_cap(chat_client, observation):
    observation.reset("volume")
    turn, trace = successful_turn(chat_client, "Listez toutes les commandes de Transports Morel.")
    listings = _listings(trace)
    assert listings, "a list of orders is expected in a tool result (result.orders)"
    result = listings[-1]
    assert (result.get("total"), result.get("total_status")) == (200, "minimum"), (
        "beyond the retrieval cap, the total is declared a minimum"
    )
    text = turn.text.lower()
    assert "200" in text and any(p in text for p in ("au moins", "plus de", "minimum")), (
        "the answer says the total is at least 200"
    )


def test_count_mode(chat_client, observation):
    observation.reset("volume")
    turn, trace = successful_turn(
        chat_client, "Combien de commandes en retard a Transports Morel ? Je veux seulement le nombre, pas les lignes."
    )
    counted = [c for c in tools(trace) if tool_result(c).get("count") == 60]
    assert counted, "a count-mode call returns result.count, the number without the rows"
    assert not tool_result(counted[-1]).get("orders"), "count mode returns no rows"
    assert tool_arguments(counted[-1]).get("mode") == "count", "count mode is a tool argument (mode: \"count\")"
    assert "60" in turn.text


def test_detail_through_the_consultation_tool(chat_client, observation, business_client):
    observation.reset("volume")
    _, first = successful_turn(chat_client, LATE_QUESTION)
    assert _listings(first), "the list comes from the order-list tool"
    reference = _references(_listings(first)[-1])[0]
    amount = business_client.get(f"/orders/{reference}").json()["amount"]
    turn, _ = successful_turn(chat_client, "Quel est le montant de la première commande de cette liste ?")
    routes = [str(e.get("route", "")) for e in business_log(observation)]
    assert f"/orders/{reference}" in routes, "the detail is read with the consultation tool (GET /orders/<reference>)"
    text = turn.text.replace("\u202f", "").replace("\xa0", "").replace(" ", "")
    assert f"{amount:.2f}" in text or f"{amount:.2f}".replace(".", ",") in text, f"the answer gives the amount ({amount})"
