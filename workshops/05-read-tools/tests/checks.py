"""Checks of workshop 05, shared by the public and the private tests (one function per criterion).

Trace contract read here: `tools[]` (`name`, `arguments`, `result.status`). The late filter
is an argument of the tool call: `filter: "late"`, the value used by the business API.
"""

from testkit.turns import successful_turn, tool_arguments, tool_result, tool_status, tools


def namesakes_several_candidates(chat_client, case: dict) -> None:
    turn, trace = successful_turn(chat_client, case["question"])
    candidates = case["candidates"]
    results = " ".join(str(tool_result(c)) for c in tools(trace) if tool_status(c) == "ok")
    assert all(customer in results for customer in candidates), (
        f"the customer search must return every namesake ({' and '.join(candidates.values())})"
    )
    text = turn.text.lower()
    assert all(city.lower() in text for city in candidates.values()), "the answer presents both candidates"
    assert all(reference not in turn.text for reference in case["orders_of_one_namesake"]), (
        "the agent must not pick one namesake and list its orders on behalf of the user"
    )


def late_filter_applied_by_the_tool(chat_client, observation, business_client, case: dict) -> None:
    observation.reset(case["dataset"])
    customer = business_client.get("/customers", params={"name": case["customer"]}).json()[0]
    expected = business_client.get(f"/customers/{customer['id']}/orders", params={"filter": "late"}).json()["total"]
    turn, trace = successful_turn(chat_client, case["question"])
    filtered = [c for c in tools(trace) if tool_arguments(c).get("filter") == "late"]
    assert filtered, "the late filter is an argument of the tool call (filter: \"late\"), not a selection made by the model"
    result = tool_result(filtered[-1])
    assert expected in (result.get("total"), result.get("count")), "result.total (or result.count) is the number of late orders"
    text = turn.text.lower()
    zero_word = case.get("zero_word")
    assert str(expected) in text or (zero_word is not None and expected == 0 and zero_word in text), (
        f"the answer must give the number of late orders read from the tool ({expected})"
    )
    for reference in case.get("not_late", []):
        assert reference not in turn.text, "a delivered order is not presented as late"
