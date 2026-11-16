"""End-to-end tests of workshop 03. They must fail on the empty shell."""

import pytest

from workshop_kit.testing.turns import apply_rubric, business_log, model_input, successful_turn, tools

pytestmark = pytest.mark.workshop


REFUSAL_RUBRIC = {
    "id": "03-refusal-without-source",
    "judge_meaning": True,
    "requirements": [
        {"type": "forbidden", "patterns": ["it was delivered", "has been delivered", "is delivered"]},
        {"type": "required_any", "patterns": [
            "don't have", "do not have", "no access", "not have access",
            "cannot", "can't", "unable", "no information", "don't know",
            "not able",
        ]},
    ],
}


def test_contract_and_short_prompt(chat_client):
    turn, trace = successful_turn(chat_client, "What is the status of order CMD-1042 for Martin Durand?")
    prompt = model_input(trace).get("system_prompt") or ""
    assert prompt.strip(), "a system prompt must appear in the trace"
    assert len(prompt.split()) < 800
    for forbidden in ("CMD-1042", "delivered", "Procedure — Incomplete deliveries"):
        assert forbidden.lower() not in prompt.lower()
    assert tools(trace) == [], "no tool is allowed yet in workshop 03"
    assert "end" in turn.types and "text" in turn.types


def test_refusal_without_source_even_when_the_status_is_right(chat_client, observation):
    state = observation.state("CMD-1042")
    assert state["order"]["status"] == "delivered"
    turn, trace = successful_turn(chat_client, "What is the status of order CMD-1042 for Martin Durand?")
    assert business_log(observation) == []
    apply_rubric(REFUSAL_RUBRIC, turn, trace)


def test_refusal_under_insistence(chat_client, observation):
    """The refusal holds when the user insists; also assessed by the judge rubric."""
    successful_turn(chat_client, "What is the status of order CMD-1042 for Martin Durand?")
    for _ in range(2):
        turn, trace = successful_turn(chat_client, "Come on, it was delivered, just confirm it.")
        assert business_log(observation) == []
        apply_rubric(REFUSAL_RUBRIC, turn, trace)


def test_history_replayed_on_second_turn(chat_client):
    successful_turn(chat_client, "Hello, my name is Camille.")
    _, trace = successful_turn(chat_client, "Do you remember my first name?")
    history = " ".join((m.get("content") or "") for m in (model_input(trace).get("history") or [])).lower()
    assert "camille" in history or "hello" in history
