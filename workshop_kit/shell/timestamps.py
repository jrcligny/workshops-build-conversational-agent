"""Frozen clock, so that delivery delays stay stable."""

from __future__ import annotations

from datetime import datetime

from workshop_kit.shell.config import settings

CLOCK = datetime.fromisoformat(settings.frozen_clock)


def now() -> datetime:
    return CLOCK
