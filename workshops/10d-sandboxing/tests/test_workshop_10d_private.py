"""Private tests of workshop 10d (not given to students): same checks (`checks.py`), other cases
(`cases_private.yaml`): other refused destinations (cloud metadata address, a host that only
starts like the business application), each limit on its own, another order and another way to
ask for the secret.
"""

import pytest

from agent_testkit.cases import PRIVATE_CASES, load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)


def test_sandbox_policy_refuses_look_alike_destinations(services):
    checks.sandbox_policy(services, CASES["sandbox_policy_refuses_look_alike_destinations"])


def test_destination_outside_allowlist_refused(chat_client, services):
    checks.destination_outside_allowlist_refused(chat_client, services, CASES["destination_outside_allowlist_refused"])


def test_no_file_access_during_a_normal_turn(chat_client):
    checks.no_file_access_during_a_normal_turn(chat_client, CASES["no_file_access_during_a_normal_turn"])


@pytest.mark.parametrize("case", CASES["turn_stopped_at_each_limit"], ids=lambda c: c["id"])
def test_turn_stopped_at_each_limit(services, reset_state, case):
    checks.turn_stopped_at_the_limit(services, case)


def test_secret_absent_from_the_context(chat_client, services):
    checks.secret_absent_from_the_context(chat_client, CASES["secret_absent_from_the_context"])
