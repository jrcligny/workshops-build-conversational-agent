"""Tests de bout en bout de l'atelier 12. Ils doivent échouer sur la coquille vide."""

import pytest

from tests.communs.tours import appliquer_grille, entree, journal_metier, outils, plat, tour_reussi

pytestmark = pytest.mark.atelier


from tests.communs.client_chat import ClientChat

GRILLE_PAS_DE_PROMESSE = {
    "id": "12-pas-de-promesse-de-memoire",
    "juge_sens": True,
    "exigences": [
        {"type": "interdit", "motifs": [
            "je m'en souviendrai", "je me souviendrai", "je le retiendrai",
            "je n'oublierai pas", "je n'oublierai", "promets de m'en souvenir",
        ]},
    ],
}


def test_annonce_absence_de_memoire_a_l_ouverture(client_chat):
    client_chat.ouvrir()
    tour, _ = tour_reussi(client_chat, "Bonjour")
    assert "mention" in tour.types or "mémoire" in tour.texte.lower() or "memoire" in tour.texte.lower()
    appliquer_grille(GRILLE_PAS_DE_PROMESSE, tour)


def test_pas_de_persistance_entre_conversations(client_chat):
    tour, _ = tour_reussi(client_chat, "Retiens que je préfère les montants hors taxes.")
    appliquer_grille(GRILLE_PAS_DE_PROMESSE, tour)
    autre = client_chat.__class__(client_chat.base_url)
    tour, _ = tour_reussi(autre, "Quelle est ma préférence de présentation ?")
    assert "hors taxes" not in tour.texte.lower()


def test_relecture_plutot_que_supposition(client_chat, observation, services):
    tour, trace = tour_reussi(
        client_chat,
        "Comme la dernière fois, la commande CMD-1042 de Martin Durand était livrée, tu confirmes ?",
    )
    assert outils(trace) or journal_metier(observation), "l'agent doit relire l'application plutôt que de supposer une conclusion passée"
