"""One builder per event type of the interface contract.

What it gives you: a well-formed `Event` for each type, with the field names the interface
and the tests read (`content`, `tool`, `sources`, `draft_id`, `action`, `topic`, `value`...).
Extra keyword arguments are added to the event data as they are.

What stays yours: when to emit each event, what it says, and its consistency with the trace
(one `step` per tool call in workshop 06, a `mention` that really announces a partial answer,
`sources` taken from the passages actually used in workshop 13...).
"""

from __future__ import annotations

from typing import Any

from agent_sdk.contract import Event


def text(content: str) -> Event:
    """A piece of the answer; the interface concatenates them."""
    return Event("text", {"content": content})


def end(full_text: str = "", ok: bool = True, **extra: Any) -> Event:
    """Closes the turn. Emit at least one `text` before it: the history keeps only answered turns."""
    return Event("end", {"ok": ok, "text": full_text, **extra})


def error(detail: str) -> Event:
    return Event("error", {"detail": detail})


def step(tool: str, **extra: Any) -> Event:
    """One tool call during a turn (workshop 06)."""
    return Event("step", {"tool": tool, **extra})


def mention(content: str, **extra: Any) -> Event:
    """A notice shown to the user: partial answer, limit reached, memory in use..."""
    return Event("mention", {"content": content, **extra})


def interruption(**extra: Any) -> Event:
    """The turn stopped cleanly on request (workshop 06)."""
    return Event("interruption", dict(extra))


def compaction(**extra: Any) -> Event:
    """The history was compacted on this turn (workshop 08)."""
    return Event("compaction", dict(extra))


def confirmation_requested(draft_id: str, **extra: Any) -> Event:
    """A write is prepared and waits for the user's gesture (workshop 10b)."""
    return Event("confirmation_requested", {"draft_id": draft_id, **extra})


def memory(action: str, topic: str, value: Any = None, **extra: Any) -> Event:
    """A change of the persistent memory shown to the user (workshop 12)."""
    return Event("memory", {"action": action, "topic": topic, "value": value, **extra})


def sources(items: list[dict], **extra: Any) -> Event:
    """The documents used by the answer: `[{"title", "version", "address"}]` (workshop 13)."""
    return Event("sources", {"sources": list(items), **extra})


def attachment(attachment_id: str, **extra: Any) -> Event:
    """An attached document was read (workshop 15)."""
    return Event("attachment", {"id": attachment_id, **extra})
