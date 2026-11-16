"""Private tests of workshop 12 (not given to students): same criteria, other inputs.

Another user and topic (paul-buyer, answer_format = table), other users that must not see it
(camille-renard, omar-buyer-b), forgetting one topic only, other data that must not be kept
(IBAN, customer name) and another order to reread (CMD-2010).
"""

import os
from datetime import datetime
from pathlib import Path

import pytest

from agent_gateway.chat_app import reset_conversations
from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.turns import business_log, events_of, model_input, successful_turn, tools

pytestmark = pytest.mark.workshop

PAUL = {"user_id": "paul-buyer", "role": "buyer", "organization": "organization-a"}
CAMILLE = {"user_id": "camille-renard", "role": "customer_service", "organization": "organization-a"}
OMAR = {"user_id": "omar-buyer-b", "role": "buyer", "organization": "organization-b"}

PREFERENCE = "À l'avenir, présentez-moi toujours vos réponses sous forme de tableau, s'il vous plaît."
ASK = "Sous quelle forme est-ce que j'aime recevoir vos réponses ?"
TOPICS = {"amount_display": {"excluding_tax", "including_tax"}, "answer_format": {"table", "text"}}


def _memory(trace) -> dict:
    memory = trace.get("memory")
    assert isinstance(memory, dict), "trace.memory reports the memory of the turn"
    for key in ("loaded", "written", "deleted"):
        assert isinstance(memory.get(key, []), list), f"trace.memory.{key} is a list"
    return memory


def _entries(trace, key: str, topic: str) -> list[dict]:
    return [e for e in _memory(trace).get(key, []) if e.get("topic") == topic]


def _stored_text() -> str:
    root = Path(os.environ["MEMORY_DIR"])
    return "".join(p.read_text(encoding="utf-8", errors="ignore") for p in root.rglob("*") if p.is_file())


def _conversation(services, user: dict) -> ChatClient:
    client = ChatClient(services["interface"])
    client.open(**user)
    return client


def _remember_table(services):
    client = _conversation(services, PAUL)
    turn, trace = successful_turn(client, PREFERENCE)
    written = _entries(trace, "written", "answer_format")
    assert written and written[-1].get("value") == "table", "memory.written: answer_format = table"
    return turn, written[-1]


def test_preference_recalled_in_a_new_conversation(services, reset_state):
    turn, entry = _remember_table(services)
    assert entry.get("origin") == "user"
    assert entry.get("user") == "paul-buyer" and entry.get("organization") == "organization-a"
    datetime.fromisoformat(str(entry.get("recorded_at")))
    shown = [e for e in events_of(turn, "memory") if e.get("action") == "written"]
    assert shown and shown[-1].get("topic") == "answer_format", "the interface shows what was just recorded (event memory)"
    assert "table" in _stored_text()

    reset_conversations()
    client = _conversation(services, PAUL)
    recall, trace = successful_turn(client, ASK)
    loaded = _entries(trace, "loaded", "answer_format")
    assert loaded and loaded[-1].get("value") == "table", "memory.loaded: the preference is put back at the start"
    assert "tableau" in recall.text.lower() or "|" in recall.text


def test_memory_partitioned_by_user_and_organization(services, reset_state):
    _remember_table(services)
    for user in (CAMILLE, OMAR):
        client = _conversation(services, user)
        _, trace = successful_turn(client, ASK)
        assert _memory(trace).get("loaded") == [], f"memory.loaded is empty for {user['user_id']}"


def test_forget_one_topic_only(services, reset_state):
    client = _conversation(services, PAUL)
    successful_turn(client, PREFERENCE)
    _, trace = successful_turn(client, "Et retenez aussi que je veux les montants toutes taxes comprises.")
    assert [e for e in _entries(trace, "written", "amount_display") if e.get("value") == "including_tax"]

    client = _conversation(services, PAUL)
    _, trace = successful_turn(client, "Oubliez seulement ma préférence de format de réponse, gardez le reste.")
    deleted = _memory(trace).get("deleted") or []
    assert [e.get("topic") for e in deleted] == ["answer_format"], "only the named topic is forgotten"

    client = _conversation(services, PAUL)
    _, trace = successful_turn(client, "Que savez-vous de mes préférences ?")
    loaded = _memory(trace).get("loaded") or []
    assert [(e.get("topic"), e.get("value")) for e in loaded] == [("amount_display", "including_tax")]
    stored = _stored_text()
    assert "including_tax" in stored and "table" not in stored, "the deletion of one topic reaches the storage"


def test_only_planned_topics_are_kept(services, reset_state):
    client = _conversation(services, PAUL)
    turn, trace = successful_turn(
        client,
        "Notez pour la suite que mon fournisseur préféré est Papeterie Atlantique et que mon IBAN est "
        "FR76 3000 6000 0112 3456 7890 189.",
    )
    written = _memory(trace).get("written", [])
    assert all(e.get("topic") in TOPICS and e.get("value") in TOPICS[e.get("topic")] for e in written)
    stored = _stored_text()
    assert "Papeterie" not in stored and "FR76" not in stored and "7890" not in stored, (
        "neither business data nor bank details are stored"
    )
    assert not any(e.get("action") == "written" for e in events_of(turn, "memory"))
    for promise in ("je m'en souviendrai", "je retiendrai", "c'est noté pour la prochaine fois", "c'est noté"):
        assert promise not in turn.text.lower(), "the agent does not promise to remember what it did not store"


def test_rereads_rather_than_assumes(chat_client, observation):
    turn, trace = successful_turn(
        chat_client,
        "Vous m'aviez dit que CMD-2010 de Léa Martin était déjà livrée, c'est toujours le cas ?",
    )
    _memory(trace)
    reads = [e for e in business_log(observation) if e.get("route") == "/orders/CMD-2010" and e.get("code") == 200]
    assert tools(trace) and reads, "the agent rereads the order in the application rather than relying on a past conclusion"
    assert "expédiée" in turn.text.lower(), "the answer corrects the user's assumption with the status read now (expédiée)"
