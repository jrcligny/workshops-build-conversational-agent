"""Horloge figée pour des retards stables."""

from __future__ import annotations

from datetime import datetime

from socle.config import reglages

HORLOGE = datetime.fromisoformat(reglages.horloge_figee)


def maintenant() -> datetime:
    return HORLOGE
