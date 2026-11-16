"""Minimal chat interface: typed SSE events, consumed by the tests' client."""

from __future__ import annotations

import json
import uuid
from collections import defaultdict

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from workshop_kit.shell.harness_contract import Event, HarnessNotImplemented, Message, TestUser
from workshop_kit.shell.loader import load_harness

app = FastAPI(title="Workshop chat interface", version="0.1.0")

_conversations: dict[str, dict] = {}
_histories: dict[str, list[Message]] = defaultdict(list)
_confirmations: dict[str, bool] = {}
_interruptions: set[str] = set()
_harness = None
_urls: dict[str, str] = {}


def configure(urls: dict[str, str] | None = None) -> None:
    global _urls
    _urls = urls or {}


def harness():
    global _harness
    if _harness is None:
        _harness = load_harness()
    return _harness


def reset_conversations() -> None:
    _conversations.clear()
    _histories.clear()
    _confirmations.clear()
    _interruptions.clear()
    global _harness
    _harness = None


class ConversationIn(BaseModel):
    user_id: str = "camille-renard"
    role: str = "customer_service"
    organization: str = "organization-a"
    app_token: str | None = None
    limits: dict | None = None


class MessageIn(BaseModel):
    text: str
    attachments: list[str] = []
    interrupt: bool = False


class ConfirmationIn(BaseModel):
    confirmed: bool = True


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/attachments")
def list_attachments():
    """Contract entry point for workshop 15. The area is empty in the shell."""
    from workshop_kit.services.attachments.registry import list_attachments as _list

    return {"attachments": _list()}


@app.post("/conversations")
def create_conversation(body: ConversationIn):
    conversation_id = uuid.uuid4().hex
    _conversations[conversation_id] = body.model_dump()
    _histories[conversation_id] = []
    return {"id": conversation_id, "user": body.model_dump()}


@app.post("/conversations/{conversation_id}/confirmation")
def confirm(conversation_id: str, body: ConfirmationIn):
    """The user's confirmation gesture (workshop 10b)."""
    if conversation_id not in _conversations:
        raise HTTPException(status_code=404, detail="unknown conversation")
    _confirmations[conversation_id] = bool(body.confirmed)
    return {"ok": True, "confirmed": bool(body.confirmed)}


@app.post("/conversations/{conversation_id}/interruption")
def interrupt(conversation_id: str):
    """Interruption request for the current turn (workshop 06)."""
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
    interrupt_requested = conversation_id in _interruptions or body.interrupt
    confirmation = _confirmations.get(conversation_id, False)
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
