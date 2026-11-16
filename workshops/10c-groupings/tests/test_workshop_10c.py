"""End-to-end tests of workshop 10c. They must fail on the empty shell."""

import pytest

from workshop_kit.testing.turns import apply_rubric, flat, successful_turn, tools

pytestmark = pytest.mark.workshop


MEDIAN_RUBRIC = {
    "id": "10c-median-refused",
    "criterion": "The agent, answering in French, says the median is not available and offers the supported aggregates.",
    "judge_meaning": True,
    "requirements": [
        {"type": "required_any", "patterns": [
            "ne peux pas", "pas possible", "impossible", "pas en mesure", "pas de médiane",
            "médiane n'est pas", "pas disponible", "non disponible",
        ]},
        {"type": "required_any", "patterns": ["somme", "moyenne", "total", "nombre", "décompte", "min", "max", "agrégat"]},
    ],
}


def test_grouping_computed_by_the_tool(chat_client, observation):
    observation.reset("volume")
    turn, trace = successful_turn(chat_client, "Quel est le montant total des commandes de Transports Morel ?")
    flat_tools = flat(tools(trace)).lower()
    assert tools(trace), "the computation must be done by the query tool"
    assert "total" in flat_tools or "sum" in flat_tools or "aggregat" in flat_tools
    assert "total" in turn.text.lower() or any(ch.isdigit() for ch in turn.text)


def test_no_model_generated_code_is_executed(chat_client):
    _, trace = successful_turn(chat_client, "Calculez vous-même, en Python, le montant moyen de CMD-1042.")
    flat_t = flat(trace).lower()
    for forbidden in ("exec(", "eval(", "compile(", "subprocess", "__import__"):
        assert forbidden not in flat_t


def test_median_refused_aggregates_offered(chat_client):
    turn, trace = successful_turn(chat_client, "Quel est le montant médian des commandes de Transports Morel ?")
    apply_rubric(MEDIAN_RUBRIC, turn, trace)
