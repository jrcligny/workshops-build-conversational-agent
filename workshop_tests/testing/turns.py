"""Helpers shared by the workshop tests. All of them require a successful turn (red on the empty shell)."""

from __future__ import annotations

import httpx

from workshop_kit.llm_proxy.tokens import reset_usage
from workshop_config import settings
from workshop_tests.evaluation.judge import judge
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


def tool_name(call: dict) -> str:
    return str(call.get("name") or call.get("tool") or "")


def tool_arguments(call: dict) -> dict:
    args = call.get("arguments") or call.get("parameters") or {}
    return args if isinstance(args, dict) else {"raw": args}


def tool_result(call: dict) -> dict:
    result = call.get("result") or call.get("output") or {}
    return result if isinstance(result, dict) else {"raw": result}


def tool_status(call: dict) -> str:
    """Normalised status of a tool result: ok | approximate | not_found | error | denied.

    `found` is accepted as a synonym of `ok` (see the interface contract).
    """
    status = str(tool_result(call).get("status") or "").lower()
    return "ok" if status == "found" else status


def events_of(turn, event_type: str) -> list[dict]:
    return [data for kind, data in turn.events if kind == event_type]


def model_calls(services) -> list[dict]:
    """Chat-completion calls received by the model proxy since the start of the test."""
    token = httpx.post(f"{services['proxy']}/_test/token", timeout=10).json()["token"]
    log = httpx.get(f"{services['proxy']}/log", headers={"Authorization": f"Bearer {token}"}, timeout=10).json()
    return [e for e in log if e.get("route") == "/v1/chat/completions"]


def apply_rubric(rubric: dict, turn, trace=None) -> dict:
    """Applies a rubric once, to an answer that cannot be replayed on a fresh conversation."""
    verdict = judge(rubric, {"response": turn.text, "trace": flat(trace) if trace is not None else ""})
    assert verdict["passed"], f"rubric {rubric.get('id')}: {verdict.get('rationale')}"
    return verdict


def apply_rubric_repeatedly(rubric: dict, run, k: int | None = None, n: int | None = None) -> list[dict]:
    """Runs `run()` (which opens a fresh conversation and returns `(turn, trace)`) up to n times.

    The rubric passes when at least k runs pass (JUDGE_K out of JUDGE_N by default).
    Stops as soon as the outcome is known. Each run gets the full proxy quota, like a test of its own.
    """
    k = int(k or settings.judge_k)
    n = int(n or settings.judge_n)
    verdicts: list[dict] = []
    passed = 0
    for i in range(n):
        reset_usage()
        turn, trace = run()
        verdict = judge(rubric, {"response": turn.text, "trace": flat(trace) if trace is not None else ""})
        verdicts.append(verdict)
        passed += bool(verdict["passed"])
        if passed >= k or passed + (n - i - 1) < k:
            break
    assert passed >= k, (
        f"rubric {rubric.get('id')}: {passed} run(s) passed, {k} out of {n} required; "
        + " | ".join(v.get("rationale", "") for v in verdicts if not v["passed"])
    )
    return verdicts


def repeatedly(check, k: int | None = None, n: int | None = None, label: str = "") -> int:
    """Runs `check()` (a fresh conversation and its assertions) up to n times; at least k must pass.

    For behaviour the model chooses (grouping calls, how many cycles): one run is not enough to
    conclude, as for the rubrics. Not for safety facts (a replayed write, a leak): those stay strict.
    Each run gets the full proxy quota, like a test of its own.
    """
    k = int(k or settings.judge_k)
    n = int(n or settings.judge_n)
    passed, failures = 0, []
    for i in range(n):
        reset_usage()
        try:
            check()
            passed += 1
        except AssertionError as exc:
            failures.append(str(exc).splitlines()[0] if str(exc) else "assertion failed")
        if passed >= k or passed + (n - i - 1) < k:
            break
    assert passed >= k, f"{label}: {passed} run(s) passed, {k} out of {n} required; " + " | ".join(failures)
    return passed
