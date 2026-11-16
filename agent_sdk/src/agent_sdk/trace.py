"""The trace of a turn, written through one method per thing that happens.

You never assemble the trace JSON yourself: create one `Tracer` at the start of the turn, call
its methods as things happen, then `write()` once at the end. The fields it produces are the ones
the tests read (`docs/interface-contract.md`, section « Names read by the tests », and each
`contrat.md`, section « Ce que lisent les tests »).

    tracer = Tracer(conversation_id, user, message)
    tracer.input(system_prompt, history)                  # what the model receives (03)
    response = tracer.call_model(client, messages)        # one model call, timed and recorded
    tracer.tool_call("get_order", {"reference": "CMD-1042"}, result)   # 04
    tracer.output(answer)
    tracer.write()

What it does not do: decide anything. Which history you send, which tools you offer, when you
compact, what goes into the state or the memory, how you measure the context size... stay the
work of the workshops. The tracer only records what you hand it, in the expected format.

Methods returning an `Event` also give you the interface event to `yield` (`mention`,
`compaction`, `memory`): one call traces it and builds it.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_sdk import trace_store as _writer
from agent_sdk.contract import Event, Message, TestUser


def _message(m: Message | dict) -> dict[str, Any]:
    if isinstance(m, Message):
        return {"role": m.role, "content": m.content}
    return dict(m)


def _add_usage(total: dict[str, int], usage: dict[str, Any]) -> None:
    for key, value in (usage or {}).items():
        if isinstance(value, (int, float)):
            total[key] = total.get(key, 0) + int(value)


def memory_entry(topic: str, value: Any, user: TestUser, origin: str = "user") -> dict[str, Any]:
    """One memory entry in the expected format (12), stamped now. Which topics and values you
    keep, and how you store them under `MEMORY_DIR`, stay yours."""
    return {
        "topic": topic,
        "value": value,
        "origin": origin,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "user": user.id,
        "organization": user.organization,
    }


class Tracer:
    """Builds the trace of one turn. Create one per turn; `write()` it once."""

    def __init__(self, conversation_id: str, user: TestUser, message: str):
        self._trace: dict[str, Any] = {
            "turn_id": _writer.new_id(),
            "conversation_id": conversation_id,
            "user": {"id": user.id, "role": user.role, "organization": user.organization},
            "input": {"system_prompt": "", "history": [], "message": message},
            "tools": [],
            "output": "",
        }
        self._cycle = 0

    # --- what the model receives (03, 08, 12) ---------------------------------------------

    def input(
        self,
        system_prompt: str | None = None,
        history: list[Message | dict] | None = None,
        state: dict | None = None,
        **extra: Any,
    ) -> None:
        """What you send to the model: the system prompt, the history you really replay (03),
        the state handed back at the start of the turn (08, `input.state`), any other block."""
        block = self._trace["input"]
        if system_prompt is not None:
            block["system_prompt"] = system_prompt
        if history is not None:
            block["history"] = [_message(m) for m in history]
        if state is not None:
            block["state"] = state
        block.update(extra)

    # --- model calls (03, 07, 14, 17, 18) -------------------------------------------------

    def model_call(
        self,
        response: dict[str, Any],
        duration_ms: int,
        offered_tools: list[str] | None = None,
        context_size: int | None = None,
        **extra: Any,
    ) -> None:
        """Records one model call from its raw answer: model id, usage, stop reason, duration.

        `offered_tools`: names of the tools offered at this call (14, 15); pass `[]` when you
        offer none once you trace them, so the list stays one entry per call.
        `context_size`: your measure of the context sent at this call (07)."""
        choice = (response.get("choices") or [{}])[0]
        call: dict[str, Any] = {
            "cycle": self._cycle,
            "model": response.get("model"),
            "usage": dict(response.get("usage") or {}),
            "duration_ms": int(duration_ms),
            "stop_reason": choice.get("finish_reason"),
        }
        if context_size is not None:
            call["context_size"] = int(context_size)
        call.update(extra)
        model = self._trace.setdefault("model", {"calls": [], "usage": {}, "duration_ms": 0})
        model["calls"].append(call)
        model["id"] = call["model"]
        model["stop_reason"] = call["stop_reason"]
        model["duration_ms"] += call["duration_ms"]
        _add_usage(model["usage"], call["usage"])
        if offered_tools is not None:
            self._trace.setdefault("offered_tools", []).append(list(offered_tools))

    def call_model(
        self,
        client: Any,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str = "default",
        context_size: int | None = None,
    ) -> dict[str, Any]:
        """Calls `client.generate(messages, tools, model=model)`, records the call, returns the answer.

        The names of `tools` are recorded as `offered_tools` when you pass a list. A failed call
        raises as is (see `ModelUnavailable`, workshop 18) and is not recorded."""
        started = time.perf_counter()
        response = client.generate(messages, tools, model=model)
        offered = None if tools is None else [(t.get("function") or t).get("name") for t in tools]
        self.model_call(
            response, round((time.perf_counter() - started) * 1000), offered_tools=offered, context_size=context_size
        )
        return response

    # --- cycles and tools (04, 06, 09, 17) ------------------------------------------------

    def cycle(self) -> int:
        """Starts a new cycle of the agent loop (06) and returns its number, from 1.
        Model and tool calls recorded afterwards carry it; `cycles` is the count."""
        self._cycle += 1
        self._trace["cycles"] = self._cycle
        return self._cycle

    def tool_call(
        self,
        name: str,
        arguments: dict[str, Any],
        result: Any,
        duration_ms: int | None = None,
        transport: str | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """Records one tool call: name, arguments, result (with its `status`), cycle (06),
        duration (17) and transport (`"mcp"`, workshop 09). Returns the recorded entry."""
        entry: dict[str, Any] = {"name": name, "arguments": arguments, "result": result, "cycle": self._cycle}
        if duration_ms is not None:
            entry["duration_ms"] = int(duration_ms)
        if transport is not None:
            entry["transport"] = transport
        entry.update(extra)
        self._trace["tools"].append(entry)
        return entry

    def cycle_limit_reached(self) -> None:
        """The loop stopped at its cycle limit (06)."""
        self._trace["cycle_limit_reached"] = True

    def interrupted(self) -> None:
        """The turn stopped on the user's request (06)."""
        self._trace["interrupted"] = True

    # --- context (07, 08) -----------------------------------------------------------------

    def compaction(
        self, summarized_answers: int, kept_user_messages: int, threshold: int, summary: str, **extra: Any
    ) -> Event:
        """Records the compaction of this turn (08) and returns the `compaction` event to yield.
        Call it only on the turn that compacts: the key stays absent otherwise."""
        data = {
            "summarized_answers": summarized_answers,
            "kept_user_messages": kept_user_messages,
            "threshold": threshold,
            "summary": summary,
            **extra,
        }
        self._trace["compaction"] = data
        return Event("compaction", dict(data))

    def state(self, state: dict[str, Any]) -> None:
        """The working state after the turn (08): `current_customer`, `current_order`, `candidates`.
        The state handed to the model at the start of the turn goes to `input(state=...)`."""
        self._trace["state"] = state

    # --- identity, limits (10a, 10d) ------------------------------------------------------

    def identity(self, user: str, token_type: str = "application", **extra: Any) -> None:
        """The identity the tools acted with (10a). Never pass the token itself."""
        self._trace["identity"] = {"user": user, "token_type": token_type, **extra}

    def limit_reached(self, limit: str) -> None:
        """The turn stopped at a limit (10d): `"duration"` or `"token_budget"`."""
        self._trace["limit_reached"] = limit

    # --- memory and skills (12, 14) -------------------------------------------------------

    def memory(
        self,
        loaded: list[dict] | None = None,
        written: list[dict] | None = None,
        deleted: list[dict] | None = None,
    ) -> list[Event]:
        """Records the persistent memory of the turn (12): entries put back at the start
        (`loaded`), written and deleted by the turn. Returns one `memory` event per change.
        Call it at least once per turn (with `loaded=[]` when nothing is kept)."""
        block = self._trace.setdefault("memory", {"loaded": [], "written": [], "deleted": []})
        block["loaded"].extend(loaded or [])
        block["written"].extend(written or [])
        block["deleted"].extend(deleted or [])
        changes = [("written", e) for e in written or []] + [("deleted", e) for e in deleted or []]
        return [Event("memory", {"action": a, "topic": e.get("topic"), "value": e.get("value")}) for a, e in changes]

    def skill_loaded(self, skill_id: str, version: str, cycle: int | None = None) -> None:
        """A skill of the catalog is loaded or still active in this turn (14)."""
        self._trace.setdefault("skills_loaded", []).append(
            {"id": skill_id, "version": version, "cycle": self._cycle if cycle is None else cycle}
        )

    # --- notices and failures (06, 07, 10d, 12, 18) ---------------------------------------

    def mention(self, content: str, **extra: Any) -> Event:
        """A notice shown to the user (partial answer, limit, memory...). Kept in the trace
        under `mentions` and returned as the `mention` event to yield."""
        self._trace.setdefault("mentions", []).append(content)
        return Event("mention", {"content": content, **extra})

    def fallback(self, from_model: str, to_model: str, reason: str) -> None:
        """The fallback model answered instead of the primary one (18)."""
        self._trace["fallback"] = {"from": from_model, "to": to_model, "reason": reason}

    def unknown_outcome(self, draft_id: str) -> None:
        """A submission's outcome is unknown (18): it must not be replayed."""
        self._trace["unknown_outcome"] = {"draft_id": draft_id}

    def versions(self, instructions: str, tools: str, skills: str, index: str) -> None:
        """The versions in use for this turn (18)."""
        self._trace["versions"] = {"instructions": instructions, "tools": tools, "skills": skills, "index": index}

    # --- answer and writing ---------------------------------------------------------------

    def output(self, text: str) -> None:
        self._trace["output"] = text

    def set(self, key: str, value: Any) -> None:
        """Any other top-level field of your own (fields not read by the tests are free)."""
        self._trace[key] = value

    def to_dict(self) -> dict[str, Any]:
        return self._trace

    def write(self) -> Path:
        """Appends the trace to `traces/turns.jsonl`, without secrets. Once per turn."""
        return _writer.write(self._trace)