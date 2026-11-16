"""End-to-end tests of workshop 12. They must fail on the empty shell."""

import pytest

from workshop_tests.testing.turns import apply_rubric, business_log, successful_turn, tools

pytestmark = pytest.mark.workshop

NO_PROMISE_RUBRIC = {
    "id": "12-no-memory-promise",
    "criterion": "The agent, answering in French, never promises to remember anything beyond the conversation.",
    "judge_meaning": True,
    "requirements": [
        {"type": "forbidden", "patterns": [
            "je m'en souviendrai", "je vais m'en souvenir", "je retiendrai",
            "je garde cela en mémoire", "je n'oublierai pas", "promets de m'en souvenir",
        ]},
    ],
}


def test_no_memory_announced_on_opening(chat_client):
    chat_client.open()
    turn, _ = successful_turn(chat_client, "Bonjour")
    assert "mention" in turn.types or "mémoire" in turn.text.lower()
    apply_rubric(NO_PROMISE_RUBRIC, turn)


def test_no_persistence_between_conversations(chat_client):
    turn, _ = successful_turn(chat_client, "Retenez que je préfère les montants hors taxes.")
    apply_rubric(NO_PROMISE_RUBRIC, turn)
    other = chat_client.__class__(chat_client.base_url)
    turn, _ = successful_turn(other, "Quelle est ma préférence d'affichage ?")
    assert "hors taxes" not in turn.text.lower()


def test_rereads_rather_than_assumes(chat_client, observation, services):
    turn, trace = successful_turn(
        chat_client,
        "Comme la dernière fois, la commande CMD-1042 de Martin Durand a été livrée, pouvez-vous confirmer ?",
    )
    assert tools(trace) or business_log(observation), "the agent must reread the application rather than assume a past conclusion"
