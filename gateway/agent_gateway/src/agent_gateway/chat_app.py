"""Minimal chat interface: typed SSE events, consumed by the tests' client."""

from __future__ import annotations

import json
import logging
import threading
import uuid
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from workshop_config import repo_path, settings
from workshop_config.reload import (
    Signature,
    changed_files,
    describe_error,
    digest,
    purge_modules,
    source_signature,
)

from agent_sdk.context import clear_contexts, context, seed
from agent_sdk.contract import Event, HarnessNotImplemented, Message, TestUser
from agent_gateway.loader import NO_RESTART, MyAgentLoadError, load_harness, wait_for_mcp_server

app = FastAPI(title="Workshop chat interface", version="0.1.0")
log = logging.getLogger("uvicorn.error")

_conversations: dict[str, dict] = {}
_histories: dict[str, list[Message]] = defaultdict(list)
_confirmations: dict[str, bool] = {}
_interruptions: set[str] = set()
_harness = None
# Folder and signature of my-agent/ at the last load attempt; kept by reset_conversations.
_loaded: tuple[Path, Signature] | None = None
_mcp_ready: str | None = None
_reload_lock = threading.Lock()
_urls: dict[str, str] = {}


def configure(urls: dict[str, str] | None = None) -> None:
    global _urls
    _urls = urls or {}


def harness():
    """The harness of my-agent/, loaded again at the first turn after any change to its Python files.

    The modules of my-agent/ are then forgotten and imported again, and a new Harness replaces the
    previous one. The conversations (`agent_sdk.context`) are kept.
    """
    global _harness, _loaded, _mcp_ready
    with _reload_lock:
        folder = repo_path(settings.my_agent_dir).resolve()
        current = source_signature(folder)
        if _harness is None or _loaded != (folder, current):
            changed: list[str] = []
            if _loaded is not None and _loaded != (folder, current):
                previous_folder, previous = _loaded
                changed = changed_files(previous, current) if previous_folder == folder else ["*"]
                purge_modules(previous_folder, changed if previous_folder == folder else ())
                purge_modules(folder)
            _harness = None
            _loaded = (folder, current)
            try:
                _harness = load_harness()
            except HarnessNotImplemented:
                raise
            except Exception as exc:  # noqa: BLE001 - any error of the student's code is reported
                detail = describe_error(exc, folder)
                log.exception("my-agent could not be loaded: %s", detail)
                raise MyAgentLoadError(f"my-agent could not be loaded: {detail}. {NO_RESTART}") from exc
            if changed:
                log.info("my-agent reloaded (changed: %s)", ", ".join(changed))
        signature = digest(current)
        if _mcp_ready != signature:
            try:
                wait_for_mcp_server(signature)
            except MyAgentLoadError as exc:
                log.error("%s", exc)
                raise
            _mcp_ready = signature
        return _harness


def reset_conversations() -> None:
    _conversations.clear()
    _histories.clear()
    _confirmations.clear()
    _interruptions.clear()
    clear_contexts()
    global _harness
    _harness = None


class ConversationIn(BaseModel):
    user_id: str = "camille-renard"
    role: str = "customer_service"
    organization: str = "organization-a"
    app_token: str | None = None
    # A signed-in interface hands the agent an entry token for the user (workshop 07).
    sign_in: bool = False
    limits: dict | None = None


class MessageIn(BaseModel):
    text: str
    attachments: list[str] = []
    interrupt: bool = False


class ConfirmationIn(BaseModel):
    confirmed: bool = True


class HistoryIn(BaseModel):
    messages: list[dict]
    append: bool = False


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/users")
def list_users():
    """Test identities of the seeded datasets, offered by the identity selector of chat-ui."""
    from business_api.seed_data import USERS

    return {
        "users": [
            {"user_id": user_id, "name": name, "role": role, "organization": organization}
            for user_id, name, role, organization in USERS
        ]
    }


@app.get("/attachments")
def list_attachments():
    """Contract entry point for workshop 14. The area is empty in the shell."""
    from agent_sdk.attachments import list_attachments as _list

    return {"attachments": _list()}


@app.post("/conversations")
def create_conversation(body: ConversationIn):
    conversation_id = uuid.uuid4().hex
    if body.sign_in and not body.app_token:
        from business_api.auth import issue_token

        body.app_token = issue_token(body.user_id, body.role, body.organization, typ="entry")
    _conversations[conversation_id] = body.model_dump()
    _histories[conversation_id] = []
    return {"id": conversation_id, "user": body.model_dump()}


@app.post("/conversations/{conversation_id}/history")
def load_history(conversation_id: str, body: HistoryIn):
    """Starts a conversation from a written history (tests, demonstrations), instead of playing it.

    The messages (user, assistant with `tool_calls`, `tool` results) become the agent's context
    (`agent_sdk.context.seed`); the transcript shown keeps, per turn, the user's text and the last
    non-empty assistant text. With `append`, the written history follows the turns already
    played (the context and the transcript are extended, the summary and the working state are kept;
    without `append`, the state is emptied and the agent rebuilds it from the messages)."""
    if conversation_id not in _conversations:
        raise HTTPException(status_code=404, detail="unknown conversation")
    if body.append:
        ctx = context(conversation_id)
        seed(conversation_id, ctx.messages + body.messages, ctx.summary, ctx.state)
        transcript = list(_histories.get(conversation_id, []))
    else:
        seed(conversation_id, body.messages)
        transcript = []
    for message in body.messages:
        role, content = message.get("role"), message.get("content") or ""
        if role == "user":
            transcript += [Message(role="user", content=content), Message(role="assistant", content="")]
        elif role == "assistant" and content and transcript:
            transcript[-1] = Message(role="assistant", content=content)
    _histories[conversation_id] = transcript
    return {"turns": len(transcript) // 2}


@app.post("/conversations/{conversation_id}/confirmation")
def confirm(conversation_id: str, body: ConfirmationIn):
    """The user's confirmation gesture (workshop 07)."""
    if conversation_id not in _conversations:
        raise HTTPException(status_code=404, detail="unknown conversation")
    _confirmations[conversation_id] = bool(body.confirmed)
    return {"ok": True, "confirmed": bool(body.confirmed)}


@app.post("/conversations/{conversation_id}/interruption")
def interrupt(conversation_id: str):
    """Interruption request for the current turn (workshop 05)."""
    if conversation_id not in _conversations:
        raise HTTPException(status_code=404, detail="unknown conversation")
    _interruptions.add(conversation_id)
    return {"ok": True}


@app.post("/conversations/{conversation_id}/messages")
def send_message(conversation_id: str, body: MessageIn):
    if conversation_id not in _conversations:
        raise HTTPException(status_code=404, detail="unknown conversation")
    meta = _conversations[conversation_id]
    user = TestUser(
        id=meta["user_id"],
        role=meta["role"],
        organization=meta["organization"],
        app_token=meta.get("app_token"),
    )
    history = list(_histories[conversation_id])
    # An interruption applies to the next turn only.
    interrupt_requested = conversation_id in _interruptions or body.interrupt
    _interruptions.discard(conversation_id)
    # A confirmation gesture applies to the next turn only: a later draft needs a new gesture.
    confirmation = _confirmations.pop(conversation_id, False)
    limits = meta.get("limits")

    def stream():
        try:
            events = list(
                harness().turn(
                    conversation_id,
                    body.text,
                    user,
                    history,
                    attachments=body.attachments,
                    interrupt_requested=interrupt_requested,
                    confirmation=confirmation,
                    limits=limits,
                )
            )
        except HarnessNotImplemented as exc:
            yield _sse(Event(type="error", data={"detail": str(exc)}))
            yield _sse(Event(type="end", data={"ok": False, "detail": str(exc)}))
            return
        except MyAgentLoadError as exc:
            yield _sse(Event(type="error", data={"detail": str(exc)}))
            yield _sse(Event(type="end", data={"ok": False, "detail": str(exc)}))
            return
        except NotImplementedError as exc:
            detail = str(exc) or "Harness not implemented (empty shell)."
            yield _sse(Event(type="error", data={"detail": detail}))
            yield _sse(Event(type="end", data={"ok": False, "detail": detail}))
            return
        except Exception as exc:  # noqa: BLE001
            yield _sse(Event(type="error", data={"detail": f"{type(exc).__name__}: {exc}"}))
            yield _sse(Event(type="end", data={"ok": False, "detail": str(exc)}))
            return
        text = ""
        for event in events:
            if event.type == "text":
                text += event.data.get("content", "")
            yield _sse(event)
        if not any(event.type == "end" for event in events):
            yield _sse(Event(type="end", data={"ok": True, "text": text}))
        # The shell only updates the history when the harness produced a successful end.
        if text:
            _histories[conversation_id].append(Message(role="user", content=body.text))
            _histories[conversation_id].append(Message(role="assistant", content=text))

    return StreamingResponse(stream(), media_type="text/event-stream")


def _sse(event: Event) -> str:
    return f"event: {event.type}\ndata: {json.dumps(event.data, ensure_ascii=False)}\n\n"
