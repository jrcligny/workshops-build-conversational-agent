"""End-to-end tests of workshop 13. They must fail on the empty shell.

Contract read here:
- the document search tool's result is the one of the search service: `passages[]`
  (`document_id`, `title`, `version`, `address`, `audience`) and `no_passage`;
- interface event `sources`, data `{"sources": [{"title", "version", "address"}]}`, built by
  the program from the passages actually returned (never written by the model).
"""

import pytest

from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.turns import events_of, successful_turn, tool_result, tools

pytestmark = pytest.mark.workshop

INCOMPLETE = "Que dit la procédure quand une livraison arrive incomplète ?"
CURRENT = "/docs/organization-a/incomplete-deliveries/2.1"
RETIRED = "/docs/organization-a/incomplete-deliveries/1.0"


def _searches(trace) -> list[dict]:
    return [tool_result(c) for c in tools(trace) if "passages" in tool_result(c)]


def _sources(turn) -> list[dict]:
    return [s for e in events_of(turn, "sources") for s in (e.get("sources") or [])]


def test_document_search_and_sources(chat_client):
    turn, trace = successful_turn(chat_client, INCOMPLETE)
    searches = _searches(trace)
    assert searches, "the document search tool is called and returns result.passages"
    returned = {p["address"] for r in searches for p in r["passages"]}
    sources = _sources(turn)
    assert sources, "the sources event lists the documents used"
    assert {s.get("address") for s in sources} <= returned, "every displayed source comes from a returned passage"
    assert CURRENT in {s.get("address") for s in sources}
    assert all(s.get("title") and s.get("version") for s in sources), "a source shows its title and version"


def test_empty_result_declared(chat_client):
    turn, trace = successful_turn(chat_client, "Que dit la documentation sur le voyage spatial des factures xyzzy-42 ?")
    searches = _searches(trace)
    assert searches, "the documentation is searched before answering"
    # The passages returned (if any) do not answer the question: the agent says so instead of citing them.
    assert not _sources(turn), "no source is displayed when nothing answers the question"
    assert any(w in turn.text.lower() for w in ("aucun", "pas trouvé", "rien trouvé", "introuvable")), "the empty result is declared"


def test_permission_filtering(chat_client, services):
    question = "Donnez-moi la définition interne des statuts de facture, en particulier « réglée »."
    turn, trace = successful_turn(chat_client, question)
    assert _searches(trace), "the search is made with the user's identity"
    seen = {p["document_id"] for r in _searches(trace) for p in r["passages"]}
    assert "invoice-statuses" not in seen, "the accounting document is never returned to customer service"
    assert "invoice-statuses" not in str(_sources(turn))
    accountant = ChatClient(services["interface"])
    accountant.open(user_id="nina-accountant", role="accountant", organization="organization-a")
    turn, trace = successful_turn(accountant, question)
    assert "invoice-statuses" in {p["document_id"] for r in _searches(trace) for p in r["passages"]}, (
        "the same question, asked by the accountant, reaches the accounting document"
    )


def test_retired_version_absent(chat_client):
    turn, trace = successful_turn(chat_client, "Quelle est la version en vigueur de la procédure des livraisons incomplètes ?")
    addresses = {p["address"] for r in _searches(trace) for p in r["passages"]}
    assert CURRENT in addresses and RETIRED not in addresses, "only the version in force is indexed and returned"
    assert "2.1" in turn.text and not any(m in turn.text.lower() for m in ("version 1.0", "v1.0", "1.0 de la procédure")), (
        "the answer gives the version in force, never the retired one"
    )


def test_documentation_distinguished_from_data(chat_client):
    turn, trace = successful_turn(chat_client, "Que dit la procédure pour une livraison incomplète, et quel est le statut de CMD-1042 ?")
    assert _searches(trace), "the procedure comes from the document search"
    assert any("CMD-1042" in str(c.get("arguments")) for c in tools(trace) if "passages" not in tool_result(c)), (
        "the status comes from the business application, through another tool"
    )
    assert "CMD-1042" not in str(_sources(turn)), "the sources event lists documents only, not application data"
    assert "livrée" in turn.text.lower()
