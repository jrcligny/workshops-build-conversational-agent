"""Tests de bout en bout de l'atelier 17. Ils doivent échouer sur la coquille vide."""

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

def test_traces_masquees_et_rapport_de_parcours(client_chat, traces):
    _tour_reussi(client_chat, "Où en est la commande CMD-1042 ?")
    plat = str(traces.dernier()).lower()
    assert "authorization" not in plat and "bearer " not in plat
    from pathlib import Path
    assert (Path("mon-agent") / "rapport-parcours.md").exists(), "rapport de taux de parcours manquant"
