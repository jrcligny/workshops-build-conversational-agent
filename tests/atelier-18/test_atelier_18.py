"""Tests de bout en bout de l'atelier 18. Ils doivent échouer sur la coquille vide."""

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

def test_soumission_jamais_rejouee(client_chat, observation):
    observation.armer_panne("issue_inconnue", True)
    tour, _ = _tour_reussi(client_chat, "Soumets la demande d'achat déjà préparée.")
    assert "vérif" in tour.texte.lower() or "verif" in tour.texte.lower()
