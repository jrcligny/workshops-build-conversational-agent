"""Bootstrap of your agent.

This file is the entry point of your agent. It already runs end to end: it receives a
turn, writes a trace and sends the interface its events (`text`, then `end`). What it
does not do is the work of the workshops: it calls neither the model nor any tool, and
answers every turn with the same cautious sentence. Every workshop test fails on it.

Workshop 03 starts here: replace the fixed answer with a system prompt and a call to the
kit's model client (`workshop_kit.shell.model_client`, wired to the proxy), keep the
conversation history, and enrich the trace as the workshops ask (see each `contrat.md`).

Your agent converses in French: the tests send French user turns and expect French
answers (code, comments and identifiers stay English).
"""

from __future__ import annotations

from collections.abc import Iterator

from workshop_kit.shell import tracer
from workshop_kit.shell.harness_contract import Event, Message, TestUser

ANSWER = (
    "Je n'ai pas accès aux données de l'application et je ne peux pas affirmer "
    "l'état d'une commande précise. Pouvez-vous préciser votre demande ?"
)


class Harness:
    def turn(
        self,
        conversation_id: str,
        message: str,
        user: TestUser,
        history: list[Message],
        attachments: list[str] | None = None,
        interrupt_requested: bool = False,
        confirmation: bool = False,
        limits: dict | None = None,
    ) -> Iterator[Event]:
        # One trace line per turn: the tests and your own queries read it.
        tracer.write({
            "turn_id": tracer.new_id(),
            "conversation_id": conversation_id,
            "user": {"id": user.id, "role": user.role, "organization": user.organization},
            "input": {"system": "", "history": [], "message": message},
            "tools": [],
            "output": ANSWER,
        })
        yield Event(type="text", data={"content": ANSWER})
        yield Event(type="end", data={"ok": True, "text": ANSWER})
