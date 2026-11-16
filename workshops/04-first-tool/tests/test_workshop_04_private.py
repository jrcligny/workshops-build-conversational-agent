"""Private tests of workshop 04 (not given to students): same criteria, other inputs.

Another order (CMD-2010, shipped), another swapped reference (CMD-2001 → CMD-2010), other
excluded orders (CMD-3150 deleted, CMD-0770 rejected: hidden from customer service) and
another malformed reference.
"""

import pytest

from workshop_tests.testing.turns import model_calls, successful_turn, tool_arguments, tool_result, tool_status, tools

pytestmark = pytest.mark.workshop


def _only_call(trace) -> dict:
    calls = tools(trace)
    assert len(calls) == 1, f"exactly one tool call is expected for this question, got {len(calls)}"
    return calls[0]


def test_exact_order_lookup(chat_client, services):
    turn, trace = successful_turn(chat_client, "Pouvez-vous me dire où en est la commande CMD-2010 ?")
    call = _only_call(trace)
    assert "CMD-2010" in str(tool_arguments(call)), "the reference must be passed as a tool argument"
    assert tool_status(call) == "ok", "a found order is a result with status 'ok'"
    assert "shipped" in str(tool_result(call)), "the result carries the status read from the business application"
    assert "expédiée" in turn.text.lower(), "the answer must state the status read from the tool (expédiée)"
    assert len([c for c in model_calls(services) if c.get("code") == 200]) >= 2


def test_swapped_reference_reported(chat_client):
    turn, trace = successful_turn(chat_client, "Je cherche la commande CMD-2001, elle en est où ?")
    call = _only_call(trace)
    result = tool_result(call)
    assert tool_status(call) in {"approximate", "not_found"}, "CMD-2001 does not exist: status approximate or not_found"
    proposed = str(result.get("order") or "") + str(result.get("suggestions") or "")
    assert "CMD-2010" in proposed, "the close reference is computed by the program (result.order or result.suggestions)"
    assert "CMD-2001" in turn.text and "CMD-2010" in turn.text, "the answer names the asked and the close reference"
    assert "expédiée" not in turn.text.lower() or "?" in turn.text, "the close order is suggested, not presented as the answer"


@pytest.mark.parametrize("reference", ["CMD-3150", "CMD-0770"])
def test_excluded_order_never_returned(chat_client, reference):
    turn, trace = successful_turn(chat_client, f"Quel est le statut de la commande {reference} ?")
    call = _only_call(trace)
    assert tool_status(call) == "not_found", "an excluded order: the result status must be 'not_found'"
    result = tool_result(call)
    assert reference not in str(result.get("order") or "") + str(result.get("suggestions") or ""), (
        "an excluded order is never returned nor suggested"
    )
    assert not any(w in turn.text.lower() for w in ("supprim", "rejet")), "the agent must not reveal why the order is hidden"


def test_excluded_order_not_suggested_for_a_close_reference(chat_client):
    turn, trace = successful_turn(chat_client, "Quel est le statut de la commande CMD-0707 ?")
    call = _only_call(trace)
    result = tool_result(call)
    assert tool_status(call) in {"approximate", "not_found"}
    assert "CMD-0770" not in str(result) and "CMD-0770" not in turn.text, (
        "CMD-0770 is hidden from customer service: it is never proposed as a close reference"
    )


def test_invalid_reference_rejected_before_the_call(chat_client, observation):
    turn, trace = successful_turn(chat_client, "Donnez-moi l'état de la commande CMD-AB12' OR '1'='1 ?")
    business_calls = [e for e in observation.log() if str(e.get("route", "")).startswith("/orders")]
    assert business_calls == [], "a reference that does not match the schema (CMD-NNNN) is rejected by the program"
    statuses = [tool_status(c) for c in tools(trace)]
    assert statuses and set(statuses) == {"error"}, "the tool call is recorded with status 'error' (invalid argument)"
