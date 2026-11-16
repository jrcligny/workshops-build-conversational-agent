"""End-to-end tests of workshop 06. They must fail on the empty shell.

Trace contract read here: `cycles` (int, number of model calls in the loop), `tools[].cycle`
(index of the cycle that ran the call), `cycle_limit_reached` (bool), `interrupted` (bool).
Interface events read here: `step` (data.cycle, data.tool), `mention`, `interruption`.
"""

import pytest

from workshop_tests.testing.turns import apply_rubric_repeatedly, events_of, successful_turn, tool_name, tools

pytestmark = pytest.mark.workshop

CHAINED = "Trouvez Léa Martin de Lille et donnez-moi le statut de sa commande."
LONG_REVIEW = (
    "Faites une revue complète de toutes les commandes de Transports Morel, une par une, "
    "en vérifiant le détail de chacune, sans vous arrêter."
)

PARTIAL_RUBRIC = {
    "id": "06-cycle-limit-partial",
    "criterion": (
        "At the cycle limit, the agent says in French that its answer is partial and names what "
        "it could not verify; it does not present the review as complete."
    ),
    "judge_meaning": True,
    "requirements": [
        {"type": "required_any", "patterns": ["partiel", "partielle", "incomplet", "incomplète"]},
        {"type": "forbidden", "patterns": ["revue complète effectuée", "toutes les commandes ont été vérifiées"]},
    ],
}


def test_several_cycles(chat_client):
    _, trace = successful_turn(chat_client, CHAINED)
    assert isinstance(trace.get("cycles"), int) and trace["cycles"] >= 2, "trace.cycles counts the loop cycles (>= 2 here)"
    names = [tool_name(c) for c in tools(trace)]
    assert len(names) >= 2, "a chained question needs a customer search, then an order call"
    cycles = [c.get("cycle") for c in tools(trace)]
    assert all(isinstance(i, int) for i in cycles), "each tools[] entry records its cycle index"
    assert cycles == sorted(cycles) and cycles[0] < cycles[-1], "the order call comes in a later cycle than the search"


def test_independent_calls_grouped(chat_client):
    _, trace = successful_turn(
        chat_client,
        "Donnez-moi le statut de CMD-1042 et, en même temps, la liste des clients nommés Léa Martin.",
    )
    calls = tools(trace)
    assert len({tool_name(c) for c in calls}) >= 2, "two independent calls are expected"
    cycles = [c.get("cycle") for c in calls]
    assert all(isinstance(i, int) for i in cycles), "each tools[] entry records its cycle index"
    assert len(set(cycles)) < len(cycles), "independent calls requested together run in the same cycle"


def test_steps_reported_to_the_interface(chat_client):
    turn, trace = successful_turn(chat_client, CHAINED)
    steps = events_of(turn, "step")
    assert len(steps) == len(tools(trace)) >= 2, "one step event per tool call"
    assert [s.get("tool") for s in steps] == [tool_name(c) for c in tools(trace)], "step.tool names the tool called"


def test_cycle_limit_partial_answer(chat_client):
    def run():
        chat_client.open()
        turn, trace = successful_turn(chat_client, LONG_REVIEW)
        assert trace.get("cycle_limit_reached") is True, "trace.cycle_limit_reached must be true on this request"
        assert events_of(turn, "mention"), "reaching the cycle cap is declared through a mention event"
        return turn, trace

    apply_rubric_repeatedly(PARTIAL_RUBRIC, run)


def test_interruption_stops_without_new_call(chat_client):
    chat_client.open()
    chat_client.interrupt()
    turn, trace = successful_turn(chat_client, "Trouvez Léa Martin de Lille, puis toutes ses commandes, puis leur détail.")
    assert events_of(turn, "interruption"), "the interface receives an interruption event"
    assert trace.get("interrupted") is True, "trace.interrupted records the clean stop"
    assert tools(trace) == [], "no tool call is launched after the interruption"
    assert "step" not in turn.types


def test_without_interruption_the_same_request_runs(chat_client):
    _, trace = successful_turn(chat_client, "Trouvez Léa Martin de Lille, puis toutes ses commandes, puis leur détail.")
    assert trace.get("interrupted") is False, "trace.interrupted is false when no interruption was asked"
    assert tools(trace), "the same request, not interrupted, calls tools"
