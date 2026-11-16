"""End-to-end tests of workshop 08. They must fail on the empty shell.

Trace contract read here: `state` (the conversation state after the turn, an object kept
outside the history: `current_customer` {id, name, city}, `current_order` {reference},
`candidates` while a namesake choice is pending) and `input.state` (the state sent to the
model at the start of the turn).
"""

import pytest

from workshop_kit.shell.config import settings
from workshop_tests.testing.turns import successful_turn, tool_arguments, tools

pytestmark = pytest.mark.workshop


def _state(trace) -> dict:
    state = trace.get("state")
    assert isinstance(state, dict) and state, "trace.state must hold the conversation state as an object"
    return state


def _fill_past_threshold(chat_client, text: str) -> None:
    for i in range(int(settings.compaction_message_threshold) + 2):
        successful_turn(chat_client, f"{text} ({i}).")


def test_state_kept_after_compaction(chat_client):
    successful_turn(chat_client, "Quel est le statut de la commande CMD-1042 de Martin Durand ?")
    _fill_past_threshold(chat_client, "D'accord, continuez à suivre ce dossier")
    turn, trace = successful_turn(chat_client, "Et celle-là, où en est-elle ?")
    state = trace.get("input", {}).get("state")
    assert isinstance(state, dict) and (state.get("current_order") or {}).get("reference") == "CMD-1042", (
        "input.state.current_order.reference is CMD-1042 even after the history was summarized"
    )
    assert (state.get("current_customer") or {}).get("name") == "Martin Durand"
    assert "CMD-1042" in str([tool_arguments(c) for c in tools(trace)]) or "livrée" in turn.text.lower(), (
        "\"celle-là\" is resolved from the state: the answer is about CMD-1042"
    )


def test_choice_between_namesakes_kept(chat_client):
    _, trace = successful_turn(chat_client, "Quelles sont les commandes de Léa Martin ?")
    assert len(_state(trace).get("candidates") or []) == 2, "state.candidates holds the two namesakes while the choice is pending"
    _, trace = successful_turn(chat_client, "Celle de Lille, s'il vous plaît.")
    assert (_state(trace).get("current_customer") or {}).get("city") == "Lille", "state.current_customer is the Lille namesake"
    _fill_past_threshold(chat_client, "Merci, restons sur ce dossier")
    turn, trace = successful_turn(chat_client, "Rappelez-moi le client en cours.")
    assert (_state(trace).get("current_customer") or {}).get("city") == "Lille"
    assert "lille" in turn.text.lower() and "lyon" not in turn.text.lower()


def test_customer_change_without_ambiguity(chat_client):
    _, trace = successful_turn(chat_client, "Quel est le statut de la commande CMD-1042 de Martin Durand ?")
    assert (_state(trace).get("current_customer") or {}).get("name") == "Martin Durand"
    _, trace = successful_turn(chat_client, "Passons maintenant à Transports Morel : combien a-t-il de commandes ?")
    state = _state(trace)
    assert (state.get("current_customer") or {}).get("name") == "Transports Morel", "the current customer is replaced"
    assert "CMD-1042" not in str(state.get("current_order") or ""), "the order of the previous customer is dropped"
