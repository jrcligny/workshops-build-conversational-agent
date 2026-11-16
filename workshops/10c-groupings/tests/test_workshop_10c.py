"""End-to-end tests of workshop 10c. They must fail on the empty shell.

Contract read here: calls to the generic query tool (workshop 09) with `arguments.source`,
`arguments.filters`, `arguments.aggregate` (count | total | average) and `result.value`
computed by the application; for a refused aggregate, `result.refused` and
`result.available_aggregates` returned by the application.
"""

import pytest

from workshop_tests.testing.turns import apply_rubric_repeatedly, successful_turn, tool_arguments, tool_name, tool_result, tools

pytestmark = pytest.mark.workshop

MEDIAN_RUBRIC = {
    "id": "10c-median-refused",
    "criterion": "The agent says in French that the median is not offered and proposes the available aggregates (count, total, average).",
    "judge_meaning": True,
    "requirements": [
        {"type": "required_any", "patterns": ["médiane"]},
        {"type": "required_any", "patterns": ["moyenne"]},
        {"type": "forbidden", "patterns": ["la médiane est de", "la médiane s'élève"]},
    ],
}


def _expected(business_client, aggregate: str) -> float:
    customer = business_client.get("/customers", params={"name": "Transports Morel"}).json()[0]
    return business_client.post(
        "/sources/orders/query", json={"filters": {"customer_id": customer["id"]}, "aggregate": aggregate}
    ).json()["value"]


def _aggregated(trace, aggregate: str) -> list:
    return [c for c in tools(trace) if tool_arguments(c).get("aggregate") == aggregate]


def _number_in(value: float, text: str) -> bool:
    compact = text.replace("\u202f", "").replace("\xa0", "").replace(" ", "")
    return any(form in compact for form in (f"{value:g}", f"{value:.2f}", f"{value:.2f}".replace(".", ","), f"{value:g}".replace(".", ",")))


def test_grouping_computed_by_the_tool(chat_client, observation, business_client):
    observation.reset("volume")
    expected = _expected(business_client, "total")
    turn, trace = successful_turn(chat_client, "Quel est le montant total des commandes de Transports Morel ?")
    calls = _aggregated(trace, "total")
    assert calls, "the sum is computed by the application (aggregate: \"total\"), not by the model"
    assert tool_result(calls[-1]).get("value") == expected
    assert not any(isinstance(tool_result(c).get("rows"), list) and len(tool_result(c)["rows"]) > 20 for c in tools(trace)), (
        "the rows are not fetched to be summed by the model"
    )
    assert _number_in(expected, turn.text), f"the answer gives the total computed by the application ({expected})"


def test_no_model_generated_code_is_executed(chat_client, observation, business_client):
    observation.reset("volume")
    expected = _expected(business_client, "average")
    turn, trace = successful_turn(chat_client, "Calculez vous-même, en Python, le montant moyen des commandes de Transports Morel.")
    names = {tool_name(c).lower() for c in tools(trace)}
    assert not any(w in n for n in names for w in ("python", "exec", "code", "eval", "shell")), "no code execution tool"
    calls = _aggregated(trace, "average")
    assert calls and tool_result(calls[-1]).get("value") == expected, "the average comes from the application (aggregate: \"average\")"
    assert _number_in(expected, turn.text)


def test_median_refused_aggregates_offered(services, chat_client):
    def run():
        chat_client.open()
        turn, trace = successful_turn(chat_client, "Quel est le montant médian des commandes de Transports Morel ?")
        refused = [c for c in tools(trace) if tool_result(c).get("refused")]
        assert refused or not _aggregated(trace, "median"), "a median request returns the application's refusal"
        return turn, trace

    apply_rubric_repeatedly(MEDIAN_RUBRIC, run)
