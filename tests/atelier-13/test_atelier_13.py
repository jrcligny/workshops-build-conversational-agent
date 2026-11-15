"""Tests de bout en bout de l'atelier 13. Ils doivent échouer sur la coquille vide."""

import pytest

from tests.communs.tours import appliquer_grille, entree, journal_metier, outils, plat, tour_reussi

pytestmark = pytest.mark.atelier


def test_recherche_documentaire_et_sources(client_chat):
    tour, trace = tour_reussi(client_chat, "Que prévoit la procédure lorsqu'une livraison arrive incomplète ?")
    assert "sources" in tour.types, "les sources affichées sont établies par le programme (événement sources)"
    assert outils(trace)
    assert "procédure" in tour.texte.lower() or "procedure" in tour.texte.lower() or "incompl" in tour.texte.lower()


def test_resultat_vide_declare(client_chat):
    tour, _ = tour_reussi(client_chat, "Que dit la documentation sur le voyage spatial des factures xyzzy-42 ?")
    texte = tour.texte.lower()
    assert "aucun" in texte or "pas trouvé" in texte or "pas trouve" in texte or "vide" in texte or "aucune" in texte


def test_filtrage_des_droits(client_chat):
    tour, trace = tour_reussi(client_chat, "Donne-moi la définition interne des statuts de facture, notamment « reglée ».")
    plat_t = (tour.texte + plat(outils(trace))).lower()
    # camille est chargé de clientèle : le document comptable ne doit pas lui être servi
    assert "comptable" not in plat_t or "pas le droit" in plat_t or "pas accès" in plat_t or "pas acces" in plat_t or "aucun" in plat_t


def test_version_retiree_absente(client_chat):
    tour, trace = tour_reussi(client_chat, "Quelle est la version actuelle de la procédure des livraisons incomplètes ?")
    plat_t = (tour.texte + plat(outils(trace))).lower()
    assert "2.1" in plat_t or "version" in plat_t
    assert "1.0" not in plat_t or "retir" in plat_t


def test_distinction_documentation_et_donnees(client_chat):
    tour, _ = tour_reussi(
        client_chat,
        "Que prévoit la procédure en cas de livraison incomplète, et où en est CMD-1042 ?",
    )
    texte = tour.texte.lower()
    assert "documentation" in texte or "procédure" in texte or "procedure" in texte or "sources" in tour.types
    assert "cmd-1042" in texte or "commande" in texte or "livr" in texte
