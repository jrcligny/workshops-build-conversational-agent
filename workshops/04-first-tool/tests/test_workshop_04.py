"""End-to-end tests of workshop 04. They must fail on the empty shell.

Trace contract read here: `tools[]` entries with `name`, `arguments` (dict) and `result`
whose `status` is ok (or found) | approximate | not_found | error | denied. A close reference
computed by the program is returned either as `status: approximate` with `order`, or as
`status: not_found` with `suggestions`; excluded orders are never returned.
"""

import pytest

from workshop_tests.testing.turns import model_calls, successful_turn, tool_arguments, tool_result, tool_status, tools

pytestmark = pytest.mark.workshop


def _only_call(trace) -> dict:
    calls = tools(trace)
    assert len(calls) == 1, f"exactly one tool call is expected for this question, got {len(calls)}"
    return calls[0]


def test_exact_order_lookup(chat_client, services):
    turn, trace = successful_turn(chat_client, "Quel est le statut de la commande CMD-1042 de Martin Durand ?")
    call = _only_call(trace)
    assert "CMD-1042" in str(tool_arguments(call)), "the reference must be passed as a tool argument"
    assert tool_status(call) == "ok", "a found order is a result with status 'ok'"
    assert "delivered" in str(tool_result(call)), "the result carries the status read from the business application"
    assert "livrée" in turn.text.lower(), "the answer must state the status read from the tool (livrée)"
    assert len([c for c in model_calls(services) if c.get("code") == 200]) >= 2, (
        "a question answered through a tool takes at least two model calls (request, then answer)"
    )


def test_swapped_reference_reported(chat_client):
    turn, trace = successful_turn(chat_client, "Quel est le statut de la commande CMD-1402 ?")
    call = _only_call(trace)
    result = tool_result(call)
    assert tool_status(call) in {"approximate", "not_found"}, "CMD-1402 does not exist: status approximate or not_found"
    proposed = str(result.get("order") or "") + str(result.get("suggestions") or "")
    assert "CMD-1042" in proposed, "the close reference is computed by the program (result.order or result.suggestions)"
    assert "CMD-1402" in turn.text and "CMD-1042" in turn.text, "the answer names the asked and the close reference"
    assert "livrée" not in turn.text.lower() or "?" in turn.text, "the close order is suggested, not presented as the answer"


def test_deleted_order_never_suggested(chat_client):
    turn, trace = successful_turn(chat_client, "Quel est le statut de la commande CMD-0881 ?")
    call = _only_call(trace)
    assert tool_status(call) == "not_found", "a deleted order is excluded: the result status must be 'not_found'"
    result = tool_result(call)
    assert not result.get("order") and not result.get("suggestions"), "an excluded order is never returned nor suggested"
    assert "supprim" not in turn.text.lower(), "the agent must not reveal that the order exists but was deleted"


def test_invalid_reference_rejected_before_the_call(chat_client, observation):
    turn, trace = successful_turn(chat_client, "Quel est le statut de la commande 1042;DROP ?")
    business_calls = [e for e in observation.log() if str(e.get("route", "")).startswith("/orders")]
    assert business_calls == [], "a reference that does not match the schema (CMD-NNNN) is rejected by the program"
    statuses = [tool_status(c) for c in tools(trace)]
    assert statuses and set(statuses) == {"error"}, "the tool call is recorded with status 'error' (invalid argument)"
