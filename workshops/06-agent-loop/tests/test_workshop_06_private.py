"""Private tests of workshop 06 (not given to students): same checks (`checks.py`), other cases
(`cases_private.yaml`): other chained and grouped questions (Léa Martin of Lyon, Martin Durand,
CMD-2010), another long review and other interrupted requests.
"""

import pytest

from agent_testkit.cases import PRIVATE_CASES, load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)


def test_several_cycles(chat_client):
    checks.several_cycles(chat_client, CASES["several_cycles"])


def test_independent_calls_grouped(chat_client):
    checks.independent_calls_grouped(chat_client, CASES["independent_calls_grouped"])


def test_steps_reported_to_the_interface(chat_client):
    checks.steps_reported_to_the_interface(chat_client, CASES["steps_reported_to_the_interface"])


def test_cycle_limit_partial_answer(chat_client):
    checks.cycle_limit_partial_answer(chat_client, CASES["cycle_limit_partial_answer"])


def test_interruption_stops_without_new_call(chat_client):
    checks.interruption_stops_without_new_call(chat_client, CASES["interruption_stops_without_new_call"])


def test_without_interruption_the_same_request_runs(chat_client):
    checks.without_interruption_the_same_request_runs(chat_client, CASES["without_interruption_the_same_request_runs"])
