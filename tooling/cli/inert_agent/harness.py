"""Inert agent of `workshop check-inert`: it replaces the bootstrap harness of my-agent/.

The bootstrap converses through the model; this one does not. It answers every turn with the
same cautious sentence, calls neither the model nor a tool, and writes the base trace, so that
every workshop test, public and private, fails against it.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from agent_sdk import events
from agent_sdk.trace import Tracer
from agent_sdk.contract import Event, Message, TestUser

ANSWER = (
    "Je n'ai pas accès aux données de l'application et je ne peux pas affirmer "
    "l'état d'une commande précise. Pouvez-vous préciser votre demande ?"
)
SYSTEM_PROMPT_FILE = Path(__file__).with_name("system_prompt.md")


def load_system_prompt() -> str:
    text = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()


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
        tracer = Tracer(conversation_id, user, message)
        # No model receives the history, so none is traced (workshop 03).
        tracer.input(system_prompt=load_system_prompt(), history=[])
        tracer.output(ANSWER)
        tracer.write()
        yield events.text(ANSWER)
        yield events.end(ANSWER)
