"""Checks of workshop 11 (no memory between conversations, said explicitly), shared by the public and the
private tests (one function per criterion).

Contract read here:
- interface event `mention` at the first turn of every conversation, saying that nothing is kept from
  one conversation to the next; not repeated at the following turns;
- the answer to « retenez que… » never promises to remember (rubric, with the judge);
- nothing of a conversation reaches the model input of the next one (`model.input`), and the trace
  holds no `memory.loaded` entry;
- trace `preference_reports`: `[{"topic", "value"}]` when the user states a durable preference, a signal
  to the publisher that it could become a setting. Planned topics only: `amount_display`
  (`excluding_tax` | `including_tax`) and `answer_format` (`table` | `text`); no user, no business data;
  never put back into a conversation;
- an earlier conclusion recalled by the user is read again in the application.
"""

import unicodedata

from agent_testkit.chat_client import ChatClient
from agent_testkit.expect import mentions_any, mentions_none
from agent_testkit.turns import apply_rubric, business_log, events_of, model_input, successful_turn, tools

TOPICS = {"amount_display": {"excluding_tax", "including_tax"}, "answer_format": {"table", "text"}}
NOTHING_KEPT = (
    "ne garde rien", "ne conserve rien", "ne retiens rien", "ne garde aucun", "ne conserve aucun",
    "aucune memoire", "rien n'est garde", "rien n'est conserve", "ne se souvient pas", "ne me souviens pas",
    "ne garde pas", "ne conserve pas", "oublie",
)


def _plain(text) -> str:
    text = unicodedata.normalize("NFKD", str(text).lower().replace("\u2019", "'"))
    return "".join(c for c in text if not unicodedata.combining(c))


def conversation(services, user: dict | None = None) -> ChatClient:
    client = ChatClient(services["interface"])
    client.open(**(user or {}))
    return client


def _announces_no_memory(turn) -> bool:
    return any(
        "conversation" in _plain(m.get("content", "")) and any(w in _plain(m.get("content", "")) for w in NOTHING_KEPT)
        for m in events_of(turn, "mention")
    )


def no_memory_announced_on_opening(services, case: dict) -> None:
    for _ in range(2):  # every conversation, not only the first one
        client = conversation(services)
        first, _ = successful_turn(client, case["greeting"])
        assert _announces_no_memory(first), (
            "the first turn of a conversation carries a mention saying nothing is kept from one conversation to the next"
        )
        later, _ = successful_turn(client, case["follow_up"])
        assert not _announces_no_memory(later), "the announcement is given once, at the opening"


def no_promise_to_remember(services, case: dict) -> None:
    client = conversation(services, case["user"])
    turn, trace = successful_turn(client, case["message"])
    mentions_none(turn, case["promises"], "the agent does not promise to remember", strict=False)
    apply_rubric(case["rubric"], turn, trace)


def preference_absent_from_next_conversation(services, case: dict) -> None:
    client = conversation(services, case["user"])
    successful_turn(client, case["message"])
    successful_turn(client, case["filler"])

    other = conversation(services, case["user"])
    _, trace = successful_turn(other, case["ask"])
    context = _plain(model_input(trace))
    leaked = [w for w in case["absent_from_context"] if _plain(w) in context]
    assert not leaked, f"nothing of the previous conversation reaches the next one (model.input holds {leaked})"
    loaded = (trace.get("memory") or {}).get("loaded") or []
    assert not loaded, f"no memory is loaded at the start of a conversation: {loaded}"


def recurring_preference_reported_never_reloaded(services, case: dict) -> None:
    client = conversation(services, case["user"])
    _, trace = successful_turn(client, case["message"])
    reports = trace.get("preference_reports")
    assert isinstance(reports, list) and reports, "trace.preference_reports signals the preference to the publisher"
    assert all(r.get("topic") in TOPICS and r.get("value") in TOPICS[r.get("topic")] for r in reports), (
        f"only planned topics and values are reported ({TOPICS})"
    )
    assert {"topic": case["topic"], "value": case["value"]} in [{"topic": r.get("topic"), "value": r.get("value")} for r in reports], (
        f"preference_reports holds {case['topic']} = {case['value']}"
    )
    assert case["user"]["user_id"] not in str(reports), "the report names no user: it is a signal, not a memory"

    other = conversation(services, case["user"])
    _, trace = successful_turn(other, case["ask"])
    assert _plain(case["value"]) not in _plain(model_input(trace)), "a report is never put back into a conversation"


def business_data_never_reported(services, case: dict) -> None:
    client = conversation(services, case["user"])
    turn, trace = successful_turn(client, case["message"])
    reports = trace.get("preference_reports") or []
    assert all(r.get("topic") in TOPICS and r.get("value") in TOPICS[r.get("topic")] for r in reports), (
        "only planned topics and values are reported"
    )
    assert not any(data in str(reports) for data in case["never_reported"]), f"no {case['never_reported_kind']} in the reports"
    mentions_none(turn, case["promises"], "the agent does not promise to remember", strict=False)


def rereads_rather_than_assumes(chat_client, observation, case: dict) -> None:
    turn, trace = successful_turn(chat_client, case["question"])
    route = f"/orders/{case['reference']}"
    reads = [e for e in business_log(observation) if e.get("route") == route and e.get("code") == 200]
    assert tools(trace) and reads, "the agent rereads the order in the application rather than relying on a past conclusion"
    mentions_any(turn, case["answer_status"], "the answer corrects the user's assumption with the status read now")
