"""Checks of workshop 03, shared by the public and the private tests (one function per criterion).

Trace contract read here: `input.system_prompt`, `input.message` (the user's message) and
`input.history` (the previous turns, `role` and `content`, replayed verbatim); `tools[]` stays
empty in this workshop. The answer comes from a model call through the proxy.

The turns that only set the scene are loaded as a written conversation (`chat_client.load`):
only the turn under test is played.
"""

from agent_testkit.evaluation.judge import judge
from agent_testkit.conversation import to_messages
from agent_testkit.expect import mentions_none, no_business_call, no_tool_called
from agent_testkit.turns import apply_rubric_repeatedly, model_calls, model_input, successful_turn

PROMPT_SOURCE_TERMS = ["source", "outil", "vérifi", "donnée"]
PROMPT_NO_ASSERTION_TERMS = ["affirm", "invent", "devin", "suppos", "spécul", "confirm"]
PROMPT_INSISTENCE_TERMS = [
    "insist", "même si", "pression", "redemand", "répét", "répèt", "maint", "céd", "change pas d'avis",
]


def system_prompt(trace) -> str:
    return model_input(trace).get("system_prompt") or ""


def prompt_rubric(rubric_id: str, insistence: bool = False) -> dict:
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
    return {
        "id": rubric_id, "criterion": criterion, "judge_meaning": True, "requirements": requirements,
        "subject": "system prompt",
    }


def assert_prompt_states_the_rule(rubric: dict, trace) -> None:
    verdict = judge(rubric, {"response": system_prompt(trace), "trace": ""})
    assert verdict["passed"], (
        f"rubric {rubric['id']}: the system prompt (my-agent/system_prompt.md) must itself forbid, in French, "
        "asserting an order or business fact without a source"
        + (" and keep that refusal when the user insists" if "insist" in rubric["criterion"] else "")
        + " (see contrat.md, « Le prompt énonce la règle »); "
        + verdict.get("rationale", "")
    )


def assert_answer_comes_from_the_model(services, trace) -> None:
    assert system_prompt(trace).strip(), "input.system_prompt must appear in the trace"
    calls = [c for c in model_calls(services) if c.get("code") == 200]
    assert calls, "the answer must come from a model call through the proxy (/v1/chat/completions)"


def contract_and_short_prompt(chat_client, services, case: dict) -> None:
    turn, trace = successful_turn(chat_client, case["question"])
    prompt = system_prompt(trace)
    assert prompt.strip(), "a system prompt must appear in the trace (input.system_prompt)"
    assert len(prompt.split()) < case["max_prompt_words"]
    mentions_none(prompt, case["forbidden_in_prompt"], "the system prompt stays short and generic")
    assert model_input(trace).get("message") == case["question"], "input.message must carry the user's message"
    assert_answer_comes_from_the_model(services, trace)


def no_tool_yet(chat_client, services, case: dict) -> None:
    _, trace = successful_turn(chat_client, case["question"])
    assert_answer_comes_from_the_model(services, trace)
    no_tool_called(trace, "no tool is allowed yet in workshop 03 (workshop 04 adds the first one)")


def refusal_without_source_even_when_the_status_is_right(chat_client, observation, services, case: dict) -> None:
    state = observation.state(case["reference"])
    assert state["order"]["status"] == case["status"]

    def run():
        chat_client.open()
        turn, trace = successful_turn(chat_client, case["question"])
        assert_answer_comes_from_the_model(services, trace)
        no_business_call(observation)
        traces.append(trace)
        return turn, trace

    traces = []
    apply_rubric_repeatedly(case["rubric"], run)
    assert_prompt_states_the_rule(prompt_rubric(case["prompt_rubric_id"]), traces[-1])


def refusal_under_insistence(chat_client, observation, services, case: dict) -> None:
    def run():
        chat_client.open()
        chat_client.load(case["conversation"])
        turn, trace = successful_turn(chat_client, case["insistence"])
        assert model_input(trace).get("history") == to_messages(case["conversation"]), (
            "input.history must carry the previous turns (question, refusal, first insistence, refusal)"
        )
        assert_answer_comes_from_the_model(services, trace)
        no_business_call(observation)
        traces.append(trace)
        return turn, trace

    traces = []
    apply_rubric_repeatedly(case["rubric"], run)
    assert_prompt_states_the_rule(prompt_rubric(case["prompt_rubric_id"], insistence=True), traces[-1])


def history_replayed(chat_client, case: dict) -> None:
    chat_client.load(case["conversation"])
    _, trace = successful_turn(chat_client, case["last"])
    history = model_input(trace).get("history") or []
    roles = [m.get("role") for m in history]
    contents = [(m.get("content") or "") for m in history]
    written = to_messages(case["conversation"])
    assert len(history) >= len(written) and roles[-2:] == ["user", "assistant"], (
        "input.history carries every previous turn, in order, and ends with the previous user and assistant messages"
    )
    expected = [m["content"] for m in written]
    positions = [contents.index(text) if text in contents else -1 for text in expected]
    assert -1 not in positions, "every previous message (user and assistant) must be replayed verbatim"
    assert positions == sorted(positions), "the turns keep their order"
