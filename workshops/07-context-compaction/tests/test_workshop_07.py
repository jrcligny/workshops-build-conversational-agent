"""End-to-end tests of workshop 07. They must fail on the empty shell."""

import pytest

from workshop_kit.shell.config import settings
from workshop_kit.testing.turns import apply_rubric, flat, model_input, successful_turn, tools

pytestmark = pytest.mark.workshop


PARTIAL_RUBRIC = {
    "id": "07-partial-result-announced",
    "judge_meaning": True,
    "requirements": [
        {"type": "required_any", "patterns": ["part of", "partial", "excerpt", "limited", "limit", "total"]},
    ],
}

INITIAL_REQUEST = "I am handling the file of Martin Durand, order CMD-1042, delivered orders only."


def _compaction(trace) -> dict | None:
    if isinstance(trace.get("compaction"), dict):
        return trace["compaction"]
    if isinstance(model_input(trace).get("compaction"), dict):
        return model_input(trace)["compaction"]
    for event in trace.get("events") or []:
        kind = event.get("type") if isinstance(event, dict) else (event[0] if isinstance(event, (list, tuple)) else "")
        if str(kind) == "compaction":
            return event if isinstance(event, dict) else {"type": "compaction"}
    if "compaction" in flat(trace).lower():
        return {"present": True}
    return None


def test_bounded_list_and_declared_total(chat_client, observation):
    observation.reset("volume")
    turn, trace = successful_turn(
        chat_client,
        "What are the late orders of Transports Morel, and how many are there?",
    )
    assert tools(trace)
    flat_tools = flat(tools(trace)).lower()
    assert "total" in flat_tools or "total" in turn.text.lower()
    apply_rubric(PARTIAL_RUBRIC, turn, trace)
    # context size recorded at each cycle
    assert "size" in flat(trace).lower() or "tokens" in flat(trace).lower() or trace.get("context") or model_input(trace).get("size")


def test_count_mode(chat_client, observation):
    observation.reset("volume")
    turn, trace = successful_turn(
        chat_client,
        "How many late orders does Transports Morel have? I only want the number, not the lines.",
    )
    flat_tools = flat(tools(trace)).lower()
    assert "count" in flat_tools or "total" in flat_tools or "how many" in turn.text.lower() or any(ch.isdigit() for ch in turn.text)


def test_cap_reached_total_is_a_minimum(chat_client, observation):
    observation.reset("volume")
    turn, trace = successful_turn(chat_client, "List all late orders of Transports Morel, I want the exact total.")
    flat_all = (turn.text + flat(tools(trace))).lower()
    assert "minimum" in flat_all or "at least" in flat_all or "lower bound" in flat_all or "cap" in flat_all or "partial" in flat_all


def test_no_compaction_below_threshold(chat_client):
    _, trace = successful_turn(chat_client, INITIAL_REQUEST)
    _, trace = successful_turn(chat_client, "Can you just confirm the current customer?")
    assert _compaction(trace) is None
    assert "compaction" not in flat(trace).lower()


def test_compaction_above_threshold_keeps_user_messages(chat_client):
    user_messages = [INITIAL_REQUEST]
    _, trace = successful_turn(chat_client, INITIAL_REQUEST)
    threshold = int(settings.compaction_message_threshold)
    for i in range(threshold + 2):
        msg = f"Detail number {i}: I only want the delivered orders of CMD-1042."
        user_messages.append(msg)
        turn, trace = successful_turn(chat_client, msg)
    event = _compaction(trace)
    assert event, "the trace must contain the compaction event"
    input_content = flat(model_input(trace))
    assert INITIAL_REQUEST in input_content or "CMD-1042" in input_content
    # user messages are kept verbatim; only answers and tool results are summarized
    for msg in user_messages:
        assert msg in input_content, f"user message expected verbatim in the model input: {msg!r}"
    assert "summary" in flat(trace).lower() or event.get("summary")


def test_compaction_reported_in_the_interface(chat_client):
    successful_turn(chat_client, INITIAL_REQUEST)
    turn = None
    for i in range(int(settings.compaction_message_threshold) + 2):
        turn, _ = successful_turn(chat_client, f"Next step on the Martin Durand file CMD-1042 ({i}).")
    reported = "compaction" in turn.types or any(
        ev[0] in {"compaction", "mention"} and ("summar" in str(ev[1]).lower() or ev[0] == "compaction")
        for ev in turn.events
    )
    assert reported, "the interface must report that the older part of the conversation was summarized"
