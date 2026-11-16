"""End-to-end tests of workshop 10d. They must fail on the empty shell.

The checks (and the contract they read) are in `checks.py`; the cases in `cases.yaml`.
"""

import pytest

from workshop_tests.testing.cases import load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__)


def test_sandbox_policy_active(services):
    checks.sandbox_policy(services, CASES["sandbox_policy_active"])


def test_destination_outside_allowlist_refused(chat_client, services):
    checks.destination_outside_allowlist_refused(chat_client, services, CASES["destination_outside_allowlist_refused"])


def test_no_file_access_during_a_normal_turn(chat_client):
    checks.no_file_access_during_a_normal_turn(chat_client, CASES["no_file_access_during_a_normal_turn"])


def test_turn_stopped_at_the_limit(services, reset_state):
    checks.turn_stopped_at_the_limit(services, CASES["turn_stopped_at_the_limit"])


def test_secret_absent_from_the_context(chat_client, observation, services):
    checks.secret_absent_from_the_context(chat_client, CASES["secret_absent_from_the_context"])
