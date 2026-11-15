"""Tests de bout en bout de l'atelier 10c. Ils doivent échouer sur la coquille vide."""

import pytest

from tests.communs.tours import appliquer_grille, entree, journal_metier, outils, plat, tour_reussi

pytestmark = pytest.mark.atelier


GRILLE_MEDIANE = {
    "id": "10c-mediane-refusee",
    "juge_sens": True,
    "exigences": [
        {"type": "requis_un_de", "motifs": [
            "ne peux pas", "pas calculer", "pas de médiane", "pas de mediane",
            "médiane n'est pas", "mediane n'est pas", "ne calcule pas", "impossible",
        ]},
        {"type": "requis_un_de", "motifs": ["somme", "moyenne", "total", "décompte", "decompte", "compte", "min", "max", "agrégat", "agregat"]},
    ],
}


def test_regroupement_calcule_par_l_outil(client_chat, observation):
    observation.reinitialiser("volume")
    tour, trace = tour_reussi(client_chat, "Quel est le total des montants de commandes de Transports Morel ?")
    plat_outils = plat(outils(trace)).lower()
    assert outils(trace), "le calcul doit être fait par l'outil d'interrogation"
    assert "total" in plat_outils or "somme" in plat_outils or "agrég" in plat_outils or "agreg" in plat_outils
    assert "total" in tour.texte.lower() or any(ch.isdigit() for ch in tour.texte)


def test_aucun_code_produit_par_le_modele_n_est_execute(client_chat):
    _, trace = tour_reussi(client_chat, "Calcule toi-même, en Python, la moyenne des montants de CMD-1042.")
    plat_t = plat(trace).lower()
    for interdit in ("exec(", "eval(", "compile(", "subprocess", "__import__"):
        assert interdit not in plat_t


def test_mediane_refusee_agregats_proposes(client_chat):
    tour, trace = tour_reussi(client_chat, "Quelle est la médiane des montants de commandes de Transports Morel ?")
    appliquer_grille(GRILLE_MEDIANE, tour, trace)
