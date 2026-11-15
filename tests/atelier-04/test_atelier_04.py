"""Tests de bout en bout de l'atelier 04. Ils doivent échouer sur la coquille vide."""

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

def test_consultation_commande_exacte(client_chat):
    tour, trace = _tour_reussi(client_chat, "Où en est la commande CMD-1042 de Martin Durand ?")
    outils = trace.get("outils") or []
    assert any("commande" in str(o).lower() for o in outils)
    assert "livr" in tour.texte.lower()


def test_reference_inversee_signalee(client_chat):
    tour, trace = _tour_reussi(client_chat, "Où en est la commande CMD-1402 ?")
    assert "1042" in tour.texte or "substitution" in tour.texte.lower() or "proche" in tour.texte.lower()
    assert trace.get("outils")


def test_commande_supprimee_jamais_suggeree(client_chat):
    tour, _ = _tour_reussi(client_chat, "Où en est la commande CMD-0881 ?")
    assert "supprim" not in tour.texte.lower() or "pas" in tour.texte.lower()
