"""Checks of workshop 10c, shared by the public and the private tests (one function per criterion).

Contract read here: calls to the generic query tool (workshop 09) with `arguments.source`,
`arguments.filters`, `arguments.aggregate` (count | total | average) and `result.value`
computed by the application; for a refused aggregate, `result.refused` and
`result.available_aggregates` returned by the application.
"""

from agent_testkit.turns import apply_rubric_repeatedly, successful_turn, tool_arguments, tool_name, tool_result, tools


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


def grouping_computed_by_the_tool(chat_client, observation, business_client, case: dict) -> None:
    observation.reset("volume")
    expected = expected_value(business_client, case["customer"], "total", case["filters"])
    turn, trace = successful_turn(chat_client, case["question"])
    calls = aggregated(trace, "total")
    assert calls, "the sum is computed by the application (aggregate: \"total\"), not by the model"
    for key, value in case["filters"].items():
        assert (tool_arguments(calls[-1]).get("filters") or {}).get(key) == value, f"the {key} is a filter of the query"
    assert tool_result(calls[-1]).get("value") == expected
    assert not any(isinstance(tool_result(c).get("rows"), list) and len(tool_result(c)["rows"]) > 20 for c in tools(trace)), (
        "the rows are not fetched to be summed by the model"
    )
    assert number_in(expected, turn.text), f"the answer gives the total computed by the application ({expected})"


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
