"""Zone de pièces jointes en lecture seule — coquille vide (atelier 15)."""

from __future__ import annotations

from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
EXTENSIONS = {".txt", ".md", ".pdf", ".csv"}


def dossier() -> Path:
    return DOSSIER


def lister() -> list[dict]:
    """Fichiers déposés dans la zone, hors documentation et sentinelles."""
    pieces = []
    for chemin in sorted(DOSSIER.iterdir()):
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
