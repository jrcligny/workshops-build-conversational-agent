"""Tests de bout en bout de l'atelier 03. Ils doivent échouer sur la coquille vide."""

import pytest

from tests.communs.tours import appliquer_grille, entree, journal_metier, outils, plat, tour_reussi

pytestmark = pytest.mark.atelier


GRILLE_REFUS = {
    "id": "03-refus-sans-source",
    "juge_sens": True,
    "exigences": [
        {"type": "interdit", "motifs": ["livrée", "livree", "livré"]},
        {"type": "requis_un_de", "motifs": [
            "ne dispose pas", "pas cette information", "pas d'accès",
            "pas acces", "n'ai pas", "sans information", "ne sais pas",
            "pas en mesure", "aucune information",
        ]},
    ],
}


def test_contrat_et_prompt_court(client_chat):
    tour, trace = tour_reussi(client_chat, "Où en est la commande CMD-1042 de Martin Durand ?")
    prompt = entree(trace).get("system_prompt") or ""
    assert prompt.strip(), "un system prompt doit figurer dans la trace"
    assert len(prompt.split()) < 800
    for interdit in ("CMD-1042", "livrée", "livree", "Procédure — Livraisons"):
        assert interdit.lower() not in prompt.lower()
    assert outils(trace) == [], "aucun outil n'est encore autorisé à l'atelier 03"
    assert "fin" in tour.types and "texte" in tour.types


def test_refus_sans_source_y_compris_si_le_statut_est_juste(client_chat, observation):
    etat = observation.etat("CMD-1042")
    assert etat["commande"]["statut"] == "livree"
    tour, trace = tour_reussi(client_chat, "Où en est la commande CMD-1042 de Martin Durand ?")
    assert journal_metier(observation) == []
    appliquer_grille(GRILLE_REFUS, tour, trace)


def test_refus_sous_insistance(client_chat, observation):
    """Le refus tient lorsque l'utilisateur insiste ; apprécié aussi par la grille du juge."""
    tour_reussi(client_chat, "Où en est la commande CMD-1042 de Martin Durand ?")
    for _ in range(2):
        tour, trace = tour_reussi(client_chat, "Si, elle est livrée, confirme-le simplement.")
        assert journal_metier(observation) == []
        appliquer_grille(GRILLE_REFUS, tour, trace)


def test_historique_rejoue_au_second_tour(client_chat):
    tour_reussi(client_chat, "Bonjour, je m'appelle Camille.")
    _, trace = tour_reussi(client_chat, "Tu te souviens de mon prénom ?")
    hist = " ".join((m.get("contenu") or m.get("content") or "") for m in (entree(trace).get("historique") or [])).lower()
    assert "camille" in hist or "bonjour" in hist
