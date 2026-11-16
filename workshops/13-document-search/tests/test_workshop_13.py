"""End-to-end tests of workshop 13. They must fail on the empty shell."""

import pytest

from workshop_kit.testing.turns import flat, successful_turn, tools

pytestmark = pytest.mark.workshop


def test_document_search_and_sources(chat_client):
    turn, trace = successful_turn(chat_client, "Que dit la procédure quand une livraison arrive incomplète ?")
    assert "sources" in turn.types, "the displayed sources are established by the program (sources event)"
    assert tools(trace)
    assert "procédure" in turn.text.lower() or "incomplète" in turn.text.lower()


def test_empty_result_declared(chat_client):
    turn, _ = successful_turn(chat_client, "Que dit la documentation sur le voyage spatial des factures xyzzy-42 ?")
    text = turn.text.lower()
    assert "aucun" in text or "pas trouvé" in text or "rien" in text or "introuvable" in text or " pas " in text


def test_permission_filtering(chat_client):
    turn, trace = successful_turn(chat_client, "Donnez-moi la définition interne des statuts de facture, en particulier « réglée ».")
    flat_t = (turn.text + flat(tools(trace))).lower()
    # camille works in customer service: the accounting document must not be served to her
    assert "accountant" not in flat_t or "autoris" in flat_t or "pas accès" in flat_t or "droit" in flat_t or "aucun" in flat_t


def test_retired_version_absent(chat_client):
    turn, trace = successful_turn(chat_client, "Quelle est la version en vigueur de la procédure des livraisons incomplètes ?")
    flat_t = (turn.text + flat(tools(trace))).lower()
    assert "2.1" in flat_t or "version" in flat_t
    assert "1.0" not in flat_t or "retired" in flat_t or "retiré" in flat_t


def test_documentation_distinguished_from_data(chat_client):
    turn, _ = successful_turn(
        chat_client,
        "Que dit la procédure pour une livraison incomplète, et quel est le statut de CMD-1042 ?",
    )
    text = turn.text.lower()
    assert "documentation" in text or "procédure" in text or "sources" in turn.types
    assert "cmd-1042" in text or "commande" in text or "livr" in text
