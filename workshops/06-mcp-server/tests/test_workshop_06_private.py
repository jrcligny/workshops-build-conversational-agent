"""Private tests of workshop 06 (not given to students): same checks (`checks.py`), other cases
(`cases_private.yaml`).

Another question served by MCP, another malformed filter value, another aggregate for the
accountant (average); another grouping for the controller (count by supplier and month),
another request for model-written code and another phrasing of the refused median. The
expected values are read from the business API. The catalog test has no input to vary and has
no private variant.
"""

import pytest

from agent_testkit.cases import PRIVATE_CASES, load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)
serveur = pytest.mark.etape("serveur")
regroupements = pytest.mark.etape("regroupements")


@pytest.fixture(scope="module")
def mcp_server_url():
    yield from checks.serve_mcp_server()


@serveur
def test_tools_served_by_mcp(chat_client, observation, mcp_server_url):
    checks.tools_served_by_mcp(chat_client, observation, mcp_server_url, CASES["tools_served_by_mcp"])


@serveur
def test_malformed_filter_actionable_error(chat_client):
    checks.malformed_filter_actionable_error(chat_client, CASES["malformed_filter_actionable_error"])


@serveur
def test_accountant_average_through_the_generic_query(services, observation):
    checks.accountant_aggregate_through_the_generic_query(services, observation, CASES["accountant_aggregate"])


@regroupements
def test_grouping_by_supplier_and_month(services, observation):
    checks.grouping_by_two_keys(services, observation, CASES["grouping_by_two_keys"])


@regroupements
def test_no_model_generated_code_is_executed(chat_client, observation, business_client):
    checks.no_model_generated_code_is_executed(chat_client, observation, business_client, CASES["no_model_generated_code_is_executed"])


@regroupements
def test_median_refused_aggregates_offered(services, chat_client):
    checks.median_refused_aggregates_offered(chat_client, CASES["median_refused_aggregates_offered"])
