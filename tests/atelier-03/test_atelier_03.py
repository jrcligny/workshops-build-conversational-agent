"""Tests de bout en bout de l'atelier 03. Ils doivent échouer sur la coquille vide."""

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

def test_contrat_et_prompt_court(client_chat):
    tour, trace = _tour_reussi(client_chat, "Où en est la commande CMD-1042 de Martin Durand ?")
    prompt = (trace.get("entree") or {}).get("system_prompt") or ""
    assert prompt.strip(), "un system prompt doit figurer dans la trace"
    assert len(prompt.split()) < 800
    for interdit in ("CMD-1042", "livrée", "livree", "Procédure — Livraisons"):
        assert interdit.lower() not in prompt.lower()


def test_refus_sans_source_y_compris_si_le_statut_est_juste(client_chat, observation):
    etat = observation.etat("CMD-1042")
    assert etat["commande"]["statut"] == "livree"
    tour, _ = _tour_reussi(client_chat, "Où en est la commande CMD-1042 de Martin Durand ?")
    texte = tour.texte.lower()
    assert "livr" not in texte
    journal = [e for e in observation.journal() if not str(e.get("route", "")).startswith("/observation")]
    assert journal == []


def test_historique_rejoue_au_second_tour(client_chat):
    _tour_reussi(client_chat, "Bonjour, je m'appelle Camille.")
    _, trace = _tour_reussi(client_chat, "Tu te souviens de mon prénom ?")
    historique = (trace.get("entree") or {}).get("historique") or []
    plat = " ".join((m.get("contenu") or m.get("content") or "") for m in historique).lower()
    assert "camille" in plat or "bonjour" in plat
