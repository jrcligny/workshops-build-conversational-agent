"""Tests de bout en bout de l'atelier 11. Ils doivent échouer sur la coquille vide."""

import pytest

from tests.communs.tours import appliquer_grille, entree, journal_metier, outils, plat, tour_reussi

pytestmark = pytest.mark.atelier


import importlib.util
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]


def _charger_requetes():
    fichier = RACINE / "mon-agent" / "requetes_trace.py"
    assert fichier.is_file(), (
        "livrable manquant : mon-agent/requetes_trace.py "
        "(fonctions part_lectures_intermediaires et domaines_incompatibles)"
    )
    spec = importlib.util.spec_from_file_location("requetes_trace_etudiant", fichier)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _traces_exemple() -> list[dict]:
    chemin = Path(__file__).parent / "traces-exemple.jsonl"
    return [json.loads(ligne) for ligne in chemin.read_text(encoding="utf-8").splitlines() if ligne.strip()]


def test_requetes_de_trace_presentes_et_executables():
    module = _charger_requetes()
    traces = _traces_exemple()
    assert hasattr(module, "part_lectures_intermediaires"), "fonction part_lectures_intermediaires manquante"
    assert hasattr(module, "domaines_incompatibles"), "fonction domaines_incompatibles manquante"
    parts = module.part_lectures_intermediaires(traces)
    incompatibles = module.domaines_incompatibles(traces)
    assert isinstance(parts, list) and parts, "la part des lectures intermédiaires doit être calculée tour par tour"
    assert any("t1" in plat(p) or p.get("tour_id") == "t1" or "0.6" in plat(p) or (isinstance(p, dict) and p.get("part", 0) >= 0.5) for p in parts)
    assert isinstance(incompatibles, list)
    # le second tour d'exemple mélange commandes et factures
    assert incompatibles, "le tour t2 mélange des domaines aux droits incompatibles et doit être signalé"
