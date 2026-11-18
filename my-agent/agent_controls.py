"""Specified control of workshop 17 (local-mode/specifications/unverified-references.md).

An order reference cited by the answer that no tool consulted (in this turn, in the stored context or in the
compaction summary) is flagged to the user as unverified. MY_AGENT_DISABLE_CONTROL=1 disables this control only;
the variable is read at call time. Standard library only, so local-mode/controls can import it directly.
"""

from __future__ import annotations

import json
import os
import re

ORDER_REFERENCE = re.compile(r"\bCMD-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")


def control_enabled() -> bool:
    return os.environ.get("MY_AGENT_DISABLE_CONTROL", "0").strip() != "1"


def unverified_references(text: str, tool_calls: list[dict], context: list[dict] | None = None,
                          summary: str | None = None) -> list[str]:
    """References cited in `text` that no tool consulted: neither in a tool call or result (this turn or the
    stored context) nor in the compaction summary. A reference only quoted by the user is not consulted."""
    if not control_enabled():
        return []
    consulted = set(ORDER_REFERENCE.findall(json.dumps(
        [{"arguments": t.get("arguments"), "result": t.get("result")} for t in tool_calls], ensure_ascii=False, default=str)))
    for message in context or []:
        if message.get("role") == "tool":
            consulted |= set(ORDER_REFERENCE.findall(str(message.get("content") or "")))
        for call in message.get("tool_calls") or []:
            consulted |= set(ORDER_REFERENCE.findall(json.dumps(call, ensure_ascii=False, default=str)))
    consulted |= set(ORDER_REFERENCE.findall(summary or ""))
    cited = list(dict.fromkeys(ORDER_REFERENCE.findall(text or "")))
    return [reference for reference in cited if reference not in consulted]


def unverified_mention(references: list[str]) -> str:
    return ("Référence non vérifiée : " + ", ".join(references)
            + " (non consultée dans l'application pendant cette conversation ; à vérifier avant de s'y fier).")
