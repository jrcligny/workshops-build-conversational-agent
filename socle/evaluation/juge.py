
"""Juge : en conception, scripté ou rejoué ; plus tard, via le proxy Azure."""

from __future__ import annotations

from typing import Any


def juger_script(grille: dict[str, Any], dialogue: dict[str, Any], verdict_attendu: str | None = None) -> dict[str, Any]:
    """Juge déterministe de conception.

    Si un verdict attendu est fourni (rejeu manuscrit), il est renvoyé tel quel.
    Sinon le juge se limite à des contrôles structurels ; il ne calibre pas une grille.
    """
    if verdict_attendu:
        return {
            "reussi": verdict_attendu == "reussi",
            "justification": "verdict rejoué (conception)",
            "extraits": [],
            "mode": "rejoue",
        }
    # Contrôle structurel minimal, sans prétendre évaluer le sens.
    texte = (dialogue.get("reponse") or "").strip()
    if not texte:
        return {
            "reussi": False,
            "justification": "aucune réponse d'assistant à juger",
            "extraits": [],
            "mode": "simule",
        }
    return {
        "reussi": False,
        "justification": "juge réel non disponible en conception ; item à calibrer en phase B",
        "extraits": [texte[:200]],
        "mode": "simule",
        "a_calibrer": True,
    }
