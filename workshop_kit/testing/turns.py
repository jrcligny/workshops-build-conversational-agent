"""Helpers shared by the workshop tests. All of them require a successful turn (red on the empty shell)."""

from __future__ import annotations

from workshop_kit.evaluation.judge import judge
from workshop_kit.shell.tracer import read_all


def successful_turn(chat_client, message: str, **kwargs):
    turn = chat_client.turn(message, **kwargs)
    assert turn.ok, (
        f"the turn must complete (text + end); got: ok={turn.ok}, error={turn.error!r}"
    )
    assert "text" in turn.types
    assert "end" in turn.types
    traces = read_all()
    assert traces, "a turn trace is required"
    return turn, traces[-1]


def business_log(observation) -> list:
    return [e for e in observation.log() if not str(e.get("route", "")).startswith("/observation")]


def model_input(trace: dict) -> dict:
    return trace.get("input") or {}


def tools(trace: dict) -> list:
    return list(trace.get("tools") or [])


def history(trace: dict) -> list:
    return list(model_input(trace).get("history") or [])


def flat(obj) -> str:
    return str(obj)


def apply_rubric(rubric: dict, turn, trace=None) -> dict:
    verdict = judge(rubric, {"response": turn.text, "trace": flat(trace) if trace is not None else ""})
    assert verdict["passed"], f"rubric {rubric.get('id')}: {verdict.get('rationale')}"
    return verdict
