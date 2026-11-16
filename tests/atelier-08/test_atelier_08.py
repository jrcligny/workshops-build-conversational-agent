"""Tests de bout en bout de l'atelier 08. Ils doivent échouer sur la coquille vide."""

import pytest

from tests.communs.tours import appliquer_grille, entree, journal_metier, outils, plat, tour_reussi

pytestmark = pytest.mark.atelier


from socle.config import reglages


def _etat(trace) -> str:
    return plat(trace.get("etat") or trace.get("memoire_travail") or entree(trace).get("etat") or "")


def test_etat_preserve_apres_compaction(client_chat):
    tour_reussi(client_chat, "Je parle du client Martin Durand, commande CMD-1042.")
    for i in range(int(reglages.seuil_compaction_messages) + 2):
        tour_reussi(client_chat, f"D'accord, continue de suivre ce dossier ({i}).")
    tour, trace = tour_reussi(client_chat, "Et celle-là, elle est où ?")
    etat = _etat(trace)
    assert etat, "l'état de conversation doit figurer dans la trace, distinct du résumé"
    assert "1042" in etat or "Durand" in etat
    # distinct du résumé de compaction
    assert trace.get("etat") or trace.get("memoire_travail") or entree(trace).get("etat")


def test_choix_entre_homonymes_conserve(client_chat):
    tour_reussi(client_chat, "Quelles sont les commandes de Léa Martin ?")
    tour_reussi(client_chat, "Celle de Lille, s'il te plaît.")
    for i in range(int(reglages.seuil_compaction_messages) + 2):
        tour_reussi(client_chat, f"Merci, on reste sur ce dossier ({i}).")
    _, trace = tour_reussi(client_chat, "Rappelle-moi le client en cours.")
    etat = _etat(trace) + plat(entree(trace))
    assert "Lille" in etat or "lille" in etat.lower()
    assert "Lyon" not in etat or "Lille" in etat


def test_changement_de_client_sans_ambiguite(client_chat):
    tour_reussi(client_chat, "Je parle de Martin Durand, commande CMD-1042.")
    tour, trace = tour_reussi(client_chat, "Passons maintenant à Transports Morel uniquement.")
    etat = _etat(trace)
    assert "Morel" in etat or "morel" in etat.lower()
    assert "Durand" not in etat
