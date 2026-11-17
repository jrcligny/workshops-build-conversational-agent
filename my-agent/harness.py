"""Bootstrap of your agent.

This file is the entry point of your agent. It already converses: at each turn it sends the
model the system prompt (`system_prompt.md`, next to this file, read without its HTML
comments), the context of the conversation (`agent_sdk.context`: every message the model has
seen, kept between turns) and the user's message, relays the model's answer to the interface
(`text`, then `end`), records the turn in the context and writes the trace of the turn with
`agent_sdk.trace.Tracer`.

The `history` parameter is the transcript shown by the interface (texts only), for information:
the context of the model is `agent_sdk.context`, which also keeps tool calls and their results.

What it does not do is the work of the workshops: no tool, no business data, no loop, no
compaction, no memory... Each workshop adds its part (see each `contrat.md`). The package
`agent_sdk` (installed with this project, not edited) holds the repetitive code (contract types,
HTTP and MCP clients, event builders, tool declarations, the tracer) so you can focus on each
workshop's goal.

Your agent converses in French: the tests send French user turns and expect French
answers (code, comments and identifiers stay English).
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from pathlib import Path

from agent_sdk import events
from agent_sdk.context import context, unoffered_call_results
from agent_sdk.trace import Tracer
from agent_sdk.contract import Event, Message, TestUser
from agent_sdk.model_client import ModelClient, ModelUnavailable

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
        ctx = context(conversation_id)
        system_prompt = load_system_prompt()
        tracer.input(system_prompt=system_prompt, history=ctx.messages)
        turn_messages: list[dict] = [{"role": "user", "content": message}]
        answer = ""
        try:
            model = model_client()
            for _ in range(2):
                response = tracer.call_model(model, ctx.for_model(system_prompt) + turn_messages)
                reply = response["choices"][0]["message"]
                answer = reply.get("content") or ""
                refusals = unoffered_call_results(reply, offered=[])
                if not refusals:
                    break
                # The history may name tools this agent does not offer: refuse them, ask again.
                turn_messages += [{"role": "assistant", "content": answer, "tool_calls": reply["tool_calls"]}, *refusals]
                answer = ""
        except ModelUnavailable:
            answer = UNAVAILABLE
        else:
            if answer:
                ctx.record(turn_messages + [{"role": "assistant", "content": answer}])
        answer = answer or UNAVAILABLE
        tracer.output(answer)
        tracer.write()
        yield events.text(answer)
        yield events.end(answer)
