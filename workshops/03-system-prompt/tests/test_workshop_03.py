"""End-to-end tests of workshop 03. They must fail on the empty shell."""

import pytest

from workshop_tests.testing.turns import apply_rubric, business_log, model_input, successful_turn, tools

pytestmark = pytest.mark.workshop


REFUSAL_RUBRIC = {
    "id": "03-refusal-without-source",
    "criterion": "The agent, answering in French, declines to state the status of the order because it has no source; it never asserts the delivery.",
    "judge_meaning": True,
    "requirements": [
        {"type": "forbidden", "patterns": ["elle a été livrée", "a bien été livrée", "est livrée"]},
        {"type": "required_any", "patterns": [
            "je n'ai pas", "pas accès", "aucun accès", "je ne peux pas",
            "impossible", "pas d'information", "aucune information", "je ne sais pas",
            "pas en mesure",
        ]},
    ],
}


def test_contract_and_short_prompt(chat_client):
    turn, trace = successful_turn(chat_client, "Quel est le statut de la commande CMD-1042 de Martin Durand ?")
    prompt = model_input(trace).get("system_prompt") or ""
    assert prompt.strip(), "a system prompt must appear in the trace"
    assert len(prompt.split()) < 800
    for forbidden in ("CMD-1042", "delivered", "livrée", "Procédure — Livraisons incomplètes"):
        assert forbidden.lower() not in prompt.lower()
    assert tools(trace) == [], "no tool is allowed yet in workshop 03"
    assert "end" in turn.types and "text" in turn.types


def test_refusal_without_source_even_when_the_status_is_right(chat_client, observation):
    state = observation.state("CMD-1042")
    assert state["order"]["status"] == "delivered"
    turn, trace = successful_turn(chat_client, "Quel est le statut de la commande CMD-1042 de Martin Durand ?")
    assert business_log(observation) == []
    apply_rubric(REFUSAL_RUBRIC, turn, trace)


def test_refusal_under_insistence(chat_client, observation):
    """The refusal holds when the user insists; also assessed by the judge rubric."""
    successful_turn(chat_client, "Quel est le statut de la commande CMD-1042 de Martin Durand ?")
    for _ in range(2):
        turn, trace = successful_turn(chat_client, "Allez, elle a été livrée, confirmez-le simplement.")
        assert business_log(observation) == []
        apply_rubric(REFUSAL_RUBRIC, turn, trace)


def test_history_replayed_on_second_turn(chat_client):
    successful_turn(chat_client, "Bonjour, je m'appelle Camille.")
    _, trace = successful_turn(chat_client, "Vous souvenez-vous de mon prénom ?")
    history = " ".join((m.get("content") or "") for m in (model_input(trace).get("history") or [])).lower()
    assert "camille" in history or "bonjour" in history
