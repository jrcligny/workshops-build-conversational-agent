"""OpenAI-compatible proxy: simulated, replay and live modes (Azure OpenAI, server-side key)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from workshop_kit.llm_proxy import live, replay, simulated
from workshop_kit.llm_proxy.tokens import STUDENTS, consume, issue_student_token, require_student, usage
from workshop_kit.shell.config import settings

logger = logging.getLogger("llm_proxy")

app = FastAPI(title="Model proxy", version="0.1.0")
_LOG: list[dict] = []
_SCRIPTS: list[dict] = []
_FAILURES: dict[str, bool] = {}


class ChatIn(BaseModel):
    model: str | None = None
    messages: list[dict[str, Any]]
    stream: bool = False
    tools: list[dict[str, Any]] | None = None
    temperature: float | None = None


class EmbeddingsIn(BaseModel):
    model: str | None = None
    input: str | list[str]


class ScriptsIn(BaseModel):
    scripts: list[dict[str, Any]] = Field(default_factory=list)


def _mode() -> str:
    return (settings.proxy_mode or "simulated").lower()


def _record(student: str, route: str, model: str, tokens: int, code: int) -> None:
    entry = {
        "student": student,
        "route": route,
        "model": model,
        "tokens": tokens,
        "code": code,
        "mode": _mode(),
    }
    _LOG.append(entry)
    # Never an Azure key in the logs.
    logger.info("proxy call student=%s route=%s tokens=%s code=%s", student, route, tokens, code)


def _scripted(messages: list[dict[str, Any]]) -> dict[str, Any] | None:
    """A loaded test script still takes precedence in live mode, so test scenarios stay reproducible."""
    if not _SCRIPTS:
        return None
    user_text = next((m.get("content") or "" for m in reversed(messages) if m.get("role") == "user"), "")
    for script in _SCRIPTS:
        if simulated._match(script, messages, user_text):
            return simulated.complete(messages, [script])
    return None


def _live_chat(body: ChatIn, student: str) -> dict[str, Any]:
    try:
        return live.chat(body.messages, model=body.model, tools=body.tools, temperature=body.temperature)
    except live.LiveError as exc:
        _record(student, "/v1/chat/completions", body.model or "", 0, exc.status_code)
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@app.get("/health")
def health():
    return {"status": "ok", "mode": _mode()}


@app.post("/v1/chat/completions")
def chat(body: ChatIn, student: dict = Depends(require_student)):
    if body.stream:
        # During design, streaming is simulated by a single response; the interface splits it if needed.
        pass
    if _FAILURES.get("primary_model"):
        model = body.model or ""
        # The fallback model, when requested explicitly, stays reachable.
        if "fallback" not in model.lower():
            _record(student["sub"], "/v1/chat/completions", model, 0, 503)
            raise HTTPException(status_code=503, detail="primary model unavailable")
    response = None
    if _mode() == "live":
        response = _scripted(body.messages) or _live_chat(body, student["sub"])
    if _mode() == "replay":
        response = replay.find(body.messages)
    if response is None:
        response = simulated.complete(body.messages, _SCRIPTS)
    tokens = int((response.get("usage") or {}).get("total_tokens") or 16)
    try:
        consume(student["sub"], tokens)
    except HTTPException as exc:
        _record(student["sub"], "/v1/chat/completions", response.get("model", ""), tokens, exc.status_code)
        raise
    _record(student["sub"], "/v1/chat/completions", response.get("model", ""), tokens, 200)
    return response


@app.post("/v1/embeddings")
def embeddings(body: EmbeddingsIn, student: dict = Depends(require_student)):
    # Embeddings stay deterministic in every mode: the document index is built with the same local vectors.
    texts = body.input if isinstance(body.input, list) else [body.input]
    response = simulated.embeddings(texts)
    tokens = int((response.get("usage") or {}).get("total_tokens") or len(texts))
    consume(student["sub"], tokens)
    _record(student["sub"], "/v1/embeddings", response.get("model", ""), tokens, 200)
    return response


@app.get("/log")
def read_log(student: dict = Depends(require_student)):
    # During design, a test student may read the test log.
    return list(_LOG)


@app.post("/_test/scripts")
def load_scripts(body: ScriptsIn, student: dict = Depends(require_student)):
    _SCRIPTS.clear()
    _SCRIPTS.extend(body.scripts)
    return {"n": len(_SCRIPTS)}


@app.post("/_test/token")
def test_token(student_id: str = "test-student"):
    """Issues a course token. No Azure key is ever returned."""
    return {"student_id": student_id, "token": issue_student_token(student_id), "predefined": list(STUDENTS)}


@app.get("/_test/usage/{student_id}")
def api_usage(student_id: str):
    return usage(student_id)


class ProxyFailureIn(BaseModel):
    type: str
    active: bool = True


@app.post("/_test/failures")
def arm_proxy_failure(body: ProxyFailureIn):
    """Arms a test failure (primary model unavailable, workshop 18)."""
    _FAILURES[body.type] = body.active
    return {"type": body.type, "active": body.active}


def clear_log() -> None:
    _LOG.clear()
    _SCRIPTS.clear()
    _FAILURES.clear()
