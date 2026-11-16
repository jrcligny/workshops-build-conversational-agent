"""Emplacement et interface du confinement, sans politique appliquée.

À l'atelier 10d, le serveur d'outils tournera dans un conteneur (utilisateur
non privilégié, système de fichiers en lecture seule, proxy de sortie à liste
d'autorisation). Cette coquille expose seulement le contrat et l'emplacement
des fichiers ; elle n'applique aucune politique.
"""

from __future__ import annotations

from pathlib import Path

import yaml

DOSSIER = Path(__file__).resolve().parent
FICHIER_POLITIQUE = DOSSIER / "politique.yaml"


def politique() -> dict:
    data = yaml.safe_load(FICHIER_POLITIQUE.read_text(encoding="utf-8")) or {}
    return {
        "active": bool(data.get("active")),
        "liste_autorisation": list(data.get("liste_autorisation") or []),
        "limites": dict(data.get("limites") or {}),
        "emplacement": str(FICHIER_POLITIQUE),
    }


def politique_appliquee() -> bool:
    return politique()["active"]


def autorise_sortie(_url: str) -> bool | None:
    """Renvoie None tant qu'aucune politique n'est active (coquille)."""
    if not politique_appliquee():
        return None
    # L'implémentation de la liste d'autorisation est le travail de l'atelier 10d.
    raise NotImplementedError("politique de confinement à implémenter (atelier 10d)")
