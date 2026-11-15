
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
