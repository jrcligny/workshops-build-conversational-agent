"""The base fields of a turn trace, the ones every workshop reads from 03 on.

What it gives you: `base_trace(...)` returns a plain dict with `turn_id`, `conversation_id`,
`user`, `input` (`system_prompt`, `history`, `message`), `tools` (empty) and `output` (empty).
Fill it during the turn, then write it once with `agent_helpers.kit.write_trace(trace)`.

What stays yours: the real values (the history you actually send, each tool call with its
arguments and result, the answer) and every field a workshop adds: `model` (03, 07, 17),
`cycles` (06), `compaction` and `state` (08), `identity` (10a), `limit_reached` (10d),
`memory` (12), `skills_loaded` and `offered_tools` (14), `fallback` and `versions` (18)...
Each `contrat.md` (section « Ce que lisent les tests ») and `docs/interface-contract.md` name them.
"""

from __future__ import annotations

from typing import Any

from workshop_kit.shell import tracer
from workshop_kit.shell.harness_contract import Message, TestUser


def base_trace(
    conversation_id: str,
    user: TestUser,
    system_prompt: str,
    history: list[Message],
    message: str,
) -> dict[str, Any]:
    return {
        "turn_id": tracer.new_id(),
        "conversation_id": conversation_id,
        "user": {"id": user.id, "role": user.role, "organization": user.organization},
        "input": {
            "system_prompt": system_prompt,
            "history": [{"role": m.role, "content": m.content} for m in history],
            "message": message,
        },
        "tools": [],
        "output": "",
    }
