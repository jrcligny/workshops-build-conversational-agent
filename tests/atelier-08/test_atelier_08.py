"""Tests de bout en bout de l'atelier 08. Ils doivent échouer sur la coquille vide."""

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

def test_etat_preserve_apres_compaction(client_chat):
    _tour_reussi(client_chat, "Je parle du client Martin Durand, commande CMD-1042.")
    for i in range(10):
        _tour_reussi(client_chat, f"D'accord, continue de suivre ce dossier ({i}).")
    tour, trace = _tour_reussi(client_chat, "Et celle-là, elle est où ?")
    plat = str(trace.get("etat") or trace.get("memoire_travail") or {}) + tour.texte
    assert "1042" in plat or "Durand" in plat
