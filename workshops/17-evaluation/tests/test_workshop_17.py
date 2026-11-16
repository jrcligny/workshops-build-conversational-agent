"""End-to-end tests of workshop 17. They must fail on the empty shell.

The trace checks (and the contract they read) are in `checks.py`; their cases in `cases.yaml`.

Routes: official routes in `workshops/17-evaluation/routes/cases/`, the student's own in
`my-agent/routes/` (same YAML format, see `workshop_tests/evaluation/route_runner.py`);
the runner writes `my-agent/route-report.json`. The test checks the report, not keywords.
"""

import json

import pytest

from workshop_tests.evaluation import route_runner
from workshop_tests.evaluation.routes import expected_digest, routes_digest
from workshop_tests.testing.cases import load_cases, load_checks
from workshop_tests.testing.chat_client import ChatClient

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__)


def test_masked_and_observable_traces(chat_client, traces):
    checks.masked_and_observable_traces(chat_client, traces, CASES["masked_and_observable_traces"])


# Public only: the route tests have no input to vary, hence no case and no private variant.
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
