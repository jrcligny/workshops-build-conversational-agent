"""Checks of workshop 06, shared by the public and the private tests (one function per criterion).

Trace contract read here: `cycles` (int, number of model calls in the loop), `tools[].cycle`
(index of the cycle that ran the call), `cycle_limit_reached` (bool), `interrupted` (bool).
Interface events read here: `step` (data.cycle, data.tool), `mention`, `interruption`.
"""

from workshop_tests.testing.turns import apply_rubric_repeatedly, events_of, repeatedly, successful_turn, tool_name, tools


def several_cycles(chat_client, case: dict) -> None:
    def check():
        chat_client.open()
        _, trace = successful_turn(chat_client, case["question"])
        assert isinstance(trace.get("cycles"), int) and trace["cycles"] >= 2, "trace.cycles counts the loop cycles (>= 2 here)"
        names = [tool_name(c) for c in tools(trace)]
        assert len(names) >= 2, "a chained question needs a customer search, then an order call"
        cycles = [c.get("cycle") for c in tools(trace)]
        assert all(isinstance(i, int) for i in cycles), "each tools[] entry records its cycle index"
        assert cycles == sorted(cycles) and cycles[0] < cycles[-1], "the order call comes in a later cycle than the search"
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
        assert events_of(turn, "mention"), "reaching the cycle cap is declared through a mention event"
        return turn, trace

    apply_rubric_repeatedly(case["rubric"], run)


def interruption_stops_without_new_call(chat_client, case: dict) -> None:
    chat_client.open()
    chat_client.interrupt()
    turn, trace = successful_turn(chat_client, case["question"])
    assert events_of(turn, "interruption"), "the interface receives an interruption event"
    assert trace.get("interrupted") is True, "trace.interrupted records the clean stop"
    assert tools(trace) == [], "no tool call is launched after the interruption"
    assert "step" not in turn.types


def without_interruption_the_same_request_runs(chat_client, case: dict) -> None:
    _, trace = successful_turn(chat_client, case["question"])
    assert trace.get("interrupted") is False, "trace.interrupted is false when no interruption was asked"
    assert tools(trace), "the same request, not interrupted, calls tools"
