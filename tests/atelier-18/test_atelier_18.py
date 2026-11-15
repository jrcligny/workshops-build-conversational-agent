"""Tests de bout en bout de l'atelier 18. Ils doivent échouer sur la coquille vide."""

import httpx
import pytest

from tests.communs.tours import appliquer_grille, journal_metier, plat, tour_reussi

pytestmark = pytest.mark.atelier

GRILLE_REPLI = {
    "id": "18-repli-puis-fin",
    "juge_sens": True,
    "exigences": [
        {
            "type": "requis_un_de",
            "motifs": ["repli", "secours", "alternatif", "indisponible", "pas pu", "échec", "echec"],
        },
    ],
}


def test_soumission_jamais_rejouee(client_chat, observation):
    observation.armer_panne("issue_inconnue", True)
    tour, _ = tour_reussi(client_chat, "Soumets la demande d'achat déjà préparée.")
    assert "vérif" in tour.texte.lower() or "verif" in tour.texte.lower()
    soumissions = [e for e in journal_metier(observation) if "soumet" in str(e).lower()]
    assert len(soumissions) <= 1


def test_repli_unique_puis_fin(client_chat, services):
    httpx.post(
        f"{services['proxy']}/_test/pannes",
        json={"type": "modele_principal", "active": True},
        timeout=10,
    )
    tour, trace = tour_reussi(client_chat, "Où en est la commande CMD-1042 de Martin Durand ?")
    plat_t = plat(trace).lower()
    assert "repli" in plat_t or "fallback" in plat_t or "modele_repli" in plat_t
    appliquer_grille(GRILLE_REPLI, tour, trace)


def test_versions_dans_la_trace(client_chat):
    _, trace = tour_reussi(client_chat, "Où en est la commande CMD-1042 ?")
    plat_t = plat(trace).lower()
    assert "version" in plat_t
    for composant in ("consigne", "skill", "outil", "index"):
        assert composant in plat_t, f"la trace doit porter la version de : {composant}"
