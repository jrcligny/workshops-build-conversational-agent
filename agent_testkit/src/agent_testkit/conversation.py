"""Written conversations: what a test loads instead of playing the turns that only set the scene.

A conversation is written in the cases (`cases.yaml`, `cases_private.yaml`) as a list of turns:

    conversation:
      - user: "Je cherche les commandes de Léa Martin."
        tools:
          - name: search_customers
            arguments: {name: "Léa Martin"}
            result: {status: ok, customers: [...]}
        answer: "Deux clientes portent ce nom : ..."
      - user: "Celle du Nord."
        answer: "..."

Each turn becomes chat messages: the user's message; when it has tools, one assistant message
carrying the calls (`tool_calls`, ids `call_<turn>_<index>`) followed by one `tool` message per
result (content as JSON); then the assistant's answer. Tool names are neutral (`get_order`,
`search_customers`, `list_orders`): the agent replays them as they are and never runs a tool
it does not offer. Results are taken from `business_api.seed_data`
(`agent_testkit/tests/test_conversations.py` checks them against the business API).
"""

from __future__ import annotations

import json
from typing import Any


def _call_id(turn: int, index: int) -> str:
    return f"call_{turn}_{index}"


def to_messages(conversation: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Chat messages of a written conversation. Messages already in chat form are kept as they are."""
    messages: list[dict[str, Any]] = []
    for number, turn in enumerate(conversation, start=1):
        if "role" in turn:
            messages.append(dict(turn))
            continue
        messages.append({"role": "user", "content": turn["user"]})
        tools = turn.get("tools") or []
        if tools:
            messages.append(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": _call_id(number, index),
                            "type": "function",
                            "function": {
                                "name": tool["name"],
                                "arguments": json.dumps(tool.get("arguments") or {}, ensure_ascii=False),
                            },
                        }
                        for index, tool in enumerate(tools, start=1)
                    ],
                }
            )
            for index, tool in enumerate(tools, start=1):
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": _call_id(number, index),
                        "name": tool["name"],
                        "content": json.dumps(tool.get("result"), ensure_ascii=False),
                    }
                )
        if turn.get("answer"):
            messages.append({"role": "assistant", "content": turn["answer"]})
    return messages


def tool_results(conversation: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every written tool call of a conversation: `{turn, name, arguments, result}`."""
    return [
        {"turn": number, "name": tool["name"], "arguments": tool.get("arguments") or {}, "result": tool.get("result")}
        for number, turn in enumerate(conversation, start=1)
        if "role" not in turn
        for tool in turn.get("tools") or []
    ]
