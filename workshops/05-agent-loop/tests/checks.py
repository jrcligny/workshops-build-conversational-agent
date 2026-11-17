"""Checks of workshop 05, shared by the public and the private tests (one function per criterion).

Step `outils` (the read tools). Trace contract read here: `tools[]` (`name`, `arguments`,
`result.status`). The late filter is an argument of the tool call: `filter: "late"`, the value
used by the business API.

Step `boucle` (the agent loop). Trace contract read here: `cycles` (int, number of model calls in
the loop), `tools[].cycle` (index of the cycle that ran the call), `cycle_limit_reached` (bool),
`interrupted` (bool). Interface events read here: `step` (data.cycle, data.tool), `mention`,
`interruption`.
"""

from agent_testkit.expect import expect_event, expect_no_event, mentions, mentions_all, mentions_none, no_tool_called
from agent_testkit.turns import (
    apply_rubric_repeatedly,
    events_of,
    repeatedly,
    successful_turn,
    tool_arguments,
    tool_name,
    tool_result,
    tool_status,
    tools,
)


def namesakes_several_candidates(chat_client, case: dict) -> None:
    turn, trace = successful_turn(chat_client, case["question"])
    candidates = case["candidates"]
    results = " ".join(str(tool_result(c)) for c in tools(trace) if tool_status(c) == "ok")
    assert all(customer in results for customer in candidates), (
        f"the customer search must return every namesake ({' and '.join(candidates.values())})"
    )
    mentions_all(turn, candidates.values(), "the answer presents both candidates")
    mentions_none(
        turn, case["orders_of_one_namesake"], "the agent must not pick one namesake and list its orders on behalf of the user", strict=True
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
    zero_word = case.get("zero_word")
    assert mentions(turn, str(expected), strict=True) or (zero_word is not None and expected == 0 and mentions(turn, zero_word)), (
        f"the answer must give the number of late orders read from the tool ({expected})"
    )
    mentions_none(turn, case.get("not_late", []), "a delivered order is not presented as late", strict=True)


def several_cycles(chat_client, case: dict) -> None:
    def check():
        chat_client.open()
        _, trace = successful_turn(chat_client, case["question"])
        assert isinstance(trace.get("cycles"), int) and trace["cycles"] >= 2, "trace.cycles counts the loop cycles (>= 2 here)"
        names = [tool_name(c) for c in tools(trace)]
        assert len(names) >= 2, "a chained question needs a customer search, then a call on its orders"
        cycles = [c.get("cycle") for c in tools(trace)]
        assert all(isinstance(i, int) for i in cycles), "each tools[] entry records its cycle index"
        assert cycles == sorted(cycles) and cycles[0] < cycles[-1], "the call on the orders comes in a later cycle than the search"
        assert trace["cycles"] > max(cycles), "the loop ends with a model call that answers, after the last tool call"

    repeatedly(check, label=case["label"])


def independent_calls_grouped(chat_client, case: dict) -> None:
    def check():
        chat_client.open()
        _, trace = successful_turn(chat_client, case["question"])
        calls = tools(trace)
        assert len({tool_name(c) for c in calls}) >= 2, "two independent calls are expected"
        cycles = [c.get("cycle") for c in calls]
        assert all(isinstance(i, int) for i in cycles), "each tools[] entry records its cycle index"
        assert len(set(cycles)) < len(cycles), "independent calls requested together run in the same cycle"

    repeatedly(check, label=case["label"])


def steps_reported_to_the_interface(chat_client, case: dict) -> None:
    turn, trace = successful_turn(chat_client, case["question"])
    steps = events_of(turn, "step")
    assert len(steps) == len(tools(trace)) >= 2, "one step event per tool call"
    assert [s.get("tool") for s in steps] == [tool_name(c) for c in tools(trace)], "step.tool names the tool called"


def cycle_limit_partial_answer(chat_client, case: dict) -> None:
    def run():
        chat_client.open()
        turn, trace = successful_turn(chat_client, case["question"])
        assert trace.get("cycle_limit_reached") is True, "trace.cycle_limit_reached must be true on this request"
        expect_event(turn, "mention", message="reaching the cycle cap is declared through a mention event")
        return turn, trace

    apply_rubric_repeatedly(case["rubric"], run)


def interruption_stops_without_new_call(chat_client, case: dict) -> None:
    chat_client.open()
    chat_client.interrupt()
    turn, trace = successful_turn(chat_client, case["question"])
    expect_event(turn, "interruption", message="the interface receives an interruption event")
    assert trace.get("interrupted") is True, "trace.interrupted records the clean stop"
    no_tool_called(trace, "no tool call is launched after the interruption")
    expect_no_event(turn, "step", "no step is reported after the interruption")


def without_interruption_the_same_request_runs(chat_client, case: dict) -> None:
    _, trace = successful_turn(chat_client, case["question"])
    assert trace.get("interrupted") is False, "trace.interrupted is false when no interruption was asked"
    assert tools(trace), "the same request, not interrupted, calls tools"
