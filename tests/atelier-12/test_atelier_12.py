"""Tests de bout en bout de l'atelier 12. Ils doivent échouer sur la coquille vide."""

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

def test_annonce_absence_de_memoire_a_l_ouverture(client_chat):
    client_chat.ouvrir()
    tour, _ = _tour_reussi(client_chat, "Bonjour")
    assert "mention" in tour.types or "mémoire" in tour.texte.lower() or "memoire" in tour.texte.lower()


def test_pas_de_persistance_entre_conversations(client_chat):
    _tour_reussi(client_chat, "Retiens que je préfère les montants hors taxes.")
    autre = client_chat.__class__(client_chat.base_url)
    tour, _ = _tour_reussi(autre, "Quelle est ma préférence de présentation ?")
    assert "hors taxes" not in tour.texte.lower() or "réglage" in tour.texte.lower()
