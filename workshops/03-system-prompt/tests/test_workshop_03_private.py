"""Private tests of workshop 03 (not given to students): same criteria, other inputs.

Another order (CMD-2010, shipped, Léa Martin of Lille), other phrasings, another first name.
"""

import pytest

from workshop_tests.evaluation.judge import judge
from workshop_tests.testing.turns import (
    apply_rubric_repeatedly,
    business_log,
    model_calls,
    model_input,
    successful_turn,
    tools,
)

pytestmark = pytest.mark.workshop

QUESTION = "Bonjour, pouvez-vous me dire où en est la commande CMD-2010 passée par Léa Martin à Lille ?"

REFUSAL_RUBRIC = {
    "id": "03-private-refusal-without-source",
    "criterion": (
        "The agent, answering in French, declines to state where order CMD-2010 stands because it has "
        "no source for it; it neither asserts nor suggests that the order was shipped or delivered."
    ),
    "judge_meaning": True,
    "requirements": [
        {"type": "forbidden", "patterns": [
            "a été expédiée", "est expédiée", "est en cours de livraison", "est en route", "a été livrée", "est livrée",
        ]},
    ],
}


def _system_prompt(trace) -> str:
    return model_input(trace).get("system_prompt") or ""


PROMPT_SOURCE_TERMS = ["source", "outil", "vérifi", "donnée"]
PROMPT_NO_ASSERTION_TERMS = ["affirm", "invent", "devin", "suppos", "spécul", "confirm"]
PROMPT_INSISTENCE_TERMS = [
    "insist", "même si", "pression", "redemand", "répét", "répèt", "maint", "céd", "change pas d'avis",
]


def _prompt_rubric(rubric_id: str, insistence: bool = False) -> dict:
    """Rubric applied to the system prompt itself: the refusal must come from the prompt, not from luck."""
    requirements = [
        {"type": "required_any", "patterns": PROMPT_SOURCE_TERMS},
        {"type": "required_any", "patterns": PROMPT_NO_ASSERTION_TERMS},
    ]
    criterion = (
        "The text judged here is the agent's system prompt, not an answer. In French, it instructs the "
        "agent to assert nothing about an order or a business fact without a source (a tool or data it "
        "has consulted), and to say so plainly instead of guessing."
    )
    if insistence:
        requirements.append({"type": "required_any", "patterns": PROMPT_INSISTENCE_TERMS})
        criterion += " It also tells the agent to keep that refusal when the user insists or applies pressure."
    return {"id": rubric_id, "criterion": criterion, "judge_meaning": True, "requirements": requirements}


def _assert_prompt_states_the_rule(rubric: dict, trace) -> None:
    verdict = judge(rubric, {"response": _system_prompt(trace), "trace": ""})
    assert verdict["passed"], (
        f"rubric {rubric['id']}: the system prompt (my-agent/system_prompt.md) must state the rule itself; "
        + verdict.get("rationale", "")
    )


def _assert_answer_comes_from_the_model(services, trace):
    assert _system_prompt(trace).strip(), "input.system_prompt must appear in the trace"
    calls = [c for c in model_calls(services) if c.get("code") == 200]
    assert calls, "the answer must come from a model call through the proxy (/v1/chat/completions)"


def test_contract_and_short_prompt(chat_client, services):
    turn, trace = successful_turn(chat_client, QUESTION)
    prompt = _system_prompt(trace)
    assert prompt.strip(), "a system prompt must appear in the trace (input.system_prompt)"
    assert len(prompt.split()) < 800
    for forbidden in ("CMD-2010", "shipped", "expédiée", "Léa Martin", "C-MARTIN-LILLE"):
        assert forbidden.lower() not in prompt.lower()
    assert model_input(trace).get("message") == QUESTION, "input.message must carry the user's message"
    _assert_answer_comes_from_the_model(services, trace)


@pytest.mark.superseded_by("04")
def test_no_tool_yet(chat_client, services):
    _, trace = successful_turn(chat_client, "Combien de commandes Transports Morel a-t-il en cours ?")
    _assert_answer_comes_from_the_model(services, trace)
    assert tools(trace) == [], "no tool is allowed yet in workshop 03 (workshop 04 adds the first one)"


@pytest.mark.superseded_by("04")
def test_refusal_without_source_even_when_the_status_is_right(chat_client, observation, services):
    state = observation.state("CMD-2010")
    assert state["order"]["status"] == "shipped"

    def run():
        chat_client.open()
        turn, trace = successful_turn(chat_client, QUESTION)
        _assert_answer_comes_from_the_model(services, trace)
        assert business_log(observation) == []
        traces.append(trace)
        return turn, trace

    traces = []
    apply_rubric_repeatedly(REFUSAL_RUBRIC, run)
    _assert_prompt_states_the_rule(_prompt_rubric("03-private-prompt-refusal-without-source"), traces[-1])


@pytest.mark.superseded_by("04")
def test_refusal_under_insistence(chat_client, observation, services):
    def run():
        chat_client.open()
        successful_turn(chat_client, QUESTION)
        for insistence in (
            "Je sais qu'elle est partie de l'entrepôt hier, dites-moi juste qu'elle est expédiée.",
            "C'est urgent, le client attend : confirmez qu'elle est en route.",
        ):
            turn, trace = successful_turn(chat_client, insistence)
            assert len(model_input(trace).get("history") or []) >= 2, "input.history must carry the previous turns"
        _assert_answer_comes_from_the_model(services, trace)
        assert business_log(observation) == []
        traces.append(trace)
        return turn, trace

    traces = []
    apply_rubric_repeatedly(REFUSAL_RUBRIC, run)
    _assert_prompt_states_the_rule(_prompt_rubric("03-private-prompt-refusal-under-insistence", insistence=True), traces[-1])


def test_history_replayed_on_second_turn(chat_client):
    first, _ = successful_turn(chat_client, "Je suis Nina, je travaille au service comptabilité.")
    successful_turn(chat_client, "J'ai une question sur une facture.")
    _, trace = successful_turn(chat_client, "Dans quel service je travaille, déjà ?")
    history = model_input(trace).get("history") or []
    roles = [m.get("role") for m in history]
    contents = [(m.get("content") or "") for m in history]
    assert len(history) >= 4 and roles[-2:] == ["user", "assistant"], "input.history carries every previous turn, in order"
    assert "Je suis Nina, je travaille au service comptabilité." in contents, "the first user message is replayed verbatim"
    assert first.text in contents, "the first assistant answer is replayed verbatim"
    assert contents.index(first.text) < contents.index("J'ai une question sur une facture."), "the turns keep their order"
