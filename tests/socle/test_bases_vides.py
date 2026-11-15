"""Bases vides de la coquille : emplacements et contrats présents, contenus vides."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import yaml

from services.confinement.interface import autorise_sortie, politique, politique_appliquee
from services.pieces_jointes.registre import lister as lister_pieces

pytestmark = pytest.mark.socle

RACINE = Path(__file__).resolve().parents[2]


def test_confinement_interface_sans_politique():
    pol = politique()
    assert pol["active"] is False
    assert pol["liste_autorisation"] == []
    assert politique_appliquee() is False
    assert autorise_sortie("https://exemple.invalid") is None
    assert (RACINE / "services" / "confinement" / "politique.yaml").is_file()


def test_catalogue_skills_vide():
    manifeste = yaml.safe_load(
        (RACINE / "services" / "catalogue" / "manifeste.yaml").read_text(encoding="utf-8")
    )
    assert "skills" in manifeste
    assert manifeste["skills"] == []
    dossier = RACINE / "services" / "catalogue" / "skills"
    assert dossier.is_dir()
    skills = [p for p in dossier.iterdir() if p.name != ".gitkeep"]
    assert skills == []


def test_pieces_jointes_zone_vide_et_point_d_entree(services):
    assert lister_pieces() == []
    r = httpx.get(f"{services['interface']}/pieces-jointes", timeout=5)
    assert r.status_code == 200
    assert r.json()["pieces_jointes"] == []


def test_mode_local_coding_agent_accueil_vide():
    racine = RACINE / "mon-agent" / "mode-local"
    assert (racine / "README.md").is_file()
    assert (racine / "specifications").is_dir()
    assert (racine / "controles").is_dir()
    livrables = [
        p
        for sous in (racine / "specifications", racine / "controles")
        for p in sous.iterdir()
        if p.name != ".gitkeep"
    ]
    assert livrables == []
