"""Tests de bout en bout de l'atelier 07. Ils doivent échouer sur la coquille vide."""

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

def test_liste_bornee_et_total_declare(client_chat, observation):
    observation.reinitialiser("volume")
    tour, trace = _tour_reussi(client_chat, "Quelles sont les commandes en retard de Transports Morel, et combien y en a-t-il ?")
    assert "total" in tour.texte.lower() or "retard" in tour.texte.lower()
    assert trace.get("outils")


def test_compaction_au_dela_du_seuil(client_chat):
    trace = None
    for i in range(10):
        _, trace = _tour_reussi(
            client_chat,
            f"Précision numéro {i} concernant Martin Durand et la commande CMD-1042 : je ne veux que les commandes livrées.",
        )
    assert "compaction" in str(trace).lower() or (trace.get("entree") or {}).get("compaction")
    plat = str(trace.get("entree") or {})
    assert "CMD-1042" in plat or "C-DURAND" in plat
