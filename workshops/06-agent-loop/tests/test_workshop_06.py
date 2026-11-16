"""End-to-end tests of workshop 06. They must fail on the empty shell."""

import pytest

from workshop_kit.testing.turns import apply_rubric, flat, successful_turn, tools

pytestmark = pytest.mark.workshop


PARTIAL_RUBRIC = {
    "id": "06-cycle-limit-partial",
    "judge_meaning": True,
    "requirements": [
        {"type": "required_any", "patterns": ["partial", "could not", "couldn't", "not verified", "incomplete", "missing"]},
    ],
}


def test_several_cycles(chat_client):
    turn, trace = successful_turn(chat_client, "Find Léa Martin from Lille and give me the status of her order.")
    cycles = trace.get("cycles") or tools(trace)
    assert cycles, "the agent loop must produce several cycles or calls"
    if trace.get("cycles"):
        assert (isinstance(trace["cycles"], int) and trace["cycles"] >= 2) or len(trace["cycles"]) >= 2


def test_independent_calls_grouped(chat_client):
    _, trace = successful_turn(
        chat_client,
        "Give me the status of CMD-1042 and, in parallel, the number of orders of Martin Durand.",
    )
    calls = tools(trace)
    assert len(calls) >= 2
    # at least two calls carry the same cycle index, when it is exposed
    indices = [c.get("cycle") or c.get("cycle_id") for c in calls if c.get("cycle") or c.get("cycle_id") is not None]
    if indices:
        assert len(set(indices)) < len(indices), "independent calls must be grouped in the same cycle"


def test_steps_reported_to_the_interface(chat_client):
    turn, _ = successful_turn(chat_client, "Find Léa Martin from Lille and give me the status of her order.")
    assert "step" in turn.types


def test_cycle_limit_partial_answer(chat_client):
    turn, trace = successful_turn(
        chat_client,
        "Make a full review of every order of Transports Morel, linked customer by linked customer, without stopping.",
    )
    if "mention" in turn.types or "partial" in turn.text.lower():
        apply_rubric(PARTIAL_RUBRIC, turn, trace)
        return
    # without a mention, the trace must show that a cycle cap was reached
    assert "limit" in flat(trace).lower() or "cap" in flat(trace).lower() or "max_cycles" in flat(trace).lower()
    apply_rubric(PARTIAL_RUBRIC, turn, trace)


def test_interruption_stops_without_new_call(chat_client):
    chat_client.open()
    chat_client.interrupt()
    turn, trace = successful_turn(
        chat_client,
        "Find Léa Martin from Lille, then all her orders, then their details.",
        interrupt=True,
    )
    assert "interruption" in turn.types or "interrupted" in turn.text.lower() or "interrupt" in flat(trace).lower()
    # no new call after the interruption event
    after = False
    for event_type, _ in turn.events:
        if event_type == "interruption":
            after = True
        if after:
            assert event_type in {"interruption", "text", "mention", "end", "error"}
