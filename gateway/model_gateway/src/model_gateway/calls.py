"""Every model call, saved as one JSON file: the full input the model received and its answer.

The proxy sees every chat completion, whatever the mode (simulated, replay, live) and whatever
the harness does, so it is the one place that knows exactly what the model was given. Files go
under `settings.llm_calls_dir` (`.workshop/llm-calls/` by default), one folder per conversation:

    .workshop/llm-calls/<conversation_id>/call-0001.json

The conversation and the turn come from the `X-Workshop-Conversation` and `X-Workshop-Turn`
headers, which `agent_sdk.model_client.ModelClient` adds during a turn of the gateway. A call
without them (judge, script, direct HTTP call) goes to `_hors-conversation/`.

No secret is written: neither the request headers nor the course token, and any token found
in the payload (JWT, `Bearer ...`, keys named like a secret, configured secrets) is masked.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workshop_config import repo_path, settings

logger = logging.getLogger("llm_proxy.calls")

CONVERSATION_HEADER = "X-Workshop-Conversation"
TURN_HEADER = "X-Workshop-Turn"
NO_CONVERSATION = "_hors-conversation"
SCHEMA = 1

_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
_FILE = re.compile(r"^call-(\d{4,})\.json$")
_JWT = re.compile(r"eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]+")
_BEARER = re.compile(r"(?i)\bbearer\s+[^\s\"']+")
_SECRET_KEYS = {
    "authorization", "api_key", "api-key", "apikey", "app_token", "access_token", "refresh_token",
    "id_token", "token", "password", "secret", "client_secret",
}
MASK = "[masqué]"
_lock = threading.Lock()


def folder() -> Path | None:
    return repo_path(settings.llm_calls_dir) if settings.llm_calls_dir else None


def conversation_folder(conversation_id: str | None) -> str:
    return conversation_id if conversation_id and _ID.match(conversation_id) else NO_CONVERSATION


def _literal_secrets() -> list[str]:
    values = (settings.azure_openai_api_key, settings.token_secret, settings.observation_token, settings.judge_api_key)
    return [v for v in values if v and len(v) >= 8]


def scrub(value: Any, secrets: list[str] | None = None) -> Any:
    """A copy of `value` without tokens nor keys."""
    secrets = _literal_secrets() if secrets is None else secrets
    if isinstance(value, dict):
        return {
            k: MASK if str(k).lower() in _SECRET_KEYS and isinstance(v, str) and v else scrub(v, secrets)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [scrub(v, secrets) for v in value]
    if isinstance(value, str):
        text = _BEARER.sub("Bearer " + MASK, _JWT.sub(MASK, value))
        for secret in secrets:
            text = text.replace(secret, MASK)
        return text
    return value


def system_sha256(messages: list[dict[str, Any]]) -> str:
    """Fingerprint of the system message of a request ("" without one)."""
    system = next((m.get("content") for m in messages if m.get("role") == "system"), None)
    return hashlib.sha256(str(system).encode("utf-8")).hexdigest() if isinstance(system, str) else ""


def _turn(value: str | int | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def _answer(response: dict[str, Any]) -> dict[str, Any]:
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    return {
        "model": response.get("model"),
        "content": message.get("content"),
        "tool_calls": message.get("tool_calls") or [],
        "finish_reason": choice.get("finish_reason"),
        "usage": response.get("usage") or {},
        "message": message,
    }


def record(
    *,
    conversation_id: str | None,
    turn: str | int | None,
    student: str,
    mode: str,
    request: dict[str, Any],
    response: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
    duration_ms: int = 0,
) -> Path | None:
    """Saves one model call. Never raises: a failed write only logs a warning."""
    root = folder()
    if root is None:
        return None
    name = conversation_folder(conversation_id)
    entry: dict[str, Any] = {
        "schema": SCHEMA,
        "conversation_id": name,
        "turn": _turn(turn),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": int(duration_ms),
        "student": student,
        "mode": mode,
        "status": (error or {}).get("status", 200),
        "system_sha256": system_sha256(request.get("messages") or []),
        "request": request,
        "response": _answer(response) if response is not None else None,
        "error": error,
    }
    try:
        target = root / name
        with _lock:
            target.mkdir(parents=True, exist_ok=True)
            index = 1 + max((int(m.group(1)) for m in map(_FILE.match, os.listdir(target)) if m), default=0)
            entry["call"] = index
            path = target / f"call-{index:04d}.json"
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(scrub(entry), ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporary, path)
        return path
    except OSError as exc:
        logger.warning("model call not saved: %s", exc)
        return None


def _files(name: str) -> list[tuple[int, Path]]:
    root = folder()
    if root is None or not _ID.match(name):
        return []
    target = root / name
    if not target.is_dir():
        return []
    found = [(int(m.group(1)), target / m.group(0)) for m in map(_FILE.match, os.listdir(target)) if m]
    return sorted(found)


def _read(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _last_user_text(entry: dict[str, Any] | None) -> str:
    messages = ((entry or {}).get("request") or {}).get("messages") or []
    text = next((m.get("content") for m in reversed(messages) if m.get("role") == "user"), "")
    return text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)


def conversations() -> list[dict[str, Any]]:
    """One summary per conversation folder, the most recent first."""
    root = folder()
    if root is None or not root.is_dir():
        return []
    result = []
    for child in root.iterdir():
        files = _files(child.name) if child.is_dir() else []
        if not files:
            continue
        first, last = _read(files[0][1]), _read(files[-1][1])
        result.append(
            {
                "id": child.name,
                "calls": len(files),
                "last_call": files[-1][0],
                "turns": (last or {}).get("turn"),
                "first_message": _last_user_text(first)[:200],
                "recorded_at": (last or {}).get("recorded_at") or "",
            }
        )
    return sorted(result, key=lambda c: c["recorded_at"], reverse=True)


def calls(name: str, since: int = 0) -> list[dict[str, Any]] | None:
    """The calls of a conversation, in order (those after `since` only); None when unknown."""
    files = _files(name)
    if not files:
        return None
    entries = []
    for index, path in files:
        if index > since:
            entry = _read(path)
            if entry is not None:
                entry.setdefault("call", index)
                entry["file"] = path.name
                entries.append(entry)
    return entries
