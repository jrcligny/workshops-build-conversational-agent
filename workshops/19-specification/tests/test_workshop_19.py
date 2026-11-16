"""Tests de bout en bout de l'atelier 19. Ils doivent échouer sur la coquille vide."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

pytestmark = pytest.mark.atelier

RACINE = Path(__file__).resolve().parents[2]


def _somme(racine: Path) -> str:
    h = hashlib.sha256()
    fichiers = [
        c for c in racine.rglob("*") if c.is_file() and c.name != "somme-parcours.sha256"
    ]
    for chemin in sorted(fichiers, key=lambda c: c.relative_to(racine).as_posix()):
        rel = chemin.relative_to(racine).as_posix()
        h.update(rel.encode())
        h.update(chemin.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
    return h.hexdigest()


def test_specification_implementation_et_essai_contre_sortie_fausse():
    specs_dir = RACINE / "mon-agent" / "mode-local" / "specifications"
    controles = RACINE / "mon-agent" / "mode-local" / "controles"
    specs = [
        p
        for p in specs_dir.rglob("*")
        if p.is_file() and p.name != ".gitkeep" and p.stat().st_size > 80
    ]
    assert specs, "spécification courte du contrôle manquante dans mon-agent/mode-local/specifications/"
    essais = [
        p
        for p in controles.rglob("*")
        if p.is_file() and p.name != ".gitkeep" and p.stat().st_size > 80
    ]
    assert essais, "implémentation ou essais du contrôle manquants dans mon-agent/mode-local/controles/"
    textes = "\n".join(p.read_text(encoding="utf-8", errors="ignore").lower() for p in essais)
    assert any(
        motif in textes
        for motif in ("sortie fausse", "volontairement fausse", "sortie_fausse", "false_output", "fake output")
    ), "au moins un essai doit soumettre au harness une sortie de modèle volontairement fausse"

    attendu = (RACINE / "tests" / "evaluation" / "somme-parcours.sha256").read_text(encoding="utf-8").strip()
    actuel = _somme(RACINE / "tests" / "evaluation")
    assert actuel == attendu, "le jeu de parcours d'évaluation a été modifié ; il doit rester intact"

    for p in (RACINE / "mon-agent" / "mode-local").rglob("*"):
        if p.is_file():
            contenu = p.read_text(encoding="utf-8", errors="ignore").lower()
            assert "tests/evaluation/reserve" not in contenu.replace("\\", "/")
