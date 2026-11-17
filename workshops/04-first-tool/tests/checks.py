"""Checks of workshop 04, shared by the public and the private tests (one function per criterion).

Trace contract read here: `tools[]` entries with `name`, `arguments` (dict) and `result`
whose `status` is ok (or found) | approximate | not_found | error | denied. A close reference
computed by the program is returned either as `status: approximate` with `order`, or as
`status: not_found` with `suggestions`; excluded orders are never returned.
"""

from workshop_tests.testing.turns import history, model_calls, successful_turn, tool_arguments, tool_result, tool_status, tools


def only_call(trace) -> dict:
    calls = tools(trace)
    assert len(calls) == 1, f"exactly one tool call is expected for this question, got {len(calls)}"
    return calls[0]


def proposed(result: dict) -> str:
    return str(result.get("order") or "") + str(result.get("suggestions") or "")


def exact_order_lookup(chat_client, services, case: dict) -> None:
    turn, trace = successful_turn(chat_client, case["question"])
    call = only_call(trace)
    assert case["reference"] in str(tool_arguments(call)), "the reference must be passed as a tool argument"
    assert tool_status(call) == "ok", "a found order is a result with status 'ok'"
    assert case["status"] in str(tool_result(call)), "the result carries the status read from the business application"
    assert case["answer_status"] in turn.text.lower(), (
        f"the answer must state the status read from the tool ({case['answer_status']})"
    )
    assert len([c for c in model_calls(services) if c.get("code") == 200]) >= 2, (
        "a question answered through a tool takes at least two model calls (request, then answer)"
    )


def swapped_reference_reported(chat_client, case: dict) -> None:
    turn, trace = successful_turn(chat_client, case["question"])
    call = only_call(trace)
    asked, close = case["asked"], case["close"]
    assert tool_status(call) in {"approximate", "not_found"}, f"{asked} does not exist: status approximate or not_found"
    assert close in proposed(tool_result(call)), "the close reference is computed by the program (result.order or result.suggestions)"
    assert asked in turn.text and close in turn.text, "the answer names the asked and the close reference"
    assert case["close_status"] not in turn.text.lower() or "?" in turn.text, (
        "the close order is suggested, not presented as the answer"
    )


def excluded_order_never_returned(chat_client, case: dict) -> None:
    turn, trace = successful_turn(chat_client, case["question"])
    call = only_call(trace)
    assert tool_status(call) == "not_found", "an excluded order: the result status must be 'not_found'"
    result = tool_result(call)
    if case.get("nothing_proposed"):
        assert not result.get("order") and not result.get("suggestions"), "an excluded order is never returned nor suggested"
    else:
        assert case["reference"] not in proposed(result), "an excluded order is never returned nor suggested"
    assert not any(w in turn.text.lower() for w in case["hidden_reasons"]), "the agent must not reveal why the order is hidden"


def invalid_reference_rejected_before_the_call(chat_client, observation, case: dict) -> None:
    _, trace = successful_turn(chat_client, case["question"])
    business_calls = [e for e in observation.log() if str(e.get("route", "")).startswith("/orders")]
    assert business_calls == [], "a reference that does not match the schema (CMD-NNNN) is rejected by the program"
    statuses = [tool_status(c) for c in tools(trace)]
    assert statuses and set(statuses) == {"error"}, "the tool call is recorded with status 'error' (invalid argument)"


def tool_result_replayed_next_turn(chat_client, case: dict) -> None:
    successful_turn(chat_client, case["question"])
    _, trace = successful_turn(chat_client, case["follow_up"])
    replayed = history(trace)
    calls = [m for m in replayed if m.get("role") == "assistant" and m.get("tool_calls")]
    results = [m for m in replayed if m.get("role") == "tool"]
    assert calls, "input.history replays the assistant message carrying the tool call of the previous turn"
    ids = {c.get("id") for m in calls for c in m["tool_calls"]}
    assert results and all(m.get("tool_call_id") in ids for m in results), (
        "input.history replays the tool result, linked to its call by tool_call_id"
    )
    assert any(case["status"] in str(m.get("content")) for m in results), (
        "the replayed tool result carries the status read from the business application"
    )
