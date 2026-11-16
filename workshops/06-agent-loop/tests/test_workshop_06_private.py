"""Private tests of workshop 06 (not given to students): same criteria, other inputs.

Other chained and grouped questions (Léa Martin of Lyon, Martin Durand, CMD-2010), another
long review and other interrupted requests.
"""

import pytest

from workshop_tests.testing.turns import apply_rubric_repeatedly, events_of, repeatedly, successful_turn, tool_name, tools

pytestmark = pytest.mark.workshop

CHAINED = "Retrouvez le client Martin Durand puis dites-moi combien de commandes il a et lesquelles."
LONG_REVIEW = (
    "Pour chaque commande de Transports Morel, ouvrez sa fiche détaillée et vérifiez sa date promise, "
    "sans en oublier aucune, puis faites-moi un bilan exhaustif."
)

PARTIAL_RUBRIC = {
    "id": "06-private-cycle-limit-partial",
    "criterion": (
        "At the cycle limit, the agent says in French that its answer is partial and names what "
        "it could not verify; it does not present the review as exhaustive."
    ),
    "judge_meaning": True,
    "requirements": [
        {"type": "required_any", "patterns": ["partiel", "partielle", "incomplet", "incomplète", "pas pu"]},
        {"type": "forbidden", "patterns": ["bilan exhaustif effectué", "toutes les commandes ont été vérifiées"]},
    ],
}


def test_several_cycles(chat_client):
    def check():
        chat_client.open()
        _, trace = successful_turn(chat_client, CHAINED)
        assert isinstance(trace.get("cycles"), int) and trace["cycles"] >= 2, "trace.cycles counts the loop cycles (>= 2 here)"
        names = [tool_name(c) for c in tools(trace)]
        assert len(names) >= 2, "a chained question needs a customer search, then an order call"
        cycles = [c.get("cycle") for c in tools(trace)]
        assert all(isinstance(i, int) for i in cycles), "each tools[] entry records its cycle index"
        assert cycles == sorted(cycles) and cycles[0] < cycles[-1], "the order call comes in a later cycle than the search"
        assert trace["cycles"] > max(cycles), "the loop ends with a model call that answers, after the last tool call"

    repeatedly(check, label="06-private-several-cycles")


def test_independent_calls_grouped(chat_client):
    def check():
        chat_client.open()
        _, trace = successful_turn(
            chat_client,
            "Deux choses indépendantes : le statut de la commande CMD-2010, et les clients qui s'appellent Martin Durand.",
        )
        calls = tools(trace)
        assert len({tool_name(c) for c in calls}) >= 2, "two independent calls are expected"
        cycles = [c.get("cycle") for c in calls]
        assert all(isinstance(i, int) for i in cycles), "each tools[] entry records its cycle index"
        assert len(set(cycles)) < len(cycles), "independent calls requested together run in the same cycle"

    repeatedly(check, label="06-private-independent-calls-grouped")


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
    turn, trace = successful_turn(chat_client, "Cherchez Martin Durand, listez ses commandes et détaillez chacune d'elles.")
    assert events_of(turn, "interruption"), "the interface receives an interruption event"
    assert trace.get("interrupted") is True, "trace.interrupted records the clean stop"
    assert tools(trace) == [], "no tool call is launched after the interruption"
    assert "step" not in turn.types


def test_without_interruption_the_same_request_runs(chat_client):
    _, trace = successful_turn(chat_client, "Cherchez Martin Durand, listez ses commandes et détaillez chacune d'elles.")
    assert trace.get("interrupted") is False, "trace.interrupted is false when no interruption was asked"
    assert tools(trace), "the same request, not interrupted, calls tools"
