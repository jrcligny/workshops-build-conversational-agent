"""Scriptable chat model and deterministic embeddings.

The simulated model does not reason. A test scripts it through `POST /_test/scripts` of the proxy:
`{"scripts": [{"if_contains": "...", "content": "...", "tool": {...}}, {"if_last_role": "tool", ...}]}`;
the first script whose `if_contains` is in the last user message (or whose `if_last_role` is the
role of the last message) gives the answer, otherwise a generic cautious sentence is returned."""

from __future__ import annotations

from typing import Any

from text_vectors import DIM, vector


def complete(messages: list[dict[str, Any]], scripts: list[dict] | None = None) -> dict[str, Any]:
    """Returns a scripted response when a script matches, otherwise a cautious generic response (in French, the agent's language)."""
    user_text = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_text = msg.get("content") or ""
            break
    for script in scripts or []:
        if _match(script, messages, user_text):
            return _response(script.get("content", ""), script.get("tool"))
    return _response(
        "Je n'ai pas accès aux données de l'application et je ne peux pas affirmer l'état d'une commande précise."
    )


def _match(script: dict, messages: list[dict], user_text: str) -> bool:
    pattern = (script.get("if_contains") or "").lower()
    if pattern and pattern in user_text.lower():
        return True
    if script.get("if_last_role") and messages and messages[-1].get("role") == script["if_last_role"]:
        return True
    return False


def _response(content: str, tool: dict | None = None) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": content}
    if tool:
        message["tool_calls"] = [tool]
    return {
        "id": "sim-chat",
        "object": "chat.completion",
        "model": "simulated-model",
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 16, "completion_tokens": max(len(content.split()), 1), "total_tokens": 16},
    }


def embeddings(inputs: list[str]) -> dict[str, Any]:
    data = [{"object": "embedding", "index": i, "embedding": vector(text)} for i, text in enumerate(inputs)]
    return {
        "object": "list",
        "model": "simulated-embeddings",
        "data": data,
        "usage": {"prompt_tokens": sum(len(t.split()) for t in inputs), "total_tokens": len(inputs)},
        "dimension": DIM,
    }
