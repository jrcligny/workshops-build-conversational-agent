"""End-to-end tests of workshop 16. They must fail on the empty shell."""

import pytest

from workshop_kit.testing.chat_client import ChatClient
from workshop_kit.testing.turns import flat, model_input, successful_turn

pytestmark = pytest.mark.workshop


def test_partial_result_mention_built_by_the_harness(chat_client, observation):
    observation.reset("volume")
    turn, _ = successful_turn(chat_client, "List all late orders of Transports Morel.")
    assert "mention" in turn.types, "the bounded-result mention is built by the harness, below the answer"


def test_customer_recorded_only_after_the_choice(chat_client):
    turn, trace = successful_turn(chat_client, "What are the orders of Léa Martin?")
    state = flat(trace.get("state") or model_input(trace).get("state") or "")
    # several candidates: no single current customer yet
    assert "Léa Martin" not in state or "lille" not in state.lower() or "current" not in state.lower()
    turn, trace = successful_turn(chat_client, "The one in Lille.")
    state = flat(trace.get("state") or model_input(trace).get("state") or trace)
    assert "lille" in state.lower()


def test_unconsulted_record_marked_unverified(chat_client):
    turn, trace = successful_turn(chat_client, "Are invoice FAC-9999 and order CMD-0000 paid?")
    flat_t = (turn.text + flat(trace)).lower()
    assert "mention" in turn.types or "unverified" in flat_t or "not verified" in flat_t or "not consulted" in flat_t


def test_simultaneous_conversations_isolated(services, observation):
    a = ChatClient(services["interface"])
    a.open(user_id="camille-renard", role="customer_service", organization="organization-a")
    successful_turn(a, "I am handling Martin Durand, order CMD-1042.")
    b = ChatClient(services["interface"])
    b.open(user_id="paul-buyer", role="buyer", organization="organization-a")
    turn, trace = successful_turn(b, "Who is the current customer, and which order am I following?")
    flat_t = (turn.text + flat(trace.get("state") or "") + flat(model_input(trace))).lower()
    assert "cmd-1042" not in flat_t
    assert "durand" not in flat_t
