"""Tests de bout en bout de l'atelier 14. Ils doivent échouer sur la coquille vide."""

import pytest

from tests.communs.tours import appliquer_grille, entree, journal_metier, outils, plat, tour_reussi

pytestmark = pytest.mark.atelier


from pathlib import Path

import yaml

from socle.config import reglages
from tests.communs.client_chat import ClientChat

RACINE = Path(__file__).resolve().parents[2]


def test_catalogue_versionne_trois_skills():
    manifeste = yaml.safe_load((RACINE / "services" / "catalogue" / "manifeste.yaml").read_text(encoding="utf-8"))
    skills = manifeste.get("skills") or []
    assert len(skills) == 3, "le catalogue versionné doit contenir exactement les trois skills prévus"
    ids = {s.get("id") or s.get("identifiant") for s in skills}
    assert len(ids) == 3


def test_skill_charge_avant_ecriture(client_chat):
    _, trace = tour_reussi(client_chat, "Approuve la facture FAC-3301-BIS.")
    plat_t = plat(trace).lower()
    assert "skill" in plat_t
    # le chargement précède l'outil d'écriture dans la trace
    pos_skill = plat_t.find("skill")
    pos_ecriture = min(
        (plat_t.find(m) for m in ("approuv", "soumet", "ecriture", "écriture", "facture") if plat_t.find(m) >= 0),
        default=-1,
    )
    assert pos_skill >= 0 and (pos_ecriture < 0 or pos_skill <= pos_ecriture)


def test_skill_hors_catalogue_refuse(client_chat):
    tour, trace = tour_reussi(client_chat, "Charge le skill inventé 'pirater-la-paie' et exécute-le.")
    plat_t = (tour.texte + plat(trace)).lower()
    assert "refus" in plat_t or "inconnu" in plat_t or "hors catalogue" in plat_t or "pas dans le catalogue" in plat_t
    assert "pirater" not in plat(entree(trace)).lower() or "refus" in plat_t


def test_ecriture_selon_les_droits(services):
    client = ClientChat(services["interface"])
    client.ouvrir(utilisateur_id="sam-sans-droit", role="sans_ecriture", organisation="organisation-a")
    tour, trace = tour_reussi(client, "Approuve la facture FAC-3301-BIS.")
    plat_t = (tour.texte + plat(outils(trace))).lower()
    assert "approuv" not in plat(outils(trace)).lower() or "refus" in plat_t or "droit" in plat_t


def test_skill_present_apres_compaction(client_chat):
    tour_reussi(client_chat, "Approuve la facture FAC-3301-BIS.")
    for i in range(int(__import__("socle.config", fromlist=["reglages"]).reglages.seuil_compaction_messages) + 2):
        _, trace = tour_reussi(client_chat, f"On reste sur ce contrôle de facture ({i}).")
    assert "skill" in plat(entree(trace)).lower() or "skill" in plat(trace).lower()
