"""Private tests of workshop 07 (not given to students): same criteria, other inputs.

Other phrasings, totals read from the business API (never hard-coded), a third portion,
the detail of another row of the list.
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
LATE_QUESTION = "Transports Morel : quelles commandes ont dépassé leur date de livraison promise ?"

PARTIAL_RUBRIC = {
    "id": "07-private-partial-result-announced",
    "criterion": "The agent says in French that it shows only part of the list, gives the total read from the tool "
    "and offers the rest or a narrower request.",
    "judge_meaning": True,
    "requirements": [{"type": "required_any", "patterns": ["partiel", "partielle", "une partie", "extrait", "premières", "suivantes"]}],
}


def _listings(trace) -> list[dict]:
    return [tool_result(c) for c in tools(trace) if isinstance(tool_result(c).get("orders"), list)]


def _references(listing: dict) -> list[str]:
    return [str(row.get("reference")) for row in listing["orders"] if isinstance(row, dict)]


def _late_total(business_client) -> int:
    customer = business_client.get("/customers", params={"name": "Transports Morel"}).json()[0]
    return business_client.get(f"/customers/{customer['id']}/orders", params={"filter": "late"}).json()["total"]


def test_bounded_summary_list_with_declared_total(chat_client, observation, business_client):
    observation.reset("volume")
    expected = _late_total(business_client)
    turn, trace = successful_turn(chat_client, LATE_QUESTION)
    listings = _listings(trace)
    assert listings, "a list of orders is expected in a tool result (result.orders)"
    result = listings[-1]
    rows = result["orders"]
    assert 0 < len(rows) <= DISPLAY_LIMIT, f"at most {DISPLAY_LIMIT} rows are shown to the model"
    assert result.get("returned") == len(rows)
    assert (result.get("total"), result.get("total_status"), result.get("truncated")) == (expected, "exact", True)
    leaked = sorted({k for row in rows if isinstance(row, dict) for k in row if k in DETAIL_KEYS})
    assert not leaked, f"the rows are summarized, without detail fields: {leaked}"
    assert str(expected) in turn.text, f"the answer gives the total ({expected})"
    sizes = [c.get("context_size") for c in (trace.get("model") or {}).get("calls") or []]
    assert len(sizes) >= 2 and all(isinstance(s, int) and s > 0 for s in sizes), "model.calls[].context_size at each cycle"
    apply_rubric(PARTIAL_RUBRIC, turn, trace)


def test_small_list_is_not_declared_partial(chat_client, observation, business_client):
    expected = _late_total(business_client)  # standard dataset: fewer late orders than the display limit
    assert 0 < expected <= DISPLAY_LIMIT
    _, trace = successful_turn(chat_client, LATE_QUESTION)
    listings = _listings(trace)
    assert listings, "a list of orders is expected in a tool result (result.orders)"
    result = listings[-1]
    assert (result.get("total"), result.get("total_status"), result.get("truncated")) == (expected, "exact", False)
    assert result.get("returned") == len(result["orders"]) == expected


def test_two_next_portions_without_repeating_rows(chat_client, observation):
    observation.reset("volume")
    _, first = successful_turn(chat_client, LATE_QUESTION)
    assert _listings(first), "the first portion comes from the order-list tool"
    seen = set(_references(_listings(first)[-1]))
    for follow_up in ("Et la page d'après ?", "Encore la suite, s'il vous plaît."):
        _, trace = successful_turn(chat_client, follow_up)
        listings = _listings(trace)
        assert listings, "the next portion is read again from the tool, not invented"
        following = _references(listings[-1])
        assert following, "the next portion holds rows"
        assert seen.isdisjoint(following), "the next portion does not repeat the rows already received"
        seen |= set(following)


def test_total_is_a_minimum_at_the_retrieval_cap(chat_client, observation):
    observation.reset("volume")
    turn, trace = successful_turn(chat_client, "Je voudrais l'ensemble des commandes passées par Transports Morel.")
    listings = _listings(trace)
    assert listings, "a list of orders is expected in a tool result (result.orders)"
    result = listings[-1]
    assert (result.get("total"), result.get("total_status")) == (200, "minimum")
    text = turn.text.lower()
    assert "200" in text and any(p in text for p in ("au moins", "plus de", "minimum")), "the answer says the total is at least 200"


def test_count_mode(chat_client, observation, business_client):
    observation.reset("volume")
    expected = _late_total(business_client)
    turn, trace = successful_turn(
        chat_client, "Donnez-moi seulement le chiffre : combien Transports Morel a-t-il de commandes en retard ?"
    )
    counted = [c for c in tools(trace) if tool_result(c).get("count") == expected]
    assert counted, "a count-mode call returns result.count, the number without the rows"
    assert not tool_result(counted[-1]).get("orders"), "count mode returns no rows"
    assert tool_arguments(counted[-1]).get("mode") == "count", "count mode is a tool argument (mode: \"count\")"
    assert str(expected) in turn.text


def test_detail_through_the_consultation_tool(chat_client, observation, business_client):
    observation.reset("volume")
    _, first = successful_turn(chat_client, LATE_QUESTION)
    assert _listings(first), "the list comes from the order-list tool"
    reference = _references(_listings(first)[-1])[2]
    amount = business_client.get(f"/orders/{reference}").json()["amount"]
    turn, _ = successful_turn(chat_client, f"Combien coûte la commande {reference} ?")
    routes = [str(e.get("route", "")) for e in business_log(observation)]
    assert f"/orders/{reference}" in routes, "the detail is read with the consultation tool (GET /orders/<reference>)"
    text = turn.text.replace("\u202f", "").replace("\xa0", "").replace(" ", "")
    assert f"{amount:.2f}" in text or f"{amount:.2f}".replace(".", ",") in text, f"the answer gives the amount ({amount})"
