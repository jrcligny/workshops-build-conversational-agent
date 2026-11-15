"""Tests de bout en bout de l'atelier 15. Ils doivent échouer sur la coquille vide."""

import pytest

from socle.traces.tracer import lire_tout

pytestmark = pytest.mark.atelier


def _tour_reussi(client_chat, message: str):
    tour = client_chat.tour(message)
    assert tour.ok, f"le tour doit aboutir (texte + fin) ; reçu : ok={tour.ok}, erreur={tour.erreur!r}"
    assert "texte" in tour.types
    assert "fin" in tour.types
    traces = lire_tout()
    assert traces, "une trace de tour est exigée"
    return tour, traces[-1]

def test_ecriture_retiree_apres_piece_jointe(client_chat, observation):
    _, trace = _tour_reussi(client_chat, "Lis le devis joint et prépare la demande d'achat correspondante.")
    assert observation.etat("soumissions")["demandes_soumises"] == []
    assert "joindre" in str(trace).lower() or "piece" in str(trace).lower() or "devis" in str(trace).lower()
