"""Tests de bout en bout de l'atelier 17. Ils doivent échouer sur la coquille vide."""

from pathlib import Path

import pytest

from tests.communs.tours import plat, tour_reussi

pytestmark = pytest.mark.atelier

CAS_LIMITES = [
    "reference-approximative",
    "homonymes",
    "resultat-tronque-total",
    "demande-hors-perimetre",
    "ecriture-apres-piece-jointe",
    "question-sans-reponse-documentaire",
    "utilisateur-sans-droit-ecriture",
    "facture-en-double",
]

RACINE = Path(__file__).resolve().parents[2]


def test_traces_masquees(client_chat, traces):
    tour_reussi(client_chat, "Où en est la commande CMD-1042 ?")
    plat_t = plat(traces.dernier()).lower()
    assert "authorization" not in plat_t and "bearer " not in plat_t
    assert "azure_openai_api_key" not in plat_t


def test_jeu_et_rapport_de_parcours():
    racine = RACINE / "mon-agent"
    rapport = racine / "rapport-parcours.md"
    if not rapport.exists():
        candidats = (
            list(racine.glob("rapport*parcours*"))
            + list(racine.glob("*parcours*.json"))
            + list(racine.glob("*parcours*.md"))
        )
        assert candidats, "rapport de parcours manquant (un rapport par parcours)"
        rapport = candidats[0]
    texte = rapport.read_text(encoding="utf-8").lower()
    for cas in CAS_LIMITES:
        variants = {cas, cas.replace("-", " "), cas.replace("-", "_")}
        assert any(v in texte for v in variants), (
            f"le jeu de parcours doit couvrir le cas limite {cas!r} et le rapport doit en rendre compte"
        )
    assert "répét" in texte or "repet" in texte or "k/" in texte or "essais" in texte
    assert "fait" in texte or "déterministe" in texte or "deterministe" in texte
