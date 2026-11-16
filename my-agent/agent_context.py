"""Context control: compaction of old answers in long conversations."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from workshop_kit.shell.config import settings

KEEP_RECENT_MESSAGES = 4

SUMMARY_INSTRUCTION = (
    "Résume en français, en quelques lignes factuelles, les réponses de l'assistant ci-dessous : "
    "clients, références de commande, statuts, chiffres et décisions. N'invente rien, n'ajoute aucun conseil."
)


def size(messages: list[dict[str, Any]]) -> dict[str, int]:
    """Size of a model input, recorded at each cycle."""
    return {"messages": len(messages), "chars": len(json.dumps(messages, ensure_ascii=False))}


def threshold() -> int:
    return int(settings.compaction_message_threshold)


class Compactor:
    """Summarizes old assistant answers once the history goes beyond the threshold.

    User messages are always kept verbatim; only old answers (which carry old tool results) are summarized.
    Summaries are cached per conversation and extended incrementally.
    """

    def __init__(self, summarize: Callable[[list[dict[str, Any]]], str]):
        self._summarize = summarize
        self._cache: dict[str, tuple[int, str]] = {}

    def apply(self, conversation_id: str, history: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict | None]:
        if len(history) <= threshold():
            return list(history), None
        cut = len(history) - KEEP_RECENT_MESSAGES
        old, recent = history[:cut], history[cut:]
        done, summary = self._cache.get(conversation_id, (0, ""))
        if cut > done:
            fresh = old[done:]
            request = [{"role": "system", "content": SUMMARY_INSTRUCTION}]
            if summary:
                request.append({"role": "user", "content": "Résumé précédent :\n" + summary})
            request.append(
                {
                    "role": "user",
                    "content": "\n".join(f"{m['role']}: {m['content']}" for m in fresh),
                }
            )
            summary = self._summarize(request).strip()
            self._cache[conversation_id] = (cut, summary)
        kept_user = [m for m in old if m["role"] == "user"]
        compacted = [
            {"role": "system", "content": "Résumé des réponses précédentes de l'assistant :\n" + summary},
            *kept_user,
            *recent,
        ]
        event = {
            "summary": summary,
            "summarized_answers": sum(1 for m in old if m["role"] != "user"),
            "kept_user_messages": len(kept_user),
            "threshold": threshold(),
            "history_before": len(history),
            "history_after": len(compacted),
        }
        return compacted, event
