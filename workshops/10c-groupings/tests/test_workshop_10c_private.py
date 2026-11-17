"""Private tests of workshop 10c (not given to students): same checks (`checks.py`), other cases
(`cases_private.yaml`).

Other groupings (total of the shipped orders, count of the orders), other filters (a status),
another request for model-written code and another phrasing of the refused median. The
expected values are read from the business API.
"""

import pytest

from testkit.cases import PRIVATE_CASES, load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)


def test_grouping_with_a_status_filter(chat_client, observation, business_client):
    checks.grouping_computed_by_the_tool(chat_client, observation, business_client, CASES["grouping_computed_by_the_tool"])


def test_no_model_generated_code_is_executed(chat_client, observation, business_client):
    checks.no_model_generated_code_is_executed(chat_client, observation, business_client, CASES["no_model_generated_code_is_executed"])


def test_median_refused_aggregates_offered(services, chat_client):
    checks.median_refused_aggregates_offered(chat_client, CASES["median_refused_aggregates_offered"])
