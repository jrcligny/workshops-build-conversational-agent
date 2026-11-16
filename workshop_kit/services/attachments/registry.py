"""Zone de pièces jointes en lecture seule — coquille vide (atelier 15)."""

from __future__ import annotations

from pathlib import Path

from socle.config import reglages

EXTENSIONS = {".txt", ".md", ".pdf", ".csv"}


def dossier() -> Path:
    return Path(reglages.pieces_jointes_dir)


def lister() -> list[dict]:
    """Fichiers déposés dans la zone, hors documentation et sentinelles."""
    racine = dossier()
    if not racine.is_dir():
        return []
    pieces = []
    for chemin in sorted(racine.iterdir()):
        if not chemin.is_file():
            continue
        if chemin.name.startswith("."):
            continue
        if chemin.suffix.lower() == ".py" or chemin.name.upper() == "README.MD":
            continue
        if chemin.suffix.lower() not in EXTENSIONS and chemin.suffix:
            continue
        pieces.append({"id": chemin.name, "nom": chemin.name, "chemin": str(chemin)})
    return pieces
