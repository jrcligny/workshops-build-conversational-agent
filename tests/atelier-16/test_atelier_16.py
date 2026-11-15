"""Tests de bout en bout de l'atelier 16. Ils doivent échouer sur la coquille vide."""

import pytest

from tests.communs.tours import appliquer_grille, entree, journal_metier, outils, plat, tour_reussi

pytestmark = pytest.mark.atelier


from tests.communs.client_chat import ClientChat


def test_mention_de_resultat_partiel_par_le_harness(client_chat, observation):
    observation.reinitialiser("volume")
    tour, _ = tour_reussi(client_chat, "Liste toutes les commandes en retard de Transports Morel.")
    assert "mention" in tour.types, "la mention de résultat borné est construite par le harness, sous la réponse"


def test_client_enregistre_seulement_apres_le_choix(client_chat):
    tour, trace = tour_reussi(client_chat, "Quelles sont les commandes de Léa Martin ?")
    etat = plat(trace.get("etat") or entree(trace).get("etat") or "")
    # plusieurs candidats : pas encore de client en cours unique
    assert "Léa Martin" not in etat or "lille" not in etat.lower() or "en cours" not in etat.lower()
    tour, trace = tour_reussi(client_chat, "Celle de Lille.")
    etat = plat(trace.get("etat") or entree(trace).get("etat") or trace)
    assert "lille" in etat.lower()


def test_enregistrement_non_consulte_marque_non_verifie(client_chat):
    tour, trace = tour_reussi(
        client_chat,
        "La facture FAC-9999 et la commande CMD-0000 sont-elles réglées ?",
    )
    plat_t = (tour.texte + plat(trace)).lower()
    assert "mention" in tour.types or "non vérifi" in plat_t or "non verifi" in plat_t or "pas consult" in plat_t or "pas vérifi" in plat_t


def test_conversations_simultanees_isolees(services, observation):
    a = ClientChat(services["interface"])
    a.ouvrir(utilisateur_id="camille-renard", role="charge_clientele", organisation="organisation-a")
    tour_reussi(a, "Je m'occupe de Martin Durand, commande CMD-1042.")
    b = ClientChat(services["interface"])
    b.ouvrir(utilisateur_id="paul-acheteur", role="acheteur", organisation="organisation-a")
    tour, trace = tour_reussi(b, "Qui est le client en cours, et quelle commande suis-je ?")
    plat_t = (tour.texte + plat(trace.get("etat") or "") + plat(entree(trace))).lower()
    assert "cmd-1042" not in plat_t
    assert "durand" not in plat_t
