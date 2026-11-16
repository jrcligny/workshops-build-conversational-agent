"""Private tests of workshop 13 (not given to students): same criteria, other inputs.

Another document (claim deadline 1.3, whose version 1.2 is retired), another question without
a documentary answer, another role-restricted document (purchasing workflow, buyer only) and
another order next to the procedure.
"""

import re

import pytest

from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.turns import events_of, successful_turn, tool_result, tools

pytestmark = pytest.mark.workshop

CLAIMS = "En combien de temps une réclamation pour colis endommagé doit-elle être traitée ?"
CURRENT = "/docs/organization-a/claims/1.3"
RETIRED = "/docs/organization-a/claims/1.2"


def _searches(trace) -> list[dict]:
    return [tool_result(c) for c in tools(trace) if "passages" in tool_result(c)]


def _sources(turn) -> list[dict]:
    return [s for e in events_of(turn, "sources") for s in (e.get("sources") or [])]


def test_document_search_and_sources(chat_client):
    turn, trace = successful_turn(chat_client, CLAIMS)
    searches = _searches(trace)
    assert searches, "the document search tool is called and returns result.passages"
    returned = {p["address"] for r in searches for p in r["passages"]}
    sources = _sources(turn)
    assert sources, "the sources event lists the documents used"
    assert {s.get("address") for s in sources} <= returned, "every displayed source comes from a returned passage"
    assert CURRENT in {s.get("address") for s in sources}
    assert all(s.get("title") and s.get("version") for s in sources), "a source shows its title and version"
    assert "dix" in turn.text.lower() or "10" in turn.text


def test_empty_result_declared(chat_client):
    turn, trace = successful_turn(chat_client, "Quelle est la procédure interne pour réserver la cantine du personnel le vendredi ?")
    searches = _searches(trace)
    assert searches, "the documentation is searched before answering"
    assert all(not r["passages"] for r in searches), "no passage clears the threshold: the search result is empty"
    assert not _sources(turn), "no source is displayed when nothing answers the question"
    text = turn.text.lower()
    declared = re.search(
        r"(aucun|aucune) (document|passage|information|résultat|source|mention|procédure)"
        r"|(pas|rien) trouvé|introuvable|ne (contient|mentionne|traite|couvre) (pas|rien)|ne dit rien",
        text,
    )
    assert declared, "the empty result is declared as such"
    assert "/docs/" not in text, "no document address is cited"


def test_permission_filtering(chat_client, services):
    question = "Quelles sont les étapes de validation d'une demande d'achat ?"
    turn, trace = successful_turn(chat_client, question)
    assert _searches(trace), "the search is made with the user's identity"
    seen = {p["document_id"] for r in _searches(trace) for p in r["passages"]}
    assert "purchase-request-workflow" not in seen, "the purchasing document is never returned to customer service"
    assert "purchase-request-workflow" not in str(_sources(turn))
    buyer = ChatClient(services["interface"])
    buyer.open(user_id="paul-buyer", role="buyer", organization="organization-a")
    turn, trace = successful_turn(buyer, question)
    assert "purchase-request-workflow" in {p["document_id"] for r in _searches(trace) for p in r["passages"]}, (
        "the same question, asked by the buyer, reaches the purchasing document"
    )


def test_retired_version_absent(chat_client):
    turn, trace = successful_turn(chat_client, "Quelle version de la fiche sur le délai de traitement des réclamations s'applique ?")
    addresses = {p["address"] for r in _searches(trace) for p in r["passages"]}
    assert CURRENT in addresses and RETIRED not in addresses, "only the version in force is indexed and returned"
    text = turn.text.lower()
    assert "1.3" in text and "1.2" not in text and "quinze" not in text, "the answer gives the version in force only"


def test_documentation_distinguished_from_data(chat_client):
    turn, trace = successful_turn(
        chat_client, "Quel est le délai de traitement d'une réclamation, et où en est la commande CMD-2010 ?"
    )
    assert _searches(trace), "the claim deadline comes from the document search"
    assert any("CMD-2010" in str(c.get("arguments")) for c in tools(trace) if "passages" not in tool_result(c)), (
        "the status comes from the business application, through another tool"
    )
    assert "CMD-2010" not in str(_sources(turn)), "the sources event lists documents only, not application data"
    assert "expédiée" in turn.text.lower()
