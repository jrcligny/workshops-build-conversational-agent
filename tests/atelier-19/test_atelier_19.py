"""Tests de bout en bout de l'atelier 19. Ils doivent échouer sur la coquille vide."""

import pytest

pytestmark = pytest.mark.atelier


def test_specification_et_controle_present():
    from pathlib import Path

    racine = Path("mon-agent")
    candidats = []
    for motif in ("*specif*", "*controle*", "*contrôle*"):
        candidats.extend(p for p in racine.glob(motif) if p.is_file() and p.stat().st_size > 80)
    dossier_specs = racine / "mode-local" / "specifications"
    if dossier_specs.is_dir():
        candidats.extend(
            p
            for p in dossier_specs.iterdir()
            if p.is_file() and p.name != ".gitkeep" and p.stat().st_size > 80
        )
    assert candidats, "spécification du contrôle de l'atelier 19 manquante"
