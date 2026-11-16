"""Private tests of workshop 09 (not given to students): same checks (`checks.py`), other cases
(`cases_private.yaml`).

Another question served by MCP, another malformed filter value, another aggregate for the
accountant (average, expected value read from the business API). The catalog test has no input
to vary and has no private variant.
"""

import pytest

from workshop_tests.testing.cases import PRIVATE_CASES, load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)


@pytest.fixture(scope="module")
def mcp_server_url():
    yield from checks.serve_mcp_server()


def test_tools_served_by_mcp(chat_client, observation, mcp_server_url):
    checks.tools_served_by_mcp(chat_client, observation, mcp_server_url, CASES["tools_served_by_mcp"])


def test_malformed_filter_actionable_error(chat_client):
    checks.malformed_filter_actionable_error(chat_client, CASES["malformed_filter_actionable_error"])


def test_accountant_average_through_the_generic_query(services, observation):
    checks.accountant_aggregate_through_the_generic_query(services, observation, CASES["accountant_aggregate"])
