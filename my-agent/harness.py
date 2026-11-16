"""Bootstrap of your agent.

This file is the entry point of your agent. It already runs end to end: it receives a
turn, writes a trace and sends the interface its events (`text`, then `end`). What it
does not do is the work of the workshops: it calls neither the model nor any tool, and
answers every turn with the same cautious sentence. Every workshop test fails on it.

The system prompt lives in `system_prompt.md`, next to this file: `load_system_prompt()`
reads it at each turn, without its HTML comments.

Workshop 03 starts here: replace the fixed answer with a system prompt and a call to the
model (`agent_helpers.kit.model_client()`, wired to the proxy), keep the conversation
history, and enrich the trace as the workshops ask (see each `contrat.md`). The package
`agent_helpers/` holds the repetitive code (model client, HTTP and MCP clients, event
builders, tool declarations, base trace) so you can focus on each workshop's goal.

Your agent converses in French: the tests send French user turns and expect French
answers (code, comments and identifiers stay English).
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterator
from pathlib import Path

# The kit loads this file by path: make `agent_helpers` (next to it) importable.
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.append(str(Path(__file__).resolve().parent))

from agent_helpers import events  # noqa: E402
from agent_helpers.kit import Event, Message, TestUser, write_trace  # noqa: E402
from agent_helpers.trace import base_trace  # noqa: E402

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
        # One trace line per turn: the tests and your own queries read it.
        trace = base_trace(conversation_id, user, load_system_prompt(), history, message)
        trace["output"] = ANSWER
        write_trace(trace)
        yield events.text(ANSWER)
        yield events.end(ANSWER)
