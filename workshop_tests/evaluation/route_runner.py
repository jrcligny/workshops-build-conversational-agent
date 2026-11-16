"""Runs the evaluation routes of workshop 17 and writes one report entry per route.

A route is a YAML file: the official routes live in `workshops/17-evaluation/routes/cases/`
(protected by `routes.sha256`), the student's own routes in `my-agent/routes/`. Each route
is run k out of n times (`ROUTE_K` out of `ROUTE_N`, once by default) on a fresh conversation,
with the dataset reloaded and the proxy quota reset; a run passes when every fact checked by
code holds, then when the rubric (meaning) passes. Format of a route:

    id: approximate-reference-cmd-1402
    edge_case: approximate-reference
    user: {id: camille-renard, role: customer_service, organization: organization-a}
    dataset: standard            # optional: minimal | standard | volume | concurrency
    turns:
      - message: "Quel est le statut de la commande CMD-1402 ?"
        attachments: []          # optional, ids of files of the attachments area
    facts:                       # checked by code on the last turn, at least one
      - {type: tool_called, argument_contains: CMD-1402}
      - {type: tool_status, argument_contains: CMD-1402, status_in: [approximate, not_found]}
      - {type: text_contains, value: CMD-1042}
    rubric:                      # meaning, judged after the facts
      criterion: "..."
      requirements: [{type: required_any, patterns: ["..."]}]

A route may set `counterfactual_of: <id of another route>` when it replays that route with one detail
changed (a proper noun, a reference); the expected facts then change accordingly.

Fact types: tool_called, tool_not_called, tool_status, text_contains, text_absent, event,
no_event, no_drafts, no_submission, state_equals (dotted path in trace.state).
A route needs at least one fact other than text_contains / text_absent: the text alone proves little.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from workshop_kit.llm_proxy.tokens import reset_usage
from workshop_config import repo_path, settings
from workshop_tests.evaluation.judge import judge
from workshop_tests.evaluation.routes import ROUTES_DIR

EDGE_CASES = (
    "approximate-reference",
    "namesakes",
    "truncated-result-total",
    "out-of-scope-request",
    "write-after-attachment",
    "question-without-documentary-answer",
    "user-without-write-permission",
    "duplicate-invoice",
)
FACT_TYPES = {
    "tool_called", "tool_not_called", "tool_status", "text_contains", "text_absent",
    "event", "no_event", "no_drafts", "no_submission", "state_equals",
}
TEXT_FACTS = {"text_contains", "text_absent"}
REPORT_FILE = "route-report.json"


def official_dir() -> Path:
    return ROUTES_DIR / "cases"


def student_dir() -> Path:
    return repo_path(settings.my_agent_dir) / "routes"


def load_routes(folder: Path, origin: str) -> list[dict]:
    routes = []
    if not folder.is_dir():
        return routes
    for path in sorted(folder.glob("*.y*ml")):
        route = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        route["origin"] = origin
        route["file"] = path.name
        routes.append(route)
    return routes


def validate(route: dict) -> list[str]:
    errors = []
    for key in ("id", "edge_case", "turns", "facts", "rubric"):
        if not route.get(key):
            errors.append(f"missing {key}")
    if route.get("edge_case") and route["edge_case"] not in EDGE_CASES:
        errors.append(f"unknown edge_case {route['edge_case']!r}")
    for fact in route.get("facts") or []:
        if fact.get("type") not in FACT_TYPES:
            errors.append(f"unknown fact type {fact.get('type')!r}")
    facts = route.get("facts") or []
    if facts and all(f.get("type") in TEXT_FACTS for f in facts):
        errors.append("facts only read the answer text: add a fact on the trace, the events or the application state")
    if route.get("rubric") and not route["rubric"].get("criterion"):
        errors.append("rubric without criterion")
    return errors


def _calls(trace: dict, needle: str | None) -> list[dict]:
    calls = trace.get("tools") or []
    if not needle:
        return calls
    return [c for c in calls if needle in json.dumps(c.get("arguments") or c.get("parameters") or {}, ensure_ascii=False)]


def _status(call: dict) -> str:
    result = call.get("result") or call.get("output") or {}
    status = str(result.get("status") or "").lower() if isinstance(result, dict) else ""
    return "ok" if status == "found" else status


def _dig(data: Any, dotted: str) -> Any:
    for part in dotted.split("."):
        data = data.get(part) if isinstance(data, dict) else None
    return data


def check_fact(fact: dict, turn, trace: dict, observation) -> dict:
    kind = fact.get("type")
    needle = fact.get("argument_contains")
    text = turn.text
    if kind == "tool_called":
        ok = bool(_calls(trace, needle))
    elif kind == "tool_not_called":
        ok = not _calls(trace, needle)
    elif kind == "tool_status":
        statuses = [_status(c) for c in _calls(trace, needle)]
        ok = bool(statuses) and set(statuses) <= set(fact.get("status_in") or [])
    elif kind == "text_contains":
        ok = str(fact["value"]).lower() in text.lower()
    elif kind == "text_absent":
        ok = str(fact["value"]).lower() not in text.lower()
    elif kind == "event":
        ok = fact["event"] in turn.types
    elif kind == "no_event":
        ok = fact["event"] not in turn.types
    elif kind == "no_drafts":
        ok = observation.state("submissions")["drafts"] == []
    elif kind == "no_submission":
        ok = observation.state("submissions")["submitted_requests"] == []
    elif kind == "state_equals":
        ok = _dig(trace.get("state") or {}, fact["path"]) == fact["equals"]
    else:
        ok = False
    return {"fact": fact, "passed": ok}


def run_once(route: dict, open_client, observation) -> dict:
    observation.reset(route.get("dataset") or "standard")
    # Each run is a test of its own: it gets the full proxy quota, as reset_state gives each test.
    reset_usage()
    if route.get("attachments_dir"):
        # Attachments of an official route live next to it (routes/fixtures/), not in my-agent/.
        base = official_dir().parent if route["origin"] == "official" else student_dir()
        previous = settings.attachments_dir
        settings.attachments_dir = str((base / route["attachments_dir"]).resolve())
        try:
            return _run_turns(route, open_client, observation)
        finally:
            settings.attachments_dir = previous
    return _run_turns(route, open_client, observation)


def _run_turns(route: dict, open_client, observation) -> dict:
    from workshop_kit.shell.tracer import read_all

    user = route.get("user") or {}
    client = open_client(
        user.get("id", "camille-renard"), user.get("role", "customer_service"), user.get("organization", "organization-a")
    )
    turn = trace = None
    for step in route["turns"]:
        turn = client.turn(step["message"], attachments=step.get("attachments") or None)
        if not turn.ok:
            return {"facts": [], "facts_passed": False, "meaning": None, "error": turn.error, "passed": False}
    traces = read_all()
    trace = traces[-1] if traces else {}
    facts = [check_fact(f, turn, trace, observation) for f in route["facts"]]
    facts_passed = all(f["passed"] for f in facts)
    meaning = judge(route["rubric"], {"response": turn.text, "trace": json.dumps(trace, ensure_ascii=False)}) if facts_passed else None
    return {
        "facts": facts,
        "facts_passed": facts_passed,
        "meaning": meaning,
        "passed": facts_passed and bool(meaning and meaning["passed"]),
    }


def run_route(route: dict, open_client, observation, k: int, n: int) -> dict:
    runs, passed = [], 0
    for i in range(n):
        run = run_once(route, open_client, observation)
        runs.append(run)
        passed += run["passed"]
        if passed >= k or passed + (n - i - 1) < k:
            break
    return {
        "id": route["id"],
        "edge_case": route["edge_case"],
        "origin": route["origin"],
        "k": k,
        "n": n,
        "runs": runs,
        "passed_runs": passed,
        "passed": passed >= k,
    }


def run_routes(open_client, observation, k: int | None = None, n: int | None = None, report_path: Path | None = None) -> dict:
    """Runs every official and student route; writes and returns the report."""
    k = int(k or settings.route_k)
    n = int(n or settings.route_n)
    routes = load_routes(official_dir(), "official") + load_routes(student_dir(), "student")
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "judge_mode": settings.judge_mode,
        "routes": [],
        "invalid": [],
    }
    for route in routes:
        errors = validate(route)
        if errors:
            report["invalid"].append({"file": route["file"], "origin": route["origin"], "errors": errors})
            continue
        report["routes"].append(run_route(route, open_client, observation, k, n))
    covered = {r["edge_case"] for r in report["routes"]}
    report["uncovered_edge_cases"] = [c for c in EDGE_CASES if c not in covered]
    path = report_path or repo_path(settings.my_agent_dir) / REPORT_FILE
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return report
