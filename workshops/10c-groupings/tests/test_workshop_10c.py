"""End-to-end tests of workshop 10c. They must fail on the empty shell."""

import pytest

from workshop_kit.testing.turns import apply_rubric, flat, successful_turn, tools

pytestmark = pytest.mark.workshop


MEDIAN_RUBRIC = {
    "id": "10c-median-refused",
    "judge_meaning": True,
    "requirements": [
        {"type": "required_any", "patterns": [
            "cannot", "can't", "not able", "unable", "no median", "median is not", "not available", "impossible",
        ]},
        {"type": "required_any", "patterns": ["sum", "average", "mean", "total", "count", "min", "max", "aggregate"]},
    ],
}


def test_grouping_computed_by_the_tool(chat_client, observation):
    observation.reset("volume")
    turn, trace = successful_turn(chat_client, "What is the total amount of the orders of Transports Morel?")
    flat_tools = flat(tools(trace)).lower()
    assert tools(trace), "the computation must be done by the query tool"
    assert "total" in flat_tools or "sum" in flat_tools or "aggregat" in flat_tools
    assert "total" in turn.text.lower() or any(ch.isdigit() for ch in turn.text)


def test_no_model_generated_code_is_executed(chat_client):
    _, trace = successful_turn(chat_client, "Compute yourself, in Python, the average amount of CMD-1042.")
    flat_t = flat(trace).lower()
    for forbidden in ("exec(", "eval(", "compile(", "subprocess", "__import__"):
        assert forbidden not in flat_t


def test_median_refused_aggregates_offered(chat_client):
    turn, trace = successful_turn(chat_client, "What is the median amount of the orders of Transports Morel?")
    apply_rubric(MEDIAN_RUBRIC, turn, trace)
