"""End-to-end tests of workshop 10c. They must fail on the empty shell.

The checks (and the contract they read) are in `checks.py`; the cases in `cases.yaml`.
"""

import pytest

from testkit.cases import load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__)


def test_grouping_computed_by_the_tool(chat_client, observation, business_client):
    checks.grouping_computed_by_the_tool(chat_client, observation, business_client, CASES["grouping_computed_by_the_tool"])


def test_no_model_generated_code_is_executed(chat_client, observation, business_client):
    checks.no_model_generated_code_is_executed(chat_client, observation, business_client, CASES["no_model_generated_code_is_executed"])


def test_median_refused_aggregates_offered(services, chat_client):
    checks.median_refused_aggregates_offered(chat_client, CASES["median_refused_aggregates_offered"])
