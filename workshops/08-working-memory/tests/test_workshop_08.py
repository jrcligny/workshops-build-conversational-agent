"""End-to-end tests of workshop 08. They must fail on the empty shell."""

import pytest

from workshop_kit.shell.config import settings
from workshop_kit.testing.turns import flat, model_input, successful_turn

pytestmark = pytest.mark.workshop


def _state(trace) -> str:
    return flat(trace.get("state") or trace.get("working_memory") or model_input(trace).get("state") or "")


def test_state_kept_after_compaction(chat_client):
    successful_turn(chat_client, "Je parle du client Martin Durand, commande CMD-1042.")
    for i in range(int(settings.compaction_message_threshold) + 2):
        successful_turn(chat_client, f"D'accord, continuez à suivre ce dossier ({i}).")
    turn, trace = successful_turn(chat_client, "Et celle-là, où en est-elle ?")
    state = _state(trace)
    assert state, "the conversation state must appear in the trace, distinct from the summary"
    assert "1042" in state or "Durand" in state
    # distinct from the compaction summary
    assert trace.get("state") or trace.get("working_memory") or model_input(trace).get("state")


def test_choice_between_namesakes_kept(chat_client):
    successful_turn(chat_client, "Quelles sont les commandes de Léa Martin ?")
    successful_turn(chat_client, "Celle de Lille, s'il vous plaît.")
    for i in range(int(settings.compaction_message_threshold) + 2):
        successful_turn(chat_client, f"Merci, restons sur ce dossier ({i}).")
    _, trace = successful_turn(chat_client, "Rappelez-moi le client en cours.")
    state = _state(trace) + flat(model_input(trace))
    assert "lille" in state.lower()
    assert "Lyon" not in state or "Lille" in state


def test_customer_change_without_ambiguity(chat_client):
    successful_turn(chat_client, "Je parle de Martin Durand, commande CMD-1042.")
    turn, trace = successful_turn(chat_client, "Passons maintenant à Transports Morel uniquement.")
    state = _state(trace)
    assert "morel" in state.lower()
    assert "Durand" not in state
