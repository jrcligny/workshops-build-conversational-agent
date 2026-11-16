"""End-to-end tests of workshop 18. They must fail on the empty shell.

The checks (and the contract they read) are in `checks.py`; the cases (rubrics included) in
`cases.yaml`.
"""

import pytest

from workshop_tests.testing.cases import load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__)


def test_submission_never_replayed(services, observation):
    checks.submission_never_replayed(services, observation, CASES["submission_never_replayed"])


def test_single_fallback_then_end(chat_client, services):
    checks.single_fallback_then_end(chat_client, services, CASES["single_fallback_then_end"])


def test_versions_in_the_trace(chat_client, services):
    checks.versions_in_the_trace(chat_client, services, CASES["versions_in_the_trace"])
