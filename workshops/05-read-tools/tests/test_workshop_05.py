"""End-to-end tests of workshop 05. They must fail on the empty shell.

The checks (and the trace contract they read) are in `checks.py`; the cases in `cases.yaml`.
"""

import pytest

from testkit.cases import load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__)


def test_namesakes_several_candidates(chat_client):
    checks.namesakes_several_candidates(chat_client, CASES["namesakes_several_candidates"])


def test_late_filter_applied_by_the_tool(chat_client, observation, business_client):
    checks.late_filter_applied_by_the_tool(chat_client, observation, business_client, CASES["late_filter_applied_by_the_tool"])
