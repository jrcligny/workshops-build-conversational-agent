"""Context control (07, 08): size of a model input, and compaction of the stored context.

The context of a conversation is `agent_sdk.context`: every message the model has seen. Once it
holds `compaction_message_threshold` turns at the start of a turn, the turn compacts it:

a) every tool result already in the context is replaced by a marker (the call stays, same id);
b) the turns before the last `compaction_keep_turns` leave the context for a rolling summary, written
   by a separate model call with `compaction_prompt.md`, from the previous summary.

Both settings are read at each turn.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from workshop_config import settings

COMPACTION_PROMPT_FILE = Path(__file__).with_name("compaction_prompt.md")
MARKER = (
    "[Résultat d'outil effacé du contexte (compaction) : les faits utiles sont dans le résumé de la conversation.]"
)


def size(messages: list[dict[str, Any]]) -> int:
    """Size of a model input in characters, recorded at each cycle."""
    return len(json.dumps(messages, ensure_ascii=False))


def load_compaction_prompt() -> str:
    text = COMPACTION_PROMPT_FILE.read_text(encoding="utf-8") if COMPACTION_PROMPT_FILE.exists() else ""
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()


def _render(previous_summary: str, turns: list[list[dict[str, Any]]]) -> str:
    calls: dict[str, tuple[str, str]] = {}
    lines = [
        "Résumé précédent :",
        previous_summary or "(aucun : première compaction)",
        "",
        "Tours qui quittent le contexte, dans l'ordre :",
    ]
    for number, turn in enumerate(turns, start=1):
        lines.append(f"--- Tour {number}")
        for message in turn:
            role = message.get("role")
            if role == "user":
                lines.append(f"Utilisateur : {message.get('content') or ''}")
            elif role == "assistant":
                for call in message.get("tool_calls") or []:
                    function = call.get("function") or {}
                    calls[call.get("id", "")] = (function.get("name", ""), function.get("arguments") or "{}")
                if message.get("content"):
                    lines.append(f"Assistant : {message['content']}")
            elif role == "tool":
                name, arguments = calls.get(message.get("tool_call_id", ""), (message.get("name", ""), "{}"))
                lines.append(f"Outil {name or message.get('name', '')}({arguments}) -> {message.get('content') or ''}")
    return "\n".join(lines)


def compact(ctx, summarize: Callable[[list[dict[str, Any]]], tuple[str, dict | None]]) -> dict | None:
    """Compacts `ctx` when it holds the threshold of turns; returns the trace of the compaction, or None."""
    threshold = int(settings.compaction_message_threshold)
    keep = int(settings.compaction_keep_turns)
    turns = ctx.turns()
    if len(turns) < threshold:
        return None
    cut = max(0, len(turns) - max(0, keep))
    old, kept = turns[:cut], turns[cut:]
    prompt = load_compaction_prompt()
    previous = ctx.summary or ""
    summary, model_call = summarize(
        [{"role": "system", "content": prompt}, {"role": "user", "content": _render(previous, old)}]
    )
    summary = (summary or "").strip()
    if not summary:
        return None  # nothing replaced without a summary: the next turn tries again
    cleared: list[dict[str, Any]] = []
    for number, turn in enumerate(turns, start=1):
        for message in turn:
            if message.get("role") == "tool" and message.get("content") != MARKER:
                cleared.append({"tool_call_id": message.get("tool_call_id"), "name": message.get("name"), "turn": number})
    remaining = [
        {**m, "content": MARKER} if m.get("role") == "tool" else m for turn in kept for m in turn
    ]
    ctx.replace(remaining, summary)
    return {
        "threshold": threshold,
        "kept_turns": keep,
        "cleared_tool_results": cleared,
        "summarized_turns": len(old),
        "system_prompt": prompt,
        "previous_summary": previous,
        "summary": summary,
        **({"model_call": model_call} if model_call else {}),
    }
