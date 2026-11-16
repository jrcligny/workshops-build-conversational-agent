
"""Rejeu de trajectoires écrites à la main ou enregistrées plus tard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RACINE = Path(__file__).resolve().parent / "rejeux"


def charger(nom: str) -> dict[str, Any] | None:
    chemin = RACINE / f"{nom}.json"
    if not chemin.exists():
        return None
    return json.loads(chemin.read_text(encoding="utf-8"))


def trouver(messages: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not RACINE.exists():
        return None
    dernier = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            dernier = msg.get("content") or ""
            break
    for chemin in RACINE.glob("*.json"):
        data = json.loads(chemin.read_text(encoding="utf-8"))
        if data.get("si_contient") and data["si_contient"].lower() in dernier.lower():
            return data.get("reponse")
    return None
