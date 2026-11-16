"""Inert agent, used by `workshop check-inert` to check that the workshop tests are demanding.

It answers every turn with the same cautious French sentence (the default answer of
the simulated model), never calls the model nor a tool, writes a minimal trace, and
ships deliverables that only contain the expected keywords. Every workshop test must
fail against it: a test it passes establishes nothing about the workshop.
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
