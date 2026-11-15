"""Tests de bout en bout de l'atelier 11. Ils doivent échouer sur la coquille vide."""

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

def test_requetes_de_trace_presentes_et_executables():
    from pathlib import Path
    racine = Path(__file__).resolve().parents[2]
    candidats = list((racine / "mon-agent").glob("*trace*")) + list((racine / "mon-agent").glob("*requete*"))
    assert candidats, "livrable manquant : requêtes de trace de l'atelier 11"
