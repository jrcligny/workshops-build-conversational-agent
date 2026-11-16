"""Bootstrap of your agent.

This file is the entry point of your agent. It already converses: at each turn it sends the
model the system prompt (`system_prompt.md`, next to this file, read without its HTML
comments), the conversation history and the user's message, relays the model's answer to the
interface (`text`, then `end`) and writes the trace of the turn with `agent_helpers.trace.Tracer`.

What it does not do is the work of the workshops: no tool, no business data, no loop, no
compaction, no memory... Each workshop adds its part (see each `contrat.md`). The package
`agent_helpers/` holds the repetitive code (HTTP and MCP clients, event builders, tool
declarations, the tracer) so you can focus on each workshop's goal.

Your agent converses in French: the tests send French user turns and expect French
answers (code, comments and identifiers stay English).
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Iterator
from pathlib import Path

# The kit loads this file by path: make `agent_helpers` (next to it) importable.
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.append(str(Path(__file__).resolve().parent))

from agent_helpers import events  # noqa: E402
from agent_helpers.trace import Tracer  # noqa: E402
from workshop_kit.shell.harness_contract import Event, Message, TestUser  # noqa: E402
from workshop_kit.shell.model_client import ModelClient, ModelUnavailable  # noqa: E402

SYSTEM_PROMPT_FILE = Path(__file__).with_name("system_prompt.md")
UNAVAILABLE = "Le modèle est indisponible pour le moment. Réessayez dans un instant."


def load_system_prompt() -> str:
    text = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()


def model_client(timeout: float = 60.0) -> ModelClient:
    """The model, through the course proxy (`PROXY_URL`): `generate(messages, tools=None)`."""
    return ModelClient(os.environ.get("PROXY_URL", "http://127.0.0.1:8003"), timeout=timeout)


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
        system_prompt = load_system_prompt()
        tracer.input(system_prompt=system_prompt, history=history)
        messages = (
            [{"role": "system", "content": system_prompt}]
            + [{"role": m.role, "content": m.content} for m in history]
            + [{"role": "user", "content": message}]
        )
        try:
            response = tracer.call_model(model_client(), messages)
            answer = response["choices"][0]["message"].get("content") or ""
        except ModelUnavailable:
            answer = UNAVAILABLE
        tracer.output(answer)
        tracer.write()
        yield events.text(answer)
        yield events.end(answer)