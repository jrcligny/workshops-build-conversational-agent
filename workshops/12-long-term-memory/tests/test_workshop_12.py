"""End-to-end tests of workshop 12. They must fail on the empty shell.

Contract read here: interface event `mention` at the first turn of a conversation (its
`content` says the agent keeps no memory between conversations); business call log; the
answer text.
"""

import pytest

from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.turns import apply_rubric_repeatedly, business_log, events_of, successful_turn, tools

pytestmark = pytest.mark.workshop

NO_PROMISE_RUBRIC = {
    "id": "12-no-memory-promise",
    "criterion": "The agent never promises to remember anything beyond the current conversation.",
    "judge_meaning": True,
    "requirements": [
        {"type": "forbidden", "patterns": [
            "je m'en souviendrai", "je vais m'en souvenir", "je retiendrai", "je garde cela en mémoire",
            "je n'oublierai pas", "la prochaine fois", "pour vos prochaines conversations",
        ]},
    ],
}

PREFERENCE = "Retenez que je préfère les montants hors taxes."


def test_no_memory_announced_on_opening(chat_client):
    chat_client.open()
    turn, _ = successful_turn(chat_client, "Bonjour")
    mentions = [str(m.get("content", "")).lower() for m in events_of(turn, "mention")]
    assert any("mémoire" in m for m in mentions), "the first turn carries a mention: no memory between conversations"
    chat_client_turn, _ = successful_turn(chat_client, "Et ensuite ?")
    assert not any("mémoire" in str(m.get("content", "")).lower() for m in events_of(chat_client_turn, "mention")), (
        "the mention is given once, at the opening"
    )


def test_no_persistence_between_conversations(services):
    def run():
        client = ChatClient(services["interface"])
        client.open()
        turn, trace = successful_turn(client, PREFERENCE)
        recall, _ = successful_turn(client, "Quelle est ma préférence d'affichage des montants ?")
        assert "hors taxe" in recall.text.lower(), "within the conversation, the preference is used"
        return turn, trace

    apply_rubric_repeatedly(NO_PROMISE_RUBRIC, run)
    other = ChatClient(services["interface"])
    other.open()
    turn, _ = successful_turn(other, "Quelle est ma préférence d'affichage des montants ?")
    assert "hors taxe" not in turn.text.lower(), "a new conversation starts with no memory of the previous one"


def test_rereads_rather_than_assumes(chat_client, observation):
    turn, trace = successful_turn(
        chat_client,
        "Comme la dernière fois, la commande CMD-1042 de Martin Durand est encore en préparation, vous confirmez ?",
    )
    reads = [e for e in business_log(observation) if e.get("route") == "/orders/CMD-1042" and e.get("code") == 200]
    assert tools(trace) and reads, "the agent rereads the order in the application rather than relying on a past conclusion"
    assert "livrée" in turn.text.lower(), "the answer corrects the user's assumption with the status read now (livrée)"
