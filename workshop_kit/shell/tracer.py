
"""Traces JSONL, une par tour, sans secret."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from socle.config import reglages

_lock = threading.Lock()


def dossier() -> Path:
    path = Path(reglages.traces_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def nouvel_id() -> str:
    return uuid.uuid4().hex


def ecrire(trace: dict[str, Any]) -> Path:
    trace = dict(trace)
    trace.setdefault("horodatage", datetime.now(timezone.utc).isoformat())
    # Masquage minimal : jamais de clé ni de jeton.
    for secret in ("azure_openai_api_key", "api_key", "authorization", "jeton"):
        trace.pop(secret, None)
    chemin = dossier() / "tours.jsonl"
    with _lock:
        with chemin.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(trace, ensure_ascii=False) + "\n")
    return chemin


def lire_tout() -> list[dict[str, Any]]:
    chemin = dossier() / "tours.jsonl"
    if not chemin.exists():
        return []
    lignes = []
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        if ligne.strip():
            lignes.append(json.loads(ligne))
    return lignes


def vider() -> None:
    chemin = dossier() / "tours.jsonl"
    if chemin.exists():
        chemin.unlink()
