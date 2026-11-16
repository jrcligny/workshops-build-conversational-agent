"""Replay of hand-written trajectories, or of trajectories recorded later."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent / "replays"


def load(name: str) -> dict[str, Any] | None:
    path = ROOT / f"{name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def find(messages: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not ROOT.exists():
        return None
    last = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last = msg.get("content") or ""
            break
    for path in ROOT.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("if_contains") and data["if_contains"].lower() in last.lower():
            return data.get("response")
    return None
