"""Private tests of workshop 05 (not given to students): same checks (`checks.py`), other cases
(`cases_private.yaml`): the same scenario on Hugo Petit (namesakes, Bordeaux and Strasbourg) and
Martin Durand (late filter on both datasets), and another long review.
"""

import pytest

from agent_testkit.cases import PRIVATE_CASES, load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)


@pytest.mark.etape("outils")
def test_namesakes_several_candidates(chat_client):
    checks.namesakes_several_candidates(chat_client, CASES["namesakes_several_candidates"])


@pytest.mark.etape("outils")
@pytest.mark.parametrize("case", CASES["late_filter_applied_by_the_tool"], ids=lambda c: c["dataset"])
@pytest.mark.superseded_by("06")  # 06 replaces filter="late" by the generic query (filters)
def test_late_filter_applied_by_the_tool(chat_client, observation, business_client, case):
    checks.late_filter_applied_by_the_tool(chat_client, observation, business_client, case)


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
