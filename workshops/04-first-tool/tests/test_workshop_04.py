"""End-to-end tests of workshop 04. They must fail on the empty shell.

The checks (and the trace contract they read) are in `checks.py`; the cases in `cases.yaml`.
"""

import pytest

from workshop_tests.testing.cases import load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__)


def test_exact_order_lookup(chat_client, services):
    checks.exact_order_lookup(chat_client, services, CASES["exact_order_lookup"])


def test_swapped_reference_reported(chat_client):
    checks.swapped_reference_reported(chat_client, CASES["swapped_reference_reported"])


def test_deleted_order_never_suggested(chat_client):
    checks.excluded_order_never_returned(chat_client, CASES["deleted_order_never_suggested"])


def test_invalid_reference_rejected_before_the_call(chat_client, observation):
    checks.invalid_reference_rejected_before_the_call(chat_client, observation, CASES["invalid_reference_rejected_before_the_call"])