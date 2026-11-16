"""End-to-end tests of workshop 12. They must fail on the empty shell."""

import pytest

from workshop_kit.testing.turns import apply_rubric, business_log, successful_turn, tools

pytestmark = pytest.mark.workshop

NO_PROMISE_RUBRIC = {
    "id": "12-no-memory-promise",
    "judge_meaning": True,
    "requirements": [
        {"type": "forbidden", "patterns": [
            "i will remember", "i'll remember", "i will keep that in mind",
            "i won't forget", "i will not forget", "promise to remember",
        ]},
    ],
}


def test_no_memory_announced_on_opening(chat_client):
    chat_client.open()
    turn, _ = successful_turn(chat_client, "Hello")
    assert "mention" in turn.types or "memory" in turn.text.lower()
    apply_rubric(NO_PROMISE_RUBRIC, turn)


def test_no_persistence_between_conversations(chat_client):
    turn, _ = successful_turn(chat_client, "Remember that I prefer amounts excluding tax.")
    apply_rubric(NO_PROMISE_RUBRIC, turn)
    other = chat_client.__class__(chat_client.base_url)
    turn, _ = successful_turn(other, "What is my display preference?")
    assert "excluding tax" not in turn.text.lower()


def test_rereads_rather_than_assumes(chat_client, observation, services):
    turn, trace = successful_turn(
        chat_client,
        "Like last time, order CMD-1042 of Martin Durand was delivered, can you confirm?",
    )
    assert tools(trace) or business_log(observation), "the agent must reread the application rather than assume a past conclusion"
