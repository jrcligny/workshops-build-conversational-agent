"""End-to-end tests of workshop 16. They must fail on the empty shell.

Contract read here: interface event `mention` (data `content`), built by the program below
the answer; trace `state` (workshop 08: `current_customer`, `candidates`, `current_order`);
`tools[].result.status` and `total` / `truncated` (workshop 07).
"""

import pytest

from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.turns import events_of, successful_turn, tool_arguments, tool_status, tools

pytestmark = pytest.mark.workshop


def _mentions(turn) -> str:
    return " ".join(str(m.get("content", "")) for m in events_of(turn, "mention"))


def test_partial_result_mention_built_by_the_harness(chat_client, observation, business_client):
    observation.reset("volume")
    customer = business_client.get("/customers", params={"name": "Transports Morel"}).json()[0]
    total = business_client.get(f"/customers/{customer['id']}/orders", params={"filter": "late"}).json()["total"]
    turn, trace = successful_turn(chat_client, "Listez toutes les commandes en retard de Transports Morel.")
    assert any(c.get("result", {}).get("truncated") for c in tools(trace)), "the list is bounded by the tool"
    mention = _mentions(turn)
    assert "partiel" in mention.lower() and str(total) in mention, (
        f"a mention, built from the tool result, says the list is partial and gives the total ({total})"
    )


def test_customer_recorded_only_after_the_choice(chat_client):
    _, trace = successful_turn(chat_client, "Quelles sont les commandes de Léa Martin ?")
    state = trace.get("state") or {}
    assert len(state.get("candidates") or []) == 2, "the two namesakes are kept as candidates"
    assert not state.get("current_customer"), "no current customer is recorded before the user chooses"
    _, trace = successful_turn(chat_client, "Celle de Lille.")
    assert ((trace.get("state") or {}).get("current_customer") or {}).get("city") == "Lille"


def test_unconsulted_record_marked_unverified(chat_client):
    turn, trace = successful_turn(chat_client, "La facture FAC-9999 et la commande CMD-0000 sont-elles réglées ?")
    looked_up = {ref: [tool_status(c) for c in tools(trace) if ref in str(tool_arguments(c))] for ref in ("FAC-9999", "CMD-0000")}
    assert all(looked_up.values()), "each record is looked up in the application"
    mention = _mentions(turn)
    assert "FAC-9999" in mention and "CMD-0000" in mention, "a mention lists the records that could not be verified"
    assert all(s == "not_found" for v in looked_up.values() for s in v), "neither record exists in the application"


def test_simultaneous_conversations_isolated(services):
    a = ChatClient(services["interface"])
    a.open(user_id="camille-renard", role="customer_service", organization="organization-a")
    b = ChatClient(services["interface"])
    b.open(user_id="paul-buyer", role="buyer", organization="organization-a")
    turn_a, trace_a = successful_turn(a, "Quel est le statut de la commande CMD-1042 de Martin Durand ?")
    assert ((trace_a.get("state") or {}).get("current_order") or {}).get("reference") == "CMD-1042", (
        "conversation A records its current order"
    )
    turn_b, trace_b = successful_turn(b, "Qui est le client en cours, et quelle commande est-ce que je suis ?")
    state_b = trace_b.get("state") or {}
    assert not state_b.get("current_order") and not state_b.get("current_customer"), "conversation B has its own, empty, state"
    assert "durand" not in turn_b.text.lower() and "CMD-1042" not in turn_b.text
    turn_a, trace_a = successful_turn(a, "Et son client ?")
    assert "durand" in turn_a.text.lower(), "conversation A keeps its state while B runs"
