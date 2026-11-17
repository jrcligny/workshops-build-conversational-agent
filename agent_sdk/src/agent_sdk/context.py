"""The context of each conversation: every message the model has seen, kept between turns.

`harness.py` is reloaded at each turn, so it cannot keep anything itself from one turn to the
next. This module stays loaded in the gateway process and keeps, per `conversation_id`, the
complete messages of the conversation in the chat format of the proxy:

- `{"role": "user", "content": ...}`
- `{"role": "assistant", "content": ..., "tool_calls": [...]}`
- `{"role": "tool", "tool_call_id": ..., "name": ..., "content": <result as JSON text>}`

The system prompt is not stored: you send it at each turn.

    ctx = context(conversation_id)
    messages = ctx.for_model(system_prompt) + [{"role": "user", "content": message}]
    ...                                   # model calls, tool calls of the turn
    ctx.record(turn_messages)             # at the end of the turn: user, assistant, tool..., final answer

`ctx.state` keeps the working memory of the conversation (08: current customer, current order,
candidates), outside the messages: it crosses the compaction unchanged. A written history comes
without it (`seed` empties it): when the context holds messages but no state, rebuild the state
from those messages (tool results included) before compacting.

What it does not do: decide anything. What you record, which results you clear, which turns you
summarize and how stay the work of the workshops (10). `replace` only stores what you hand it.

A conversation may also start from a written history (`seed`): the tests load a conversation
written in advance instead of playing it turn by turn, and the gateway exposes it as
`POST /conversations/{id}/history`. Your agent then continues it as if it had produced it: the
history may hold calls to tools that your agent does not offer (neutral names such as
`get_order`); replay them as they are, never call a tool you do not offer.
"""

from __future__ import annotations

import copy
import json
import threading
from typing import Any

from agent_sdk.contract import Message

SUMMARY_HEADING = "Résumé de la conversation précédente :"

_lock = threading.Lock()
_contexts: dict[str, "Context"] = {}


def _as_dict(message: Message | dict[str, Any]) -> dict[str, Any]:
    if isinstance(message, Message):
        return {"role": message.role, "content": message.content}
    return copy.deepcopy(dict(message))


class Context:
    """The messages of one conversation, its rolling summary and its working state (10)."""

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.messages: list[dict[str, Any]] = []
        self.summary: str = ""
        self.state: dict[str, Any] = {}

    def turns(self) -> list[list[dict[str, Any]]]:
        """The messages grouped by turn: a turn starts at a `user` message."""
        groups: list[list[dict[str, Any]]] = []
        for message in self.messages:
            if message.get("role") == "user" or not groups:
                groups.append([])
            groups[-1].append(message)
        return groups

    def for_model(self, system_prompt: str) -> list[dict[str, Any]]:
        """What to send the model before the user's new message: the system prompt, the summary
        when there is one (10), then every stored message. Copies: editing them changes nothing here."""
        messages = [{"role": "system", "content": system_prompt}]
        if self.summary:
            messages.append({"role": "system", "content": f"{SUMMARY_HEADING}\n{self.summary}"})
        return messages + copy.deepcopy(self.messages)

    def record(self, messages: list[Message | dict[str, Any]]) -> None:
        """Adds the messages of a finished turn, in order."""
        self.messages.extend(_as_dict(m) for m in messages)

    def replace(self, messages: list[Message | dict[str, Any]], summary: str | None = None) -> None:
        """Replaces the stored messages (after clearing or compaction, 10), and the summary if given."""
        self.messages = [_as_dict(m) for m in messages]
        if summary is not None:
            self.summary = summary


def context(conversation_id: str) -> Context:
    """The context of a conversation, created empty on first use."""
    with _lock:
        if conversation_id not in _contexts:
            _contexts[conversation_id] = Context(conversation_id)
        return _contexts[conversation_id]


def seed(
    conversation_id: str,
    messages: list[Message | dict[str, Any]],
    summary: str = "",
    state: dict[str, Any] | None = None,
) -> Context:
    """Starts a conversation from a written history (tests, demonstrations). Not for the agent.
    The working state is emptied unless given: the agent rebuilds it from the messages."""
    ctx = context(conversation_id)
    ctx.replace(messages, summary)
    ctx.state = copy.deepcopy(state or {})
    return ctx


def clear_contexts() -> None:
    """Forgets every conversation (gateway reset)."""
    with _lock:
        _contexts.clear()


def unoffered_call_results(assistant_message: dict[str, Any], offered: list[str] | None = None) -> list[dict[str, Any]]:
    """The `tool` messages answering the calls of `assistant_message` to tools you do not offer.

    A history may mention tools your agent does not have (a written conversation, an earlier
    version of the agent): the model may then try to call them. Answer each such call with this
    refusal, then call the model again; never run it."""
    offered_names = set(offered or [])
    results = []
    for call in assistant_message.get("tool_calls") or []:
        name = (call.get("function") or {}).get("name") or call.get("name") or ""
        if name in offered_names:
            continue
        results.append(
            {
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "name": name,
                "content": json.dumps(
                    {"status": "error", "error": f"tool {name!r} is not available in this conversation"},
                    ensure_ascii=False,
                ),
            }
        )
    return results
