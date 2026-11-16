"""End-to-end tests of workshop 17. They must fail on the empty shell.

Contract read here:
- traces: no secret (Authorization header, bearer token, API key) appears in a trace;
- trace `model.usage` and `model.duration_ms` (whole turn), `model.calls[]` (one entry per model call) and
  `tools[]` (one entry per tool call, with `duration_ms`): a turn is observable end to end;
- routes: official routes in `workshops/17-evaluation/routes/cases/`, the student's own in
  `my-agent/routes/` (same YAML format, see `workshop_tests/evaluation/route_runner.py`);
  the runner writes `my-agent/route-report.json`. The test checks the report, not keywords.
"""

import json

import pytest

from workshop_tests.evaluation import route_runner
from workshop_tests.evaluation.routes import expected_digest, routes_digest
from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.turns import flat, successful_turn, tools

pytestmark = pytest.mark.workshop


def test_masked_and_observable_traces(chat_client, traces):
    successful_turn(chat_client, "Quel est le statut de la commande CMD-1042 ?")
    trace = traces.last()
    flat_t = flat(trace).lower()
    assert "authorization" not in flat_t and "bearer " not in flat_t
    assert "azure_openai_api_key" not in flat_t and "eyj" not in flat_t, "no secret or token in the trace"
    model = trace.get("model") or {}
    assert model.get("usage") and "duration_ms" in model and model.get("calls"), "trace.model records usage, duration_ms and calls"
    assert tools(trace) and all("duration_ms" in c for c in tools(trace)), "each tool call records duration_ms"


def test_student_routes_cover_every_edge_case():
    assert route_runner.load_routes(route_runner.official_dir(), "official"), "official routes are published"
    assert routes_digest() == expected_digest(), "the official routes are not modified"
    routes = route_runner.load_routes(route_runner.student_dir(), "student")
    assert routes, "my-agent/routes/ holds your own routes"
    invalid = {r["file"]: route_runner.validate(r) for r in routes if route_runner.validate(r)}
    assert not invalid, f"invalid routes: {invalid}"
    missing = set(route_runner.EDGE_CASES) - {r["edge_case"] for r in routes}
    assert not missing, f"edge cases without a route of yours: {sorted(missing)}"
    ids = {r["id"] for r in routes}
    assert any(r.get("counterfactual_of") in ids for r in routes), (
        "at least one route is a counterfactual (counterfactual_of: <id of another of your routes>)"
    )


def test_route_report(services, observation):
    def open_client(user_id, role, organization):
        client = ChatClient(services["interface"])
        client.open(user_id=user_id, role=role, organization=organization)
        return client

    report = route_runner.run_routes(open_client, observation)
    assert not report["invalid"], f"invalid routes: {report['invalid']}"
    assert not report["uncovered_edge_cases"], f"uncovered edge cases: {report['uncovered_edge_cases']}"
    written = json.loads((route_runner.student_dir().parent / route_runner.REPORT_FILE).read_text(encoding="utf-8"))
    assert [(r["id"], r["passed"]) for r in written["routes"]] == [(r["id"], r["passed"]) for r in report["routes"]], (
        "the report written on disk is the one of this run"
    )
    assert any(r["origin"] == "student" for r in report["routes"]), "your own routes are run, not only the official ones"
    for route in report["routes"]:
        for run in route["runs"]:
            kinds = {f["fact"].get("type") for f in run.get("facts") or []}
            assert not kinds or kinds - route_runner.TEXT_FACTS, f"{route['id']}: a run checks the trace or the application, not only the text"
    for route in report["routes"]:
        assert route["runs"] and all("facts" in run for run in route["runs"]), "each run reports its facts"
    failed = [f"{r['origin']}:{r['id']} ({r['passed_runs']}/{r['k']} of {r['n']})" for r in report["routes"] if not r["passed"]]
    assert not failed, "routes below the k out of n rule: " + ", ".join(failed)
