"""Checks of the bonus workshop (a persistent preference memory), shared by the public and the private
tests (one function per criterion).

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

from agent_gateway.chat_app import reset_conversations
from agent_testkit.chat_client import ChatClient
from agent_testkit.expect import mentions_any, mentions_none
from agent_testkit.turns import business_log, events_of, model_input, successful_turn, tools

TOPICS = {"amount_display": {"excluding_tax", "including_tax"}, "answer_format": {"table", "text"}}


def memory(trace) -> dict:
    memory = trace.get("memory")
    assert isinstance(memory, dict), "trace.memory reports the memory of the turn"
    for key in ("loaded", "written", "deleted"):
        assert isinstance(memory.get(key, []), list), f"trace.memory.{key} is a list"
    return memory


def entries(trace, key: str, topic: str) -> list[dict]:
    return [e for e in memory(trace).get(key, []) if e.get("topic") == topic]


def stored_text() -> str:
    root = Path(os.environ["MEMORY_DIR"])
    return "".join(p.read_text(encoding="utf-8", errors="ignore") for p in root.rglob("*") if p.is_file())


def conversation(services, user: dict) -> ChatClient:
    client = ChatClient(services["interface"])
    client.open(**user)
    return client


def remember(services, case: dict):
    """`case`: the `user` who asks, the `message`, and the `topic` = `value` expected in memory.written."""
    client = conversation(services, case["user"])
    turn, trace = successful_turn(client, case["message"])
    written = entries(trace, "written", case["topic"])
    assert written and written[-1].get("value") == case["value"], f"memory.written: {case['topic']} = {case['value']}"
    return turn, written[-1]


def memory_announced_on_opening(chat_client, case: dict) -> None:
    chat_client.open()
    turn, trace = successful_turn(chat_client, case["greeting"])
    memory(trace)
    mentions = [str(m.get("content", "")).lower() for m in events_of(turn, "mention")]
    memory_mentions = [m for m in mentions if "montant" in m and ("format" in m or "tableau" in m) and "oubli" in m]
    assert memory_mentions, (
        "the first turn carries a mention naming what is kept (amount display, answer format) and that it can be forgotten"
    )
    later, _ = successful_turn(chat_client, case["follow_up"])
    assert not any("montant" in str(m.get("content", "")).lower() for m in events_of(later, "mention")), (
        "the mention is given once, at the opening"
    )


def preference_recalled_in_a_new_conversation(services, case: dict) -> None:
    preference = case["remember"]
    turn, entry = remember(services, preference)
    assert entry.get("origin") == "user", "the entry records its origin: the user asked for it"
    assert entry.get("user") == preference["user"]["user_id"] and entry.get("organization") == preference["user"]["organization"]
    datetime.fromisoformat(str(entry.get("recorded_at")))
    shown = [e for e in events_of(turn, "memory") if e.get("action") == "written"]
    assert shown and shown[-1].get("topic") == preference["topic"], "the interface shows what was just recorded (event memory)"
    assert preference["value"] in stored_text(), "the memory is stored on disk under MEMORY_DIR"

    reset_conversations()  # new conversations, new harness instance: only the stored memory remains
    client = conversation(services, preference["user"])
    recall, trace = successful_turn(client, case["ask"])
    loaded = entries(trace, "loaded", preference["topic"])
    assert loaded and loaded[-1].get("value") == preference["value"], "memory.loaded: the preference is put back at the start"
    if case.get("context_any"):
        context = str(model_input(trace)).lower()
        assert any(w in context for w in case["context_any"]), "the preference reaches the model input"
    mentions_any(recall, case["answer_any"], "the answer applies the recalled preference")


def memory_partitioned_by_user_and_organization(services, case: dict) -> None:
    remember(services, case["remember"])
    for user in case["other_users"]:
        client = conversation(services, user)
        turn, trace = successful_turn(client, case["ask"])
        assert memory(trace).get("loaded") == [], f"memory.loaded is empty for {user['user_id']}: memory is read per user"
        for word in case.get("absent_from_context", []):
            assert word not in str(model_input(trace)).lower()
        mentions_none(turn, case.get("absent_from_answer", []), f"nothing of another user's memory reaches {user['user_id']}")


def consult_correct_forget(services, case: dict) -> None:
    preference = case["remember"]
    user = preference["user"]
    remember(services, preference)

    client = conversation(services, user)
    consulted, _ = successful_turn(client, case["consult"])
    mentions_any(consulted, case["consulted_word"], "the user can consult what is kept")
    _, trace = successful_turn(client, case["correct"])
    assert [e for e in entries(trace, "written", preference["topic"]) if e.get("value") == case["corrected_value"]], (
        "the correction is written"
    )

    client = conversation(services, user)
    _, trace = successful_turn(client, case["ask"])
    loaded = entries(trace, "loaded", preference["topic"])
    assert [e.get("value") for e in loaded] == [case["corrected_value"]], (
        "the new value replaces the old one (one entry per topic)"
    )
    _, trace = successful_turn(client, case["forget"])
    assert memory(trace).get("deleted"), "memory.deleted lists what was forgotten"

    client = conversation(services, user)
    _, trace = successful_turn(client, case["ask"])
    assert memory(trace).get("loaded") == [], "nothing is put back after forgetting"
    stored = stored_text()
    assert case["corrected_value"] not in stored and preference["value"] not in stored, "the deletion reaches the storage"


def only_planned_topics_are_kept(services, case: dict) -> None:
    client = conversation(services, case["user"])
    turn, trace = successful_turn(client, case["message"])
    written = memory(trace).get("written", [])
    assert all(e.get("topic") in TOPICS and e.get("value") in TOPICS[e.get("topic")] for e in written), (
        "only planned topics and values are written"
    )
    stored = stored_text()
    assert not any(data in stored for data in case["never_stored"]), (
        f"neither business data nor {case['never_stored_kind']} are stored"
    )
    assert not any(e.get("action") == "written" for e in events_of(turn, "memory"))
    mentions_none(turn, case["promises"], "the agent does not promise to remember what it did not store")


def rereads_rather_than_assumes(chat_client, observation, case: dict) -> None:
    turn, trace = successful_turn(chat_client, case["question"])
    memory(trace)
    route = f"/orders/{case['reference']}"
    reads = [e for e in business_log(observation) if e.get("route") == route and e.get("code") == 200]
    assert tools(trace) and reads, "the agent rereads the order in the application rather than relying on a past conclusion"
    mentions_any(turn, case["answer_status"], "the answer corrects the user's assumption with the status read now")
