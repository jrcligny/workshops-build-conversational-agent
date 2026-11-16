"""Tests de bout en bout de l'atelier 05. Ils doivent échouer sur la coquille vide."""

import pytest

from tests.communs.tours import appliquer_grille, entree, journal_metier, outils, plat, tour_reussi

pytestmark = pytest.mark.atelier


def test_homonymes_plusieurs_candidats(client_chat):
    tour, trace = tour_reussi(client_chat, "Quelles sont les commandes de Léa Martin ?")
    texte = tour.texte.lower()
    assert "lille" in texte and "lyon" in texte
    # l'agent ne choisit pas un des deux à la place de l'utilisateur
    assert "laquelle" in texte or "plusieurs" in texte or "homonym" in texte or "deux" in texte or "?" in tour.texte
    assert outils(trace)


def test_filtre_retard_applique_par_l_outil(client_chat, observation):
    observation.reinitialiser("volume")
    tour, trace = tour_reussi(client_chat, "Quelles sont les commandes en retard de Transports Morel ?")
    assert tour.texte
    assert outils(trace)
    plat_outils = str(outils(trace)).lower()
    assert "retard" in plat_outils or "en_retard" in plat_outils or "late" in plat_outils
    # le filtre est dans l'appel, pas seulement dans une sélection faite par le modèle après coup
    assert any(
        "retard" in str((o.get("arguments") or o.get("parametres") or o)).lower()
        for o in outils(trace)
    )
