"""JSONL traces, one per turn, without secrets."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workshop_config import settings

_lock = threading.Lock()
TRACE_FILE = "turns.jsonl"


def folder() -> Path:
    path = Path(settings.traces_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def new_id() -> str:
    return uuid.uuid4().hex


def write(trace: dict[str, Any]) -> Path:
    trace = dict(trace)
    trace.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    # Minimal masking: never a key nor a token.
    for secret in ("azure_openai_api_key", "api_key", "authorization", "token"):
        trace.pop(secret, None)
    path = folder() / TRACE_FILE
    with _lock:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(trace, ensure_ascii=False) + "\n")
    return path


def read_all() -> list[dict[str, Any]]:
    path = folder() / TRACE_FILE
    if not path.exists():
        return []
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            lines.append(json.loads(line))
    return lines


def clear() -> None:
    path = folder() / TRACE_FILE
    if path.exists():
        path.unlink()
