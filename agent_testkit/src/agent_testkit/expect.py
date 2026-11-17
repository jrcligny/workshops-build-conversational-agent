"""Business assertions shared by the workshop checks (`workshops/*/tests/checks.py`).

Each helper raises an `AssertionError` whose message starts with the criterion (the `message`
argument) and ends with what was observed, so that every workshop reports failures the same way.

Text matching: by default case and accents are ignored ("Livrée" matches "livree").
`strict=True` compares exact substrings: use it for references, identifiers and amounts.
`text` may be a string or a turn (anything with a `.text`).
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable

from agent_testkit.turns import business_log, events_of, tool_arguments, tool_name, tool_result, tools

EXCERPT = 300


def _text(text) -> str:
    return str(getattr(text, "text", text) or "")


def _terms(terms) -> list[str]:
    return [terms] if isinstance(terms, str) else [str(t) for t in terms]


def fold(text: str) -> str:
    """Lower case, without accents: the comparison form of the non-strict helpers."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _found(text, terms, strict: bool) -> list[str]:
    haystack = _text(text) if strict else fold(_text(text))
    return [t for t in _terms(terms) if (t if strict else fold(t)) in haystack]


def _excerpt(text) -> str:
    value = _text(text)
    return repr(value if len(value) <= EXCERPT else value[:EXCERPT] + "…")


def mentions(text, terms: str | Iterable[str], *, strict: bool = False) -> bool:
    """True when the text mentions at least one of the terms (a predicate, for combined conditions)."""
    return bool(_found(text, terms, strict))


def mentions_any(text, terms: str | Iterable[str], message: str = "the answer mentions one of the terms", *, strict: bool = False) -> None:
    expected = _terms(terms)
    assert _found(text, expected, strict), f"{message}: none of {expected} in {_excerpt(text)}"


def mentions_all(text, terms: str | Iterable[str], message: str = "the answer mentions every term", *, strict: bool = False) -> None:
    expected = _terms(terms)
    missing = [t for t in expected if t not in _found(text, [t], strict)]
    assert not missing, f"{message}: missing {missing} in {_excerpt(text)}"


def mentions_none(text, terms: str | Iterable[str], message: str = "the answer mentions none of the terms", *, strict: bool = False) -> None:
    present = _found(text, terms, strict)
    assert not present, f"{message}: found {present} in {_excerpt(text)}"


def expect_event(turn, *event_types: str, message: str | None = None) -> list[dict]:
    """At least one event of one of `event_types`; returns their data."""
    found = [data for t in event_types for data in events_of(turn, t)]
    assert found, f"{message or 'the interface receives the event'}: no {' or '.join(event_types)} event in {turn.types}"
    return found


def expect_no_event(turn, event_type: str, message: str | None = None) -> None:
    assert event_type not in turn.types, f"{message or 'the interface does not receive the event'}: {event_type} in {turn.types}"


def calls_with(trace, value: str) -> list[dict]:
    """Tool calls of the turn whose arguments mention `value` (exact substring)."""
    return [c for c in tools(trace) if str(value) in str(tool_arguments(c))]


def called_with(trace, value: str, message: str | None = None) -> list[dict]:
    calls = calls_with(trace, value)
    assert calls, f"{message or 'a tool is called with the value'}: no call with {value!r} in {[tool_arguments(c) for c in tools(trace)]}"
    return calls


def no_tool_called(trace, message: str = "no tool is called") -> None:
    called = tools(trace)
    assert not called, f"{message}: {[tool_name(c) for c in called]}"


def no_business_call(observation, message: str = "the business application is not called") -> None:
    log = business_log(observation)
    assert log == [], f"{message}: {[e.get('route') for e in log]}"


def business_writes(trace) -> list[dict]:
    """Write tool calls of the turn: their result carries the id of a prepared draft."""
    return [c for c in tools(trace) if "DRAFT-" in str(tool_result(c))]


def no_business_write(observation, message: str = "nothing is prepared nor submitted") -> None:
    state = observation.state("submissions")
    drafts, submitted = state["drafts"], state["submitted_requests"]
    assert drafts == [] and submitted == [], f"{message}: drafts={drafts}, submitted_requests={submitted}"


def strings_in(value) -> list[str]:
    """Every string held in a nested structure of dicts and lists."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        value = list(value.values())
    if isinstance(value, list):
        return [s for v in value for s in strings_in(v)]
    return []


def state_of(trace) -> dict:
    state = trace.get("state")
    assert isinstance(state, dict) and state, f"trace.state must hold the conversation state as an object: {state!r}"
    return state
