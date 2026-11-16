"""End-to-end tests of workshop 10b. They must fail on the empty shell.

The checks (and the contract they read) are in `checks.py`; the cases in `cases.yaml`.
"""

import pytest

from workshop_tests.testing.cases import load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__)


def test_confirmation_before_submission(services, observation):
    checks.confirmation_before_submission(services, observation, CASES["confirmation_before_submission"])


def test_preparation_refused_without_permission(services, observation):
    checks.preparation_refused_without_permission(services, observation, CASES["preparation_refused_without_permission"])


def test_text_confirmation_is_not_a_gesture(services, observation):
    case = CASES["text_confirmation_is_not_a_gesture"]
    checks.text_confirmation_is_not_a_gesture(services, observation, case, case["typed"])


def test_submission_attributed_after_confirmation(services, observation):
    checks.submission_attributed_after_confirmation(services, observation, CASES["submission_attributed_after_confirmation"])
