
"""Charge le harness de l'étudiant depuis mon-agent/, sans fournir de boucle."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from socle.config import reglages
from socle.harness_base.contrat import HarnessNonImplemente


def charger_harness():
    dossier = Path(reglages.mon_agent_dir)
    fichier = dossier / "harness.py"
    if not fichier.exists():
        raise HarnessNonImplemente(
            "Aucun fichier mon-agent/harness.py. Implémentez le contrat du harness (atelier 03)."
        )
    spec = importlib.util.spec_from_file_location("mon_agent_harness", fichier)
    if spec is None or spec.loader is None:
        raise HarnessNonImplemente("Impossible de charger mon-agent/harness.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["mon_agent_harness"] = module
    spec.loader.exec_module(module)
    if not hasattr(module, "Harness"):
        raise HarnessNonImplemente("mon-agent/harness.py doit exposer une classe Harness.")
    return module.Harness()


def charger_module_mon_agent(nom_fichier: str, nom_module: str):
    """Charge un module de la coquille mon-agent/ (harness, serveur MCP, …)."""
    dossier = Path(reglages.mon_agent_dir)
    fichier = dossier / nom_fichier
    if not fichier.exists():
        raise FileNotFoundError(f"Fichier manquant dans la coquille : {fichier}")
    spec = importlib.util.spec_from_file_location(nom_module, fichier)
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossible de charger {fichier}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[nom_module] = module
    spec.loader.exec_module(module)
    return module


def charger_serveur_mcp():
    return charger_module_mon_agent("serveur_mcp.py", "mon_agent_serveur_mcp")
