"""Tests de bout en bout de l'atelier 04. Ils doivent échouer sur la coquille vide."""

import pytest

from tests.communs.tours import appliquer_grille, entree, journal_metier, outils, plat, tour_reussi

pytestmark = pytest.mark.atelier


def _statuts_outils(trace) -> list[str]:
    valeurs = []
    for appel in outils(trace):
        resultat = appel.get("resultat") or appel.get("sortie") or appel
        valeurs.append(str(resultat.get("statut") or resultat.get("status") or resultat).lower())
    return valeurs


def test_consultation_commande_exacte(client_chat):
    tour, trace = tour_reussi(client_chat, "Où en est la commande CMD-1042 de Martin Durand ?")
    assert any("commande" in str(o).lower() for o in outils(trace))
    assert "livr" in tour.texte.lower()
    assert len(outils(trace)) <= 1, "au plus un appel d'outil par message"
    statuts = _statuts_outils(trace)
    assert any(s for s in statuts if "ok" in s or "reussi" in s or "succ" in s or "trouve" in s or "trouv" in s)


def test_reference_inversee_signalee(client_chat):
    tour, trace = tour_reussi(client_chat, "Où en est la commande CMD-1402 ?")
    assert "1042" in tour.texte
    assert "1402" in tour.texte or "écart" in tour.texte.lower() or "ecart" in tour.texte.lower() or "proche" in tour.texte.lower() or "approxim" in tour.texte.lower()
    assert outils(trace)
    assert len(outils(trace)) <= 1


def test_commande_supprimee_jamais_suggeree(client_chat):
    tour, trace = tour_reussi(client_chat, "Où en est la commande CMD-0881 ?")
    texte = tour.texte.lower()
    assert "0881" not in texte or all(mot in texte for mot in ("pas",)) and "sugg" not in texte
    # ni suggestion d'une commande exclue, ni présentation comme trouvée
    for appel in outils(trace):
        plat_appel = str(appel).lower()
        if "0881" in plat_appel:
            assert "exclu" in plat_appel or "absent" in plat_appel or "introuv" in plat_appel or "supprim" in plat_appel
    statuts = _statuts_outils(trace)
    assert any("absent" in s or "erreur" in s or "exclu" in s or "introuv" in s or "none" in s or "vide" in s for s in statuts) or "pas" in texte
