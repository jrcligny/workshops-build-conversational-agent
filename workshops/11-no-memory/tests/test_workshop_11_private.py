"""Private tests of workshop 11 (not given to students): same checks (`checks.py`), other cases
(`cases_private.yaml`): other users, organizations and topics (answer_format, including_tax), another
recalled conclusion, and business data that is never reported.
"""

import pytest

from agent_testkit.cases import PRIVATE_CASES, load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)


def test_no_memory_announced_on_opening(services, reset_state):
    checks.no_memory_announced_on_opening(services, CASES["no_memory_announced_on_opening"])


def test_no_promise_to_remember(services, reset_state):
    checks.no_promise_to_remember(services, CASES["no_promise_to_remember"])


def test_preference_absent_from_next_conversation(services, reset_state):
    checks.preference_absent_from_next_conversation(services, CASES["preference_absent_from_next_conversation"])


def test_recurring_preference_reported_never_reloaded(services, reset_state):
    checks.recurring_preference_reported_never_reloaded(services, CASES["recurring_preference_reported_never_reloaded"])


def test_business_data_never_reported(services, reset_state):
    # Private only: a durable request that mixes business data and bank details reports neither.
    checks.business_data_never_reported(services, CASES["business_data_never_reported"])


def test_rereads_rather_than_assumes(chat_client, observation):
    checks.rereads_rather_than_assumes(chat_client, observation, CASES["rereads_rather_than_assumes"])
