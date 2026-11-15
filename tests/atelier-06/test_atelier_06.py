"""Tests de bout en bout de l'atelier 06. Ils doivent échouer sur la coquille vide."""

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

def test_plusieurs_cycles(client_chat):
    tour, trace = _tour_reussi(client_chat, "Trouve Léa Martin de Lille et donne l'état de sa commande.")
    cycles = trace.get("cycles") or trace.get("outils") or []
    assert cycles, "la boucle agentique doit produire plusieurs cycles ou appels"
