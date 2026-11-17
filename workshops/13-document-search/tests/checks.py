"""Checks of workshop 13, shared by the public and the private tests (one function per criterion).

Contract read here:
- the document search tool's result is the one of the search service: `passages[]`
  (`document_id`, `title`, `version`, `address`, `audience`) and `no_passage`;
- interface event `sources`, data `{"sources": [{"title", "version", "address"}]}`, built by
  the program from the passages actually returned (never written by the model).
"""

import re

from agent_testkit.chat_client import ChatClient
from agent_testkit.expect import mentions_any
from agent_testkit.turns import events_of, successful_turn, tool_result, tools

EMPTY_RESULT_DECLARED = re.compile(
    r"(aucun|aucune) (document|passage|information|résultat|source|mention|procédure)"
    r"|(pas|rien) trouvé|introuvable|ne (contient|mentionne|traite|couvre) (pas|rien)|ne dit rien"
)


def searches(trace) -> list[dict]:
    return [tool_result(c) for c in tools(trace) if "passages" in tool_result(c)]


def sources(turn) -> list[dict]:
    return [s for e in events_of(turn, "sources") for s in (e.get("sources") or [])]


def document_search_and_sources(chat_client, case: dict) -> None:
    turn, trace = successful_turn(chat_client, case["question"])
    results = searches(trace)
    assert results, "the document search tool is called and returns result.passages"
    returned = {p["address"] for r in results for p in r["passages"]}
    shown = sources(turn)
    assert shown, "the sources event lists the documents used"
    assert {s.get("address") for s in shown} <= returned, "every displayed source comes from a returned passage"
    assert case["current"] in {s.get("address") for s in shown}
    assert all(s.get("title") and s.get("version") for s in shown), "a source shows its title and version"
    if case.get("answer_any"):
        mentions_any(turn, case["answer_any"], "the answer uses the documentation found")


def empty_result_declared(chat_client, case: dict) -> None:
    turn, trace = successful_turn(chat_client, case["question"])
    results = searches(trace)
    assert results, "the documentation is searched before answering"
    # Above the default threshold (0.3), nothing in the corpus answers this question.
    assert all(not r["passages"] for r in results), "no passage clears the threshold: the search result is empty"
    assert not sources(turn), "no source is displayed when nothing answers the question"
    text = turn.text.lower()
    assert EMPTY_RESULT_DECLARED.search(text), "the empty result is declared as such (a bare « aucun » or « pas » is not enough)"
    assert "/docs/" not in text, "no document address is cited"


def permission_filtering(chat_client, services, case: dict) -> None:
    document = case["document"]
    turn, trace = successful_turn(chat_client, case["question"])
    assert searches(trace), "the search is made with the user's identity"
    seen = {p["document_id"] for r in searches(trace) for p in r["passages"]}
    assert document not in seen, f"the {case['document_kind']} document is never returned to customer service"
    assert document not in str(sources(turn))
    allowed = ChatClient(services["interface"])
    allowed.open(**case["allowed_user"])
    turn, trace = successful_turn(allowed, case["question"])
    assert document in {p["document_id"] for r in searches(trace) for p in r["passages"]}, (
        f"the same question, asked by the {case['allowed_user']['role']}, reaches the {case['document_kind']} document"
    )


def retired_version_absent(chat_client, case: dict) -> None:
    turn, trace = successful_turn(chat_client, case["question"])
    addresses = {p["address"] for r in searches(trace) for p in r["passages"]}
    assert case["current"] in addresses and case["retired"] not in addresses, "only the version in force is indexed and returned"
    text = turn.text.lower()
    assert case["version"] in text and not any(m in text for m in case["retired_mentions"]), (
        "the answer gives the version in force, never the retired one"
    )


def documentation_distinguished_from_data(chat_client, case: dict) -> None:
    reference = case["reference"]
    turn, trace = successful_turn(chat_client, case["question"])
    assert searches(trace), f"the {case['documentation']} comes from the document search"
    assert any(reference in str(c.get("arguments")) for c in tools(trace) if "passages" not in tool_result(c)), (
        "the status comes from the business application, through another tool"
    )
    assert reference not in str(sources(turn)), "the sources event lists documents only, not application data"
    mentions_any(turn, case["answer_status"], "the answer gives the status read in the application")
