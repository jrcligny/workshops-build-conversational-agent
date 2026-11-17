"""End-to-end tests of workshop 05. They must fail on the empty shell.

Two steps share one scenario (late orders of a customer): `outils` (the read tools), then
`boucle` (the agent loop); `workshop check 05 --etape <step>` runs one of them. The checks (and
the trace contract they read) are in `checks.py`; the cases in `cases.yaml`.
"""

import pytest

from agent_testkit.cases import load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__)


@pytest.mark.etape("outils")
def test_namesakes_several_candidates(chat_client):
    checks.namesakes_several_candidates(chat_client, CASES["namesakes_several_candidates"])


@pytest.mark.etape("outils")
def test_late_filter_applied_by_the_tool(chat_client, observation, business_client):
    checks.late_filter_applied_by_the_tool(chat_client, observation, business_client, CASES["late_filter_applied_by_the_tool"])


@pytest.mark.etape("boucle")
def test_several_cycles(chat_client):
    checks.several_cycles(chat_client, CASES["several_cycles"])


@pytest.mark.etape("boucle")
def test_independent_calls_grouped(chat_client):
    checks.independent_calls_grouped(chat_client, CASES["independent_calls_grouped"])


@pytest.mark.etape("boucle")
def test_steps_reported_to_the_interface(chat_client):
    checks.steps_reported_to_the_interface(chat_client, CASES["steps_reported_to_the_interface"])


@pytest.mark.etape("boucle")
def test_cycle_limit_partial_answer(chat_client):
    checks.cycle_limit_partial_answer(chat_client, CASES["cycle_limit_partial_answer"])


@pytest.mark.etape("boucle")
def test_interruption_stops_without_new_call(chat_client):
    checks.interruption_stops_without_new_call(chat_client, CASES["interruption_stops_without_new_call"])


@pytest.mark.etape("boucle")
def test_without_interruption_the_same_request_runs(chat_client):
    checks.without_interruption_the_same_request_runs(chat_client, CASES["without_interruption_the_same_request_runs"])
