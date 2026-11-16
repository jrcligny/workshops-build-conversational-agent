"""End-to-end tests of workshop 04. They must fail on the empty shell."""

import pytest

from workshop_kit.testing.turns import successful_turn, tools

pytestmark = pytest.mark.workshop


def _tool_statuses(trace) -> list[str]:
    values = []
    for call in tools(trace):
        result = call.get("result") or call.get("output") or call
        values.append(str(result.get("status") or result).lower())
    return values


def test_exact_order_lookup(chat_client):
    turn, trace = successful_turn(chat_client, "Quel est le statut de la commande CMD-1042 de Martin Durand ?")
    assert any("order" in str(t).lower() for t in tools(trace))
    assert "livr" in turn.text.lower()
    assert len(tools(trace)) <= 1, "at most one tool call per message"
    statuses = _tool_statuses(trace)
    assert any("ok" in s or "success" in s or "found" in s for s in statuses)


def test_swapped_reference_reported(chat_client):
    turn, trace = successful_turn(chat_client, "Quel est le statut de la commande CMD-1402 ?")
    assert "1042" in turn.text
    text = turn.text.lower()
    assert "1402" in text or "différ" in text or "proche" in text or "voulez-vous dire" in text or "approxim" in text
    assert tools(trace)
    assert len(tools(trace)) <= 1


def test_deleted_order_never_suggested(chat_client):
    turn, trace = successful_turn(chat_client, "Quel est le statut de la commande CMD-0881 ?")
    text = turn.text.lower()
    assert "0881" not in text or (("introuvable" in text or "aucune" in text or " pas " in text) and "suggér" not in text)
    # neither a suggestion of an excluded order nor a presentation as found
    for call in tools(trace):
        flat_call = str(call).lower()
        if "0881" in flat_call:
            assert "exclu" in flat_call or "absent" in flat_call or "not found" in flat_call or "deleted" in flat_call
    statuses = _tool_statuses(trace)
    assert any(
        "absent" in s or "error" in s or "exclu" in s or "not_found" in s or "not found" in s or "none" in s or "empty" in s
        for s in statuses
    ) or "introuvable" in text or "aucune" in text or " pas " in text
