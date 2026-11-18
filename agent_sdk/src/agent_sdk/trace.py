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
    """One memory entry in the expected format (bonus), stamped now. Which topics and values you
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
            # Loop facts of workshop 05, false until said otherwise (`cycle()`, `cycle_limit_reached()`,
            # `interrupted()`).
            "cycles": 0,
            "cycle_limit_reached": False,
            "interrupted": False,
        }
        self._cycle = 0

    # --- what the model receives (03, 10, bonus) ---------------------------------------------

    def input(
        self,
        system_prompt: str | None = None,
        history: list[Message | dict] | None = None,
        state: dict | None = None,
        **extra: Any,
    ) -> None:
        """What you send to the model: the system prompt, the history you really replay (03),
        the state handed back at the start of the turn (10, `input.state`), any other block."""
        block = self._trace["input"]
        if system_prompt is not None:
            block["system_prompt"] = system_prompt
        if history is not None:
            block["history"] = [_message(m) for m in history]
        if state is not None:
            block["state"] = state
        block.update(extra)

    # --- model calls (03, 09, 13, 15, 16) -------------------------------------------------

    def model_call(
        self,
        response: dict[str, Any],
        duration_ms: int,
        offered_tools: list[str] | None = None,
        context_size: int | None = None,
        **extra: Any,
    ) -> None:
        """Records one model call from its raw answer: model id, usage, stop reason, duration.

        `offered_tools`: names of the tools offered at this call (13, 14); pass `[]` when you
        offer none once you trace them, so the list stays one entry per call.
        `context_size`: your measure of the context sent at this call (09)."""
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

        The names of `tools` are recorded as `offered_tools`, one list per call (an empty list when
        `tools` is None or empty), so `offered_tools[i]` pairs with `model.calls[i]` (13, 14).
        A failed call raises as is (see `ModelUnavailable`, workshop 16) and is not recorded."""
        started = time.perf_counter()
        response = client.generate(messages, tools, model=model)
        offered = [(t.get("function") or t).get("name") for t in tools or []]
        self.model_call(
            response, round((time.perf_counter() - started) * 1000), offered_tools=offered, context_size=context_size
        )
        return response

    # --- cycles and tools (04, 05, 15) ------------------------------------------------

    def cycle(self) -> int:
        """Starts a new cycle of the agent loop (05) and returns its number, from 1: call it before
        each model call of the loop. Model and tool calls recorded afterwards carry this number;
        `cycles` is the count of cycles started (0 until the first call)."""
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
        """Records one tool call: name, arguments, result (with its `status`), cycle (05),
        duration (15) and transport (`"mcp"`, workshop 06). Returns the recorded entry."""
        entry: dict[str, Any] = {"name": name, "arguments": arguments, "result": result, "cycle": self._cycle}
        if duration_ms is not None:
            entry["duration_ms"] = int(duration_ms)
        if transport is not None:
            entry["transport"] = transport
        entry.update(extra)
        self._trace["tools"].append(entry)
        return entry

    def cycle_limit_reached(self, reached: bool = True) -> None:
        """The loop stopped at its cycle limit (05). The field is `false` until you call it."""
        self._trace["cycle_limit_reached"] = bool(reached)

    def interrupted(self, value: bool = True) -> None:
        """The turn stopped on the user's request (05). The field is `false` until you call it."""
        self._trace["interrupted"] = bool(value)

    # --- context (09, 10) -----------------------------------------------------------------

    def compaction_call(self, client: Any, messages: list[dict], model: str = "default") -> dict[str, Any]:
        """Calls the model for the compaction summary (10): `messages` start with your compaction
        system prompt. The call is recorded in `compaction.model_call`, not in `model.calls`
        (those stay the agent's). Returns the raw answer."""
        started = time.perf_counter()
        response = client.generate(messages, None, model=model)
        choice = (response.get("choices") or [{}])[0]
        self._compaction_call = {
            "model": response.get("model"),
            "usage": dict(response.get("usage") or {}),
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "stop_reason": choice.get("finish_reason"),
        }
        if isinstance(self._trace.get("compaction"), dict):
            self._trace["compaction"]["model_call"] = dict(self._compaction_call)
        return response

    def compaction(
        self,
        threshold: int,
        kept_turns: int,
        cleared_tool_results: list[dict[str, Any]],
        summarized_turns: int,
        system_prompt: str,
        previous_summary: str,
        summary: str,
        **extra: Any,
    ) -> Event:
        """Records the compaction of this turn (10) and returns the `compaction` event to yield.
        Call it only on the turn that compacts: the key stays absent otherwise.

        `cleared_tool_results`: one `{tool_call_id, name, turn}` per tool result replaced by a
        marker; `summarized_turns`: the turns that left the context for the summary; `system_prompt`:
        your compaction prompt as sent; `previous_summary`: the summary it started from ("" the
        first time). The call made with `compaction_call` is added as `model_call`."""
        data: dict[str, Any] = {
            "threshold": threshold,
            "kept_turns": kept_turns,
            "cleared_tool_results": [dict(c) for c in cleared_tool_results],
            "summarized_turns": summarized_turns,
            "system_prompt": system_prompt,
            "previous_summary": previous_summary,
            "summary": summary,
            **extra,
        }
        if getattr(self, "_compaction_call", None):
            data["model_call"] = dict(self._compaction_call)
        self._trace["compaction"] = data
        return Event("compaction", {k: v for k, v in data.items() if k != "system_prompt"})

    def state(self, state: dict[str, Any]) -> None:
        """The working state after the turn (10): `current_customer`, `current_order`, `candidates`.
        The state handed to the model at the start of the turn goes to `input(state=...)`."""
        self._trace["state"] = state

    # --- identity, limits (07) ----------------------------------------------------------

    def identity(self, user: str, token_type: str = "application", **extra: Any) -> None:
        """The identity the tools acted with (07). Never pass the token itself."""
        self._trace["identity"] = {"user": user, "token_type": token_type, **extra}

    def limit_reached(self, limit: str) -> None:
        """The turn stopped at a limit (07): `"duration"` or `"token_budget"`."""
        self._trace["limit_reached"] = limit

    # --- memory and skills (bonus, 13) -------------------------------------------------------

    def memory(
        self,
        loaded: list[dict] | None = None,
        written: list[dict] | None = None,
        deleted: list[dict] | None = None,
    ) -> list[Event]:
        """Records the persistent memory of the turn (bonus): entries put back at the start
        (`loaded`), written and deleted by the turn. Returns one `memory` event per change.
        Call it at least once per turn (with `loaded=[]` when nothing is kept)."""
        block = self._trace.setdefault("memory", {"loaded": [], "written": [], "deleted": []})
        block["loaded"].extend(loaded or [])
        block["written"].extend(written or [])
        block["deleted"].extend(deleted or [])
        changes = [("written", e) for e in written or []] + [("deleted", e) for e in deleted or []]
        return [Event("memory", {"action": a, "topic": e.get("topic"), "value": e.get("value")}) for a, e in changes]

    def skill_loaded(self, skill_id: str, version: str, cycle: int | None = None) -> None:
        """A skill of the catalog is loaded or still active in this turn (13)."""
        self._trace.setdefault("skills_loaded", []).append(
            {"id": skill_id, "version": version, "cycle": self._cycle if cycle is None else cycle}
        )

    # --- notices and failures (05, 07, 09, bonus, 16) ---------------------------------------

    def mention(self, content: str, **extra: Any) -> Event:
        """A notice shown to the user (partial answer, limit, memory...). Kept in the trace
        under `mentions` and returned as the `mention` event to yield."""
        self._trace.setdefault("mentions", []).append(content)
        return Event("mention", {"content": content, **extra})

    def fallback(self, from_model: str, to_model: str, reason: str) -> None:
        """The fallback model answered instead of the primary one (16)."""
        self._trace["fallback"] = {"from": from_model, "to": to_model, "reason": reason}

    def unknown_outcome(self, draft_id: str) -> None:
        """A submission's outcome is unknown (16): it must not be replayed."""
        self._trace["unknown_outcome"] = {"draft_id": draft_id}

    def versions(self, instructions: str, tools: str, skills: str, index: str) -> None:
        """The versions in use for this turn (16)."""
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
        """Appends the trace to `traces/turns.jsonl` once per turn. `trace_store` removes the
        known secret keys at the top level of the trace only: never put a token or a key in it."""
        return _writer.write(self._trace)