"""Tests de bout en bout de l'atelier 05. Ils doivent échouer sur la coquille vide."""

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

def test_homonymes_plusieurs_candidats(client_chat):
    tour, trace = _tour_reussi(client_chat, "Quelles sont les commandes de Léa Martin ?")
    texte = tour.texte.lower()
    assert ("lille" in texte and "lyon" in texte) or "plusieurs" in texte or "homonym" in texte
    assert trace.get("outils")


def test_filtre_retard(client_chat, observation):
    observation.reinitialiser("volume")
    tour, _ = _tour_reussi(client_chat, "Quelles sont les commandes en retard de Transports Morel ?")
    assert tour.texte
