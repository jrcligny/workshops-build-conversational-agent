"""End-to-end tests of workshop 12: a persistent preference memory. They must fail on the empty shell.

Contract read here:
- trace `memory`: `loaded` (entries put into the context at the start of the turn), `written`
  and `deleted` (entries changed by the turn). An entry is
  `{"topic", "value", "origin", "recorded_at", "user", "organization"}`.
- planned topics only: `amount_display` (`excluding_tax` | `including_tax`) and
  `answer_format` (`table` | `text`); `origin` is `"user"` (written at the user's explicit request).
- interface event `memory` (`action`: `written` | `deleted`, `topic`, `value`) when the memory changes;
  event `mention` at the first turn of a conversation, saying what the agent keeps.
- storage on disk under `MEMORY_DIR` (set by the tests, `my-agent/memory/` otherwise), read at call time.
"""

import os
from datetime import datetime
from pathlib import Path

import pytest

from agent_gateway.chat_app import reset_conversations
from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.turns import business_log, events_of, model_input, successful_turn, tools

pytestmark = pytest.mark.workshop

CAMILLE = {"user_id": "camille-renard", "role": "customer_service", "organization": "organization-a"}
PAUL = {"user_id": "paul-buyer", "role": "buyer", "organization": "organization-a"}
INES = {"user_id": "ines-service-b", "role": "customer_service", "organization": "organization-b"}

PREFERENCE = "Retenez que je préfère les montants hors taxes."
ASK = "Quelle est ma préférence d'affichage des montants ?"
TOPICS = {"amount_display": {"excluding_tax", "including_tax"}, "answer_format": {"table", "text"}}


def _memory(trace) -> dict:
    memory = trace.get("memory")
    assert isinstance(memory, dict), "trace.memory reports the memory of the turn"
    for key in ("loaded", "written", "deleted"):
        assert isinstance(memory.get(key, []), list), f"trace.memory.{key} is a list"
    return memory


def _entries(trace, key: str, topic: str = "amount_display") -> list[dict]:
    return [e for e in _memory(trace).get(key, []) if e.get("topic") == topic]


def _stored_text() -> str:
    root = Path(os.environ["MEMORY_DIR"])
    return "".join(p.read_text(encoding="utf-8", errors="ignore") for p in root.rglob("*") if p.is_file())


def _conversation(services, user: dict) -> ChatClient:
    client = ChatClient(services["interface"])
    client.open(**user)
    return client


def _remember_excluding_tax(services):
    client = _conversation(services, CAMILLE)
    turn, trace = successful_turn(client, PREFERENCE)
    written = _entries(trace, "written")
    assert written and written[-1].get("value") == "excluding_tax", "memory.written: amount_display = excluding_tax"
    return turn, written[-1]


def test_memory_announced_on_opening(chat_client):
    chat_client.open()
    turn, trace = successful_turn(chat_client, "Bonjour")
    _memory(trace)
    mentions = [str(m.get("content", "")).lower() for m in events_of(turn, "mention")]
    memory_mentions = [m for m in mentions if "montant" in m and ("format" in m or "tableau" in m) and "oubli" in m]
    assert memory_mentions, (
        "the first turn carries a mention naming what is kept (amount display, answer format) and that it can be forgotten"
    )
    later, _ = successful_turn(chat_client, "Et ensuite ?")
    assert not any("montant" in str(m.get("content", "")).lower() for m in events_of(later, "mention")), (
        "the mention is given once, at the opening"
    )


def test_preference_recalled_in_a_new_conversation(services, reset_state):
    turn, entry = _remember_excluding_tax(services)
    assert entry.get("origin") == "user", "the entry records its origin: the user asked for it"
    assert entry.get("user") == "camille-renard" and entry.get("organization") == "organization-a"
    datetime.fromisoformat(str(entry.get("recorded_at")))
    shown = [e for e in events_of(turn, "memory") if e.get("action") == "written"]
    assert shown and shown[-1].get("topic") == "amount_display", "the interface shows what was just recorded (event memory)"
    assert "excluding_tax" in _stored_text(), "the memory is stored on disk under MEMORY_DIR"

    reset_conversations()  # new conversations, new harness instance: only the stored memory remains
    client = _conversation(services, CAMILLE)
    recall, trace = successful_turn(client, ASK)
    loaded = _entries(trace, "loaded")
    assert loaded and loaded[-1].get("value") == "excluding_tax", "memory.loaded: the preference is put back at the start"
    context = str(model_input(trace)).lower()
    assert "excluding_tax" in context or "hors tax" in context, "the preference reaches the model input"
    assert "hors tax" in recall.text.lower()


def test_memory_partitioned_by_user_and_organization(services, reset_state):
    _remember_excluding_tax(services)
    for user in (PAUL, INES):
        client = _conversation(services, user)
        turn, trace = successful_turn(client, ASK)
        assert _memory(trace).get("loaded") == [], f"memory.loaded is empty for {user['user_id']}: memory is read per user"
        assert "hors tax" not in str(model_input(trace)).lower()
        assert "vous préférez les montants hors tax" not in turn.text.lower()


def test_consult_correct_forget(services, reset_state):
    _remember_excluding_tax(services)

    client = _conversation(services, CAMILLE)
    consulted, _ = successful_turn(client, "Que retenez-vous de moi d'une conversation à l'autre ?")
    assert "hors tax" in consulted.text.lower(), "the user can consult what is kept"
    _, trace = successful_turn(client, "Finalement, retenez plutôt que je préfère les montants TTC.")
    assert [e for e in _entries(trace, "written") if e.get("value") == "including_tax"], "the correction is written"

    client = _conversation(services, CAMILLE)
    _, trace = successful_turn(client, ASK)
    loaded = _entries(trace, "loaded")
    assert [e.get("value") for e in loaded] == ["including_tax"], "the new value replaces the old one (one entry per topic)"
    _, trace = successful_turn(client, "Oubliez tout ce que vous retenez de moi.")
    assert _memory(trace).get("deleted"), "memory.deleted lists what was forgotten"

    client = _conversation(services, CAMILLE)
    _, trace = successful_turn(client, ASK)
    assert _memory(trace).get("loaded") == [], "nothing is put back after forgetting"
    stored = _stored_text()
    assert "including_tax" not in stored and "excluding_tax" not in stored, "the deletion reaches the storage"


def test_only_planned_topics_are_kept(services, reset_state):
    client = _conversation(services, CAMILLE)
    turn, trace = successful_turn(
        client,
        "Retenez que la commande CMD-1042 est en préparation, et retenez aussi mon numéro de carte "
        "bancaire 4970 1234 5678 9012.",
    )
    written = _memory(trace).get("written", [])
    assert all(e.get("topic") in TOPICS and e.get("value") in TOPICS[e.get("topic")] for e in written), (
        "only planned topics and values are written"
    )
    stored = _stored_text()
    assert "CMD-1042" not in stored and "4970" not in stored, "neither business data nor a card number is stored"
    assert not any(e.get("action") == "written" for e in events_of(turn, "memory"))
    for promise in ("je m'en souviendrai", "je retiendrai", "c'est noté pour la prochaine fois"):
        assert promise not in turn.text.lower(), "the agent does not promise to remember what it did not store"


def test_rereads_rather_than_assumes(chat_client, observation):
    turn, trace = successful_turn(
        chat_client,
        "Comme la dernière fois, la commande CMD-1042 de Martin Durand est encore en préparation, vous confirmez ?",
    )
    _memory(trace)
    reads = [e for e in business_log(observation) if e.get("route") == "/orders/CMD-1042" and e.get("code") == 200]
    assert tools(trace) and reads, "the agent rereads the order in the application rather than relying on a past conclusion"
    assert "livrée" in turn.text.lower(), "the answer corrects the user's assumption with the status read now (livrée)"
