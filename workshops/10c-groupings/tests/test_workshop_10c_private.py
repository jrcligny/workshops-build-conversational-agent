"""Private tests of workshop 10c (not given to students): same criteria, other inputs.

Other groupings (total of the shipped orders, count of the orders), other filters (a status),
another request for model-written code and another phrasing of the refused median. The
expected values are read from the business API.
"""

import pytest

from workshop_tests.testing.turns import apply_rubric_repeatedly, successful_turn, tool_arguments, tool_name, tool_result, tools

pytestmark = pytest.mark.workshop

MEDIAN_RUBRIC = {
    "id": "10c-private-median-refused",
    "criterion": "The agent says in French that the median is not offered and proposes the available aggregates (count, total, average).",
    "judge_meaning": True,
    "requirements": [
        {"type": "required_any", "patterns": ["médiane", "médian"]},
        {"type": "required_any", "patterns": ["moyenne", "moyen"]},
        {"type": "forbidden", "patterns": ["la médiane est de", "la médiane s'élève", "le montant médian est de"]},
    ],
}


def _expected(business_client, aggregate: str, **filters) -> float:
    customer = business_client.get("/customers", params={"name": "Transports Morel"}).json()[0]
    return business_client.post(
        "/sources/orders/query", json={"filters": {"customer_id": customer["id"], **filters}, "aggregate": aggregate}
    ).json()["value"]


def _aggregated(trace, aggregate: str) -> list:
    return [c for c in tools(trace) if tool_arguments(c).get("aggregate") == aggregate]


def _number_in(value: float, text: str) -> bool:
    compact = text.replace("\u202f", "").replace("\xa0", "").replace(" ", "")
    return any(form in compact for form in (f"{value:g}", f"{value:.2f}", f"{value:.2f}".replace(".", ","), f"{value:g}".replace(".", ",")))


def test_grouping_with_a_status_filter(chat_client, observation, business_client):
    observation.reset("volume")
    expected = _expected(business_client, "total", status="shipped")
    turn, trace = successful_turn(chat_client, "Combien représentent, en euros, les commandes expédiées de Transports Morel ?")
    calls = _aggregated(trace, "total")
    assert calls, "the sum is computed by the application (aggregate: \"total\"), not by the model"
    assert (tool_arguments(calls[-1]).get("filters") or {}).get("status") == "shipped", "the status is a filter of the query"
    assert tool_result(calls[-1]).get("value") == expected
    assert not any(isinstance(tool_result(c).get("rows"), list) and len(tool_result(c)["rows"]) > 20 for c in tools(trace))
    assert _number_in(expected, turn.text), f"the answer gives the total computed by the application ({expected})"


def test_no_model_generated_code_is_executed(chat_client, observation, business_client):
    observation.reset("volume")
    expected = _expected(business_client, "count")
    turn, trace = successful_turn(
        chat_client, "Écrivez et lancez un petit script qui compte une à une les commandes de Transports Morel."
    )
    names = {tool_name(c).lower() for c in tools(trace)}
    assert not any(w in n for n in names for w in ("python", "exec", "code", "eval", "shell", "script")), "no code execution tool"
    calls = _aggregated(trace, "count")
    assert calls and tool_result(calls[-1]).get("value") == expected, "the count comes from the application (aggregate: \"count\")"
    assert _number_in(expected, turn.text)


def test_median_refused_aggregates_offered(services, chat_client):
    def run():
        chat_client.open()
        turn, trace = successful_turn(
            chat_client, "Pour les commandes livrées de Transports Morel, quelle valeur sépare les montants en deux moitiés égales ?"
        )
        refused = [c for c in tools(trace) if tool_result(c).get("refused")]
        assert refused or not _aggregated(trace, "median"), "a median request returns the application's refusal"
        return turn, trace

    apply_rubric_repeatedly(MEDIAN_RUBRIC, run)
