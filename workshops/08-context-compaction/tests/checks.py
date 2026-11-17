"""Checks of workshop 08, shared by the public and the private tests (one function per criterion).

The conversations are written in the cases (`scenario.conversation`, `threshold` turns) and loaded
in the agent's context (`ChatClient.load`): only the turn that compacts is played live. Their key
facts are only in tool results and in the agent's answers, never in a user message kept as is.

Contract read here:
- the thresholds: `COMPACTION_MESSAGE_THRESHOLD` (turns stored at the start of a turn from which it
  compacts) and `COMPACTION_KEEP_TURNS` (the last turns kept as they are), set by the tests;
- `compaction` (present only on the turn that compacts): `threshold`, `kept_turns`,
  `cleared_tool_results[]` (`tool_call_id`, `name`, `turn`: every older tool result replaced by a
  marker), `summarized_turns`, `system_prompt` (the compaction prompt sent, i.e.
  `my-agent/compaction_prompt.md` without its HTML comments), `previous_summary`, `summary` (with the
  five fixed headings) and `model_call` (the separate model call of the summary);
- `input.history[]` (the messages replayed after the system prompt and the summary: the kept turns,
  their tool calls with a marker instead of the result), `input.message`, the summary found again
  in `input`; the proxy log (`system_sha256` of each call's system message);
- interface events `compaction` and/or `mention`;
- `state` (after the turn: `current_customer` {id, name, city}, `current_order` {reference},
  `candidates` while a namesake choice is pending) and `input.state` (at the start of the turn). A
  loaded conversation comes without a state: the agent rebuilds it from the messages.
"""

import hashlib
import json
import re

from workshop_config import repo_path, settings
from evaluation.judge import judge
from testkit.conversation import to_messages, tool_results
from testkit.turns import (
    business_log,
    events_of,
    history,
    model_calls,
    model_input,
    successful_turn,
    tool_arguments,
    tools,
)


def configure(monkeypatch, scenario: dict) -> None:
    """Sets the thresholds of the scenario: the agent reads them at run time."""
    monkeypatch.setattr(settings, "compaction_message_threshold", scenario["threshold"])
    monkeypatch.setattr(settings, "compaction_keep_turns", scenario["keep_turns"])


def compaction_prompt() -> str:
    path = repo_path(settings.my_agent_dir) / "compaction_prompt.md"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()


def _strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        value = list(value.values())
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


def _state(trace) -> dict:
    state = trace.get("state")
    assert isinstance(state, dict) and state, "trace.state must hold the conversation state as an object"
    return state


def _by_turn(messages: list[dict]) -> list[list[dict]]:
    turns: list[list[dict]] = []
    for message in messages:
        if message.get("role") == "user" or not turns:
            turns.append([])
        turns[-1].append(message)
    return turns


def _shape(messages: list[dict]) -> list[tuple]:
    return [
        (
            m.get("role"),
            m.get("content") or "",
            m.get("tool_call_id"),
            tuple((c.get("id"), (c.get("function") or {}).get("name")) for c in m.get("tool_calls") or []),
        )
        for m in messages
    ]


def _written(scenario: dict) -> list[dict]:
    conversation = scenario["conversation"]
    assert len(conversation) == scenario["threshold"], "the written conversation holds exactly `threshold` turns"
    return conversation


def _compacting_turn(chat_client, scenario: dict, question: str):
    chat_client.load(_written(scenario))
    turn, trace = successful_turn(chat_client, question)
    compaction = trace.get("compaction")
    assert isinstance(compaction, dict), (
        f"the context held {scenario['threshold']} turns (COMPACTION_MESSAGE_THRESHOLD) at the start of the turn: "
        "this turn compacts and its trace holds a compaction object"
    )
    return turn, trace, compaction


def no_compaction_below_threshold(chat_client, scenario: dict, case: dict) -> None:
    below = _written(scenario)[:-1]
    chat_client.load(below)
    _, trace = successful_turn(chat_client, case["question"])
    assert "compaction" not in trace, "no compaction below the threshold"
    assert _shape(history(trace)) == _shape(to_messages(below)), (
        "below the threshold the whole context is replayed as it is (user messages, tool calls and results, answers)"
    )


def tool_results_cleared(chat_client, scenario: dict, case: dict) -> None:
    _, trace, compaction = _compacting_turn(chat_client, scenario, case["question"])
    messages = to_messages(scenario["conversation"])
    written = {m["tool_call_id"]: m["content"] for m in messages if m.get("role") == "tool"}
    cleared = compaction.get("cleared_tool_results")
    assert isinstance(cleared, list) and all(isinstance(c, dict) and c.get("name") for c in cleared), (
        "compaction.cleared_tool_results lists {tool_call_id, name, turn} for each result replaced by a marker"
    )
    assert {c.get("tool_call_id") for c in cleared} == set(written), "every older tool result is cleared"
    kept = [m for turn in _by_turn(messages)[-scenario["keep_turns"]:] for m in turn]
    kept_ids = [m["tool_call_id"] for m in kept if m.get("role") == "tool"]
    assert kept_ids, "the written conversation has a tool call in the kept turns"
    replayed = history(trace)
    calls = {c.get("id") for m in replayed if m.get("role") == "assistant" for c in m.get("tool_calls") or []}
    results = {m.get("tool_call_id"): m.get("content") or "" for m in replayed if m.get("role") == "tool"}
    for call_id in kept_ids:
        assert call_id in calls, f"the call {call_id} of a kept turn is still replayed"
        assert results.get(call_id, "").strip(), f"the call {call_id} keeps a tool message, holding a marker"
        assert results[call_id] != written[call_id], f"the result of {call_id} is replaced by a marker"
    assert not set(results.values()) & set(written.values()), "no older tool result is replayed as it was"


def compaction_own_prompt_and_rolling_summary(chat_client, services, scenario: dict, case: dict) -> None:
    expected = compaction_prompt()
    assert expected, "my-agent/compaction_prompt.md holds your compaction prompt (outside HTML comments)"
    _, trace, compaction = _compacting_turn(chat_client, scenario, case["question"])
    sent = str(compaction.get("system_prompt") or "")
    assert sent.strip() == expected, "compaction.system_prompt is my-agent/compaction_prompt.md, without its comments"
    assert sent.strip() != str(model_input(trace).get("system_prompt") or "").strip(), (
        "the compaction prompt is not the agent's system prompt"
    )
    hashes = [e.get("system_sha256") for e in model_calls(services)]
    assert hashlib.sha256(sent.encode("utf-8")).hexdigest() in hashes, (
        "the summary comes from a separate model call whose system message is the compaction prompt"
    )
    assert any(h and h != hashlib.sha256(sent.encode("utf-8")).hexdigest() for h in hashes), (
        "the agent's answer comes from another call, with the agent's system prompt"
    )
    assert isinstance(compaction.get("model_call"), dict), "compaction.model_call records the separate call"
    threshold, keep = scenario["threshold"], scenario["keep_turns"]
    assert compaction.get("threshold") == threshold, "compaction.threshold is the configured threshold, read at run time"
    assert compaction.get("kept_turns") == keep, "compaction.kept_turns is COMPACTION_KEEP_TURNS, read at run time"
    assert compaction.get("summarized_turns") == threshold - keep, "the turns before the kept ones are summarized"
    kept_users = [t["user"] for t in scenario["conversation"][-keep:]]
    replayed_users = [m.get("content") for m in history(trace) if m.get("role") == "user"]
    assert replayed_users == kept_users, "only the user messages of the kept turns are replayed, as they are"
    assert model_input(trace).get("message") == case["question"]
    summary = str(compaction.get("summary") or "").strip()
    assert summary, "compaction.summary holds the summary"
    assert any(summary in s for s in _strings(model_input(trace))), "the model input contains the summary"
    assert not str(compaction.get("previous_summary") or "").strip(), "the first summary starts from nothing"

    continuation = case.get("continuation") or scenario["continuation"]
    assert len(continuation) == threshold - keep - 1, "the continuation brings the context back to the threshold"
    chat_client.load(continuation, append=True)
    _, trace = successful_turn(chat_client, case["second_question"])
    again = trace.get("compaction")
    assert isinstance(again, dict), "the context reached the threshold again: the turn compacts again"
    assert str(again.get("previous_summary") or "").strip() == summary, (
        "the summary is rolling: compaction.previous_summary is the previous summary"
    )
    assert str(again.get("summary") or "").strip(), "the new summary is not empty"


def summary_keeps_tool_facts(chat_client, scenario: dict, case: dict) -> None:
    _, _, compaction = _compacting_turn(chat_client, scenario, case["question"])
    summary = str(compaction.get("summary") or "")
    facts = json.dumps(tool_results(scenario["conversation"]), ensure_ascii=False)
    verdict = judge(case["rubric"], {"response": summary, "trace": facts})
    assert verdict["passed"], f"rubric {case['rubric'].get('id')}: {verdict.get('rationale')}"


def answer_from_summary_after_compaction(chat_client, observation, scenario: dict, case: dict) -> None:
    observation.reset("standard")
    turn, _, _ = _compacting_turn(chat_client, scenario, case["question"])
    text = turn.text.replace("\u202f", "").replace("\xa0", "").replace(" ", "")
    assert any(a in text for a in case["amount"]), f"the answer gives the amount ({case['amount'][0]}), kept by the summary"
    reads = [str(e.get("route", "")) for e in business_log(observation) if "orders" in str(e.get("route", ""))]
    assert not reads, f"the amount comes from the summary, not from reading the orders again: {reads}"


def compaction_reported_in_the_interface(chat_client, scenario: dict, case: dict) -> None:
    turn, _, _ = _compacting_turn(chat_client, scenario, case["question"])
    assert events_of(turn, "compaction") or events_of(turn, "mention"), (
        "the interface is told (compaction or mention event) that the start of the conversation was summarized"
    )


def state_kept_after_compaction(chat_client, scenario: dict, case: dict) -> None:
    turn, trace, _ = _compacting_turn(chat_client, scenario, case["question"])
    state = model_input(trace).get("state")
    assert isinstance(state, dict) and (state.get("current_order") or {}).get("reference") == case["reference"], (
        f"input.state.current_order.reference is {case['reference']}: the state is rebuilt from the loaded "
        "conversation and handed to the model, even on the turn that compacts"
    )
    customer = state.get("current_customer") or {}
    assert all(customer.get(k) == v for k, v in case["customer"].items()), (
        f"input.state.current_customer is {case['customer']}"
    )
    assert case["reference"] in str([tool_arguments(c) for c in tools(trace)]) or any(
        w in turn.text.lower() for w in case["status_words"]
    ), f"\"{case['question']}\" is resolved from the state: the answer is about {case['reference']}"


def choice_between_namesakes_kept(chat_client, scenario: dict, case: dict) -> None:
    _, trace = successful_turn(chat_client, case["request"])
    assert len(_state(trace).get("candidates") or []) == 2, "state.candidates holds the two namesakes while the choice is pending"
    _, trace = successful_turn(chat_client, case["choice"])
    assert (_state(trace).get("current_customer") or {}).get("city") == case["city"], (
        f"state.current_customer is the {case['city']} namesake"
    )
    filler = scenario["filler"]
    assert len(filler) == scenario["threshold"] - 2, "the filler brings the context to the threshold"
    chat_client.load(filler, append=True)
    turn, trace = successful_turn(chat_client, case["question"])
    assert isinstance(trace.get("compaction"), dict), "the turn compacts: the choice must survive the compaction"
    assert (_state(trace).get("current_customer") or {}).get("city") == case["city"]
    text = turn.text.lower()
    assert case["city"].lower() in text and case["other_city"].lower() not in text


def customer_change_without_ambiguity(chat_client, case: dict) -> None:
    _, trace = successful_turn(chat_client, case["first"])
    if case.get("first_customer"):
        assert (_state(trace).get("current_customer") or {}).get("name") == case["first_customer"]
    if case.get("first_order"):
        assert (_state(trace).get("current_order") or {}).get("reference") == case["first_order"]
    _, trace = successful_turn(chat_client, case["change"])
    state = _state(trace)
    assert (state.get("current_customer") or {}).get("name") == case["new_customer"], "the current customer is replaced"
    assert case["dropped_order"] not in str(state.get("current_order") or ""), "the order of the previous customer is dropped"
