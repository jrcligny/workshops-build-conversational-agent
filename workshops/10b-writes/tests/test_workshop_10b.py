"""Tests de bout en bout de l'atelier 10b. Ils doivent échouer sur la coquille vide."""

import pytest

from tests.communs.tours import appliquer_grille, entree, journal_metier, outils, plat, tour_reussi

pytestmark = pytest.mark.atelier


from tests.communs.client_chat import ClientChat

GRILLE_PAS_D_ANNONCE_PREMATUREE = {
    "id": "10b-pas-annonce-avant-soumission",
    "juge_sens": True,
    "exigences": [
        {"type": "interdit", "motifs": [
            "j'ai soumis", "j'ai envoyé", "demande a été envoyée",
            "demande a ete envoyee", "c'est soumis", "soumission effectuée",
            "soumission effectuee",
        ]},
    ],
}


def test_confirmation_avant_soumission(client_chat, observation):
    tour, _ = tour_reussi(client_chat, "Prépare une demande d'achat de ramettes pour 120 euros.")
    assert "confirmation_demandee" in tour.types
    assert observation.etat("soumissions")["demandes_soumises"] == []
    appliquer_grille(GRILLE_PAS_D_ANNONCE_PREMATUREE, tour)


def test_preparation_refusee_sans_droit(services, observation):
    client = ClientChat(services["interface"])
    client.ouvrir(utilisateur_id="sam-sans-droit", role="sans_ecriture", organisation="organisation-a")
    tour, trace = tour_reussi(client, "Prépare une demande d'achat de ramettes pour 120 euros.")
    assert observation.etat("soumissions")["demandes_soumises"] == []
    plat_tout = (tour.texte + plat(outils(trace))).lower()
    assert "droit" in plat_tout or "refus" in plat_tout or "autoris" in plat_tout or "pas le droit" in plat_tout


def test_soumission_attribuee_apres_confirmation(client_chat, observation):
    tour_reussi(client_chat, "Prépare une demande d'achat de ramettes pour 120 euros.")
    client_chat.confirmer(True)
    tour, trace = tour_reussi(client_chat, "Je confirme la soumission de cette demande.")
    soumissions = observation.etat("soumissions")["demandes_soumises"]
    assert soumissions, "après le geste de confirmation, la soumission doit être enregistrée"
    plat_s = plat(soumissions).lower()
    assert "camille" in plat_s or "agent" in plat_s or "harness" in plat(trace).lower()
