"""Runs the agent's evaluation route set and writes one report per route to my-agent/route-report.md.

Each route (one YAML file under evaluation/routes/) covers an edge case of chapter 17. A route is run
`--repeat` times against the real interface (business API, docs search, proxy and interface started in
process on free ports, as in the tests). Each run is judged first on facts checked by code (events,
trace, state, tools), then on meaning with the written rubric (kit judge). A run passes only if both
pass; the route verdict is k/n.

Usage, from the repository root:
    uv run --project workshop_tests python my-agent/evaluation/run_routes.py [--repeat 3] [--route ID]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent
AGENT_DIR = HERE.parent
ROUTES_DIR = HERE / "routes"
FIXTURES_DIR = HERE / "fixtures"
REPORT = AGENT_DIR / "route-report.md"
# Run as a script: make the repository root (workshop_kit, workshop_tests) importable.
sys.path.insert(0, str(AGENT_DIR.parent))

os.environ.setdefault("OBSERVATION_TOKEN", "workshop-observation")
os.environ.setdefault("TOKEN_SECRET", "workshop-test-secret-32-bytes-long!")


def load_routes(only: str | None = None) -> list[dict[str, Any]]:
    routes = []
    for path in sorted(ROUTES_DIR.glob("*.yaml")):
        route = yaml.safe_load(path.read_text(encoding="utf-8"))
        route["file"] = path.relative_to(AGENT_DIR).as_posix()
        if only is None or route["id"] == only:
            routes.append(route)
    return routes


def _offered(trace: dict) -> set[str]:
    names = set()
    for spec in trace.get("tools_offered") or (trace.get("input") or {}).get("tools") or []:
        name = spec.get("function", {}).get("name") if isinstance(spec, dict) else spec
        if name:
            names.add(name)
    return names


def _called(trace: dict) -> list[str]:
    return [t.get("name") for t in trace.get("tools") or [] if isinstance(t, dict)]


def check_fact(fact: dict, turns: list, traces: list[dict]) -> tuple[bool, str]:
    """A fact checked by code on one run. `turn` (1-based) selects a turn; default: the last one."""
    index = int(fact.get("turn", len(turns))) - 1
    turn, trace = turns[index], traces[index]
    flat = json.dumps(trace, ensure_ascii=False)
    check = fact["check"]
    if check == "tool_called":
        ok = fact["tool"] in _called(trace)
    elif check == "tool_not_called":
        ok = fact["tool"] not in _called(trace)
    elif check == "no_tool_called":
        ok = not [n for n in _called(trace) if n not in {"load_skill"}]
    elif check == "tool_not_offered":
        ok = fact["tool"] not in _offered(trace) and fact["tool"] not in _called(trace)
    elif check == "event":
        ok = fact["event"] in turn.types
    elif check == "no_event":
        ok = fact["event"] not in turn.types
    elif check == "trace_contains":
        ok = any(p.lower() in flat.lower() for p in fact["any"])
    elif check == "state_lacks":
        ok = not (trace.get("state") or {}).get(fact["path"])
    elif check == "state_contains":
        value = json.dumps((trace.get("state") or {}).get(fact["path"]) or "", ensure_ascii=False)
        ok = any(p.lower() in value.lower() for p in fact["any"])
    elif check == "no_submission":
        ok = (trace.get("submission") or {}).get("outcome", {}).get("status") != "submitted"
    else:
        return False, f"unknown check {check!r}"
    label = check + "(" + ", ".join(f"{k}={v}" for k, v in fact.items() if k != "check") + ")"
    return ok, label


class Bench:
    """The applications of the kit, started in process like the test fixtures."""

    def __enter__(self) -> "Bench":
        from workshop_kit.apps.business_api.app import app as business_app
        from workshop_kit.apps.business_api.db import reassign
        from workshop_kit.apps.business_api.seed_data import load_dataset
        from workshop_kit.apps.docs_search.app import app as docs_app
        from workshop_kit.apps.docs_search.indexing import rebuild
        from workshop_kit.llm_proxy.app import app as proxy_app
        from workshop_kit.shell.chat_app import app as interface_app
        from workshop_kit.shell.config import settings
        from workshop_tests.testing.servers import free_port, start_uvicorn, wait_for

        self.root = Path(tempfile.mkdtemp(prefix="routes-"))
        settings.business_api_db = str(self.root / "business_api.db")
        settings.docs_search_db = str(self.root / "docs_search.db")
        settings.traces_dir = str(self.root / "traces")
        settings.token_secret = os.environ["TOKEN_SECRET"]
        settings.observation_token = os.environ["OBSERVATION_TOKEN"]
        settings.attachments_dir = str(FIXTURES_DIR)
        reassign(settings.business_api_db)
        load_dataset("standard")
        rebuild(settings.docs_search_db)
        apps = {"business_api": business_app, "docs_search": docs_app, "proxy": proxy_app, "interface": interface_app}
        ports = {name: free_port() for name in apps}
        self.servers = [start_uvicorn(app, ports[name]) for name, app in apps.items()]
        self.urls = {name: f"http://127.0.0.1:{port}" for name, port in ports.items()}
        for url in self.urls.values():
            wait_for(f"{url}/health")
        return self

    def __exit__(self, *exc) -> None:
        for server in self.servers:
            server.should_exit = True

    def run(self, route: dict) -> dict[str, Any]:
        from workshop_kit.apps.business_api.seed_data import load_dataset
        from workshop_kit.shell import tracer
        from workshop_kit.shell.chat_app import reset_conversations
        from workshop_tests.evaluation.judge import judge
        from workshop_tests.testing.chat_client import ChatClient

        load_dataset(route.get("dataset", "standard"))
        tracer.clear()
        reset_conversations()
        client = ChatClient(self.urls["interface"])
        user = route["user"]
        client.open(user_id=user["id"], role=user["role"], organization=user["organization"])
        turns = []
        for i, message in enumerate(route["turns"]):
            attachments = route.get("attachments") if i == 0 else None
            turns.append(client.turn(message, attachments=attachments))
        traces = tracer.read_all()
        if len(traces) < len(turns) or not all(t.ok for t in turns):
            errors = "; ".join(t.error or "no end event" for t in turns if not t.ok) or "missing traces"
            return {"facts": [(False, f"turn failed: {errors}")], "facts_ok": False, "meaning": None, "ok": False, "answer": ""}
        traces = traces[-len(turns):]
        facts = [check_fact(f, turns, traces) for f in route.get("facts") or []]
        facts_ok = all(ok for ok, _ in facts)
        rubric = dict(route.get("rubric") or {})
        rubric["id"] = route["id"]
        judged = int(rubric.get("turn", len(turns))) - 1
        meaning = judge(rubric, {"response": turns[judged].text, "trace": traces[judged]}) if facts_ok else None
        return {
            "facts": facts,
            "facts_ok": facts_ok,
            "meaning": meaning,
            "ok": facts_ok and bool(meaning and meaning["passed"]),
            "answer": turns[judged].text,
        }


def write_report(results: list[tuple[dict, list[dict]]], repeat: int) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Route report — evaluation of my-agent",
        "",
        f"Generated {now} by `my-agent/evaluation/run_routes.py`. Each route is repeated {repeat} times (k/{repeat} runs).",
        "A run is judged first on **facts checked by code** (deterministic: events, trace, state, tools offered "
        "and called), then on **meaning** with the written rubric (kit judge; meaning to calibrate in phase B). "
        "A run passes only if both pass.",
        "",
        "| Route (edge case) | Facts (deterministic) | Meaning (rubric) | Runs passed |",
        "|---|---|---|---|",
    ]
    for route, runs in results:
        facts = sum(r["facts_ok"] for r in runs)
        meaning = sum(bool(r["meaning"] and r["meaning"]["passed"]) for r in runs)
        passed = sum(r["ok"] for r in runs)
        lines.append(f"| {route['id']} | {facts}/{len(runs)} | {meaning}/{len(runs)} | {passed}/{len(runs)} |")
    for route, runs in results:
        passed = sum(r["ok"] for r in runs)
        lines += [
            "",
            f"## {route['id']}",
            "",
            f"- Edge case: {route['edge_case']} — {route['description']}",
            f"- Route file: `{route['file']}`; user {route['user']['id']} ({route['user']['role']}); "
            f"dataset {route.get('dataset', 'standard')}",
            f"- Repeated runs: {len(runs)}; passed {passed}/{len(runs)}",
            f"- Rubric criterion: {(route.get('rubric') or {}).get('criterion', '-')}",
        ]
        for n, run in enumerate(runs, 1):
            facts = ", ".join(("✔ " if ok else "✘ ") + label for ok, label in run["facts"])
            meaning = run["meaning"]
            verdict = "not judged (facts failed)" if meaning is None else (
                ("✔ " if meaning["passed"] else "✘ ") + meaning["rationale"]
            )
            answer = " ".join(run["answer"].split())[:220].replace("|", "/")
            lines += [
                f"- Run {n}: {'PASS' if run['ok'] else 'FAIL'}",
                f"  - Facts: {facts}",
                f"  - Meaning: {verdict}",
                f"  - Answer: {answer}",
            ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--route")
    args = parser.parse_args(argv)
    routes = load_routes(args.route)
    results = []
    with Bench() as bench:
        for route in routes:
            runs = [bench.run(route) for _ in range(args.repeat)]
            results.append((route, runs))
            print(f"{route['id']}: {sum(r['ok'] for r in runs)}/{len(runs)}", flush=True)
    write_report(results, args.repeat)
    print(f"report: {REPORT}")
    return 0 if all(all(r["ok"] for r in runs) for _, runs in results) else 1


if __name__ == "__main__":
    sys.exit(main())
