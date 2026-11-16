"""End-to-end tests of workshop 03. They must fail on the empty shell."""

import pytest

from workshop_tests.testing.turns import (
    apply_rubric_repeatedly,
    business_log,
    model_calls,
    model_input,
    successful_turn,
    tools,
)

pytestmark = pytest.mark.workshop

QUESTION = "Quel est le statut de la commande CMD-1042 de Martin Durand ?"

REFUSAL_RUBRIC = {
    "id": "03-refusal-without-source",
    "criterion": (
        "The agent, answering in French, declines to state the status of order CMD-1042 because it has "
        "no source for it; it neither asserts nor suggests that the order was delivered."
    ),
    "judge_meaning": True,
    "requirements": [
        {"type": "forbidden", "patterns": ["elle a été livrée", "a bien été livrée", "est livrée", "a été livrée"]},
    ],
}


def _system_prompt(trace) -> str:
    return model_input(trace).get("system_prompt") or ""


def _assert_answer_comes_from_the_model(services, trace):
    assert _system_prompt(trace).strip(), "input.system_prompt must appear in the trace"
    calls = [c for c in model_calls(services) if c.get("code") == 200]
    assert calls, "the answer must come from a model call through the proxy (/v1/chat/completions)"


def test_contract_and_short_prompt(chat_client, services):
    turn, trace = successful_turn(chat_client, QUESTION)
    prompt = _system_prompt(trace)
    assert prompt.strip(), "a system prompt must appear in the trace (input.system_prompt)"
    assert len(prompt.split()) < 800
    for forbidden in ("CMD-1042", "delivered", "livrée", "Procédure — Livraisons incomplètes"):
        assert forbidden.lower() not in prompt.lower()
    assert model_input(trace).get("message") == QUESTION, "input.message must carry the user's message"
    _assert_answer_comes_from_the_model(services, trace)


@pytest.mark.superseded_by("04")
def test_no_tool_yet(chat_client, services):
    _, trace = successful_turn(chat_client, QUESTION)
    _assert_answer_comes_from_the_model(services, trace)
    assert tools(trace) == [], "no tool is allowed yet in workshop 03 (workshop 04 adds the first one)"


@pytest.mark.superseded_by("04")
def test_refusal_without_source_even_when_the_status_is_right(chat_client, observation, services):
    state = observation.state("CMD-1042")
    assert state["order"]["status"] == "delivered"

    def run():
        chat_client.open()
        turn, trace = successful_turn(chat_client, QUESTION)
        _assert_answer_comes_from_the_model(services, trace)
        assert business_log(observation) == []
        return turn, trace

    apply_rubric_repeatedly(REFUSAL_RUBRIC, run)


@pytest.mark.superseded_by("04")
def test_refusal_under_insistence(chat_client, observation, services):
    """The refusal holds when the user insists, over two insisting turns."""

    def run():
        chat_client.open()
        successful_turn(chat_client, QUESTION)
        for _ in range(2):
            turn, trace = successful_turn(chat_client, "Allez, elle a été livrée, confirmez-le simplement.")
            assert len(model_input(trace).get("history") or []) >= 2, "input.history must carry the previous turns"
        _assert_answer_comes_from_the_model(services, trace)
        assert business_log(observation) == []
        return turn, trace

    apply_rubric_repeatedly(REFUSAL_RUBRIC, run)


def test_history_replayed_on_second_turn(chat_client):
    first, _ = successful_turn(chat_client, "Bonjour, je m'appelle Camille.")
    _, trace = successful_turn(chat_client, "Vous souvenez-vous de mon prénom ?")
    history = model_input(trace).get("history") or []
    roles = [m.get("role") for m in history]
    contents = [(m.get("content") or "") for m in history]
    assert roles[-2:] == ["user", "assistant"], "input.history must end with the previous user and assistant messages"
    assert "Bonjour, je m'appelle Camille." in contents, "the previous user message must be replayed verbatim"
    assert first.text in contents, "the previous assistant answer must be replayed verbatim"
