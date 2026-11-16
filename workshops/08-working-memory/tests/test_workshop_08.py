"""End-to-end tests of workshop 08. They must fail on the empty shell."""

import pytest

from workshop_kit.shell.config import settings
from workshop_kit.testing.turns import flat, model_input, successful_turn

pytestmark = pytest.mark.workshop


def _state(trace) -> str:
    return flat(trace.get("state") or trace.get("working_memory") or model_input(trace).get("state") or "")


def test_state_kept_after_compaction(chat_client):
    successful_turn(chat_client, "I am talking about the customer Martin Durand, order CMD-1042.")
    for i in range(int(settings.compaction_message_threshold) + 2):
        successful_turn(chat_client, f"All right, keep following this file ({i}).")
    turn, trace = successful_turn(chat_client, "And that one, where is it?")
    state = _state(trace)
    assert state, "the conversation state must appear in the trace, distinct from the summary"
    assert "1042" in state or "Durand" in state
    # distinct from the compaction summary
    assert trace.get("state") or trace.get("working_memory") or model_input(trace).get("state")


def test_choice_between_namesakes_kept(chat_client):
    successful_turn(chat_client, "What are the orders of Léa Martin?")
    successful_turn(chat_client, "The one in Lille, please.")
    for i in range(int(settings.compaction_message_threshold) + 2):
        successful_turn(chat_client, f"Thanks, let's stay on this file ({i}).")
    _, trace = successful_turn(chat_client, "Remind me of the current customer.")
    state = _state(trace) + flat(model_input(trace))
    assert "lille" in state.lower()
    assert "Lyon" not in state or "Lille" in state


def test_customer_change_without_ambiguity(chat_client):
    successful_turn(chat_client, "I am talking about Martin Durand, order CMD-1042.")
    turn, trace = successful_turn(chat_client, "Let's now move on to Transports Morel only.")
    state = _state(trace)
    assert "morel" in state.lower()
    assert "Durand" not in state
