"""End-to-end tests of workshop 06 (steps `serveur` and `regroupements`). They must fail on the
empty shell.

The checks (and the contract they read) are in `checks.py`; the cases in `cases.yaml`.
"""

import pytest

from agent_testkit.cases import load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__)
serveur = pytest.mark.etape("serveur")
regroupements = pytest.mark.etape("regroupements")


@pytest.fixture(scope="module")
def mcp_server_url():
    yield from checks.serve_mcp_server()


@serveur
def test_two_clients_get_the_same_catalog(mcp_server_url):
    checks.two_clients_get_the_same_catalog(mcp_server_url, CASES["two_clients_get_the_same_catalog"])


@serveur
def test_tools_served_by_mcp(chat_client, observation, mcp_server_url):
    checks.tools_served_by_mcp(chat_client, observation, mcp_server_url, CASES["tools_served_by_mcp"])


@serveur
def test_malformed_filter_actionable_error(chat_client):
    checks.malformed_filter_actionable_error(chat_client, CASES["malformed_filter_actionable_error"])


@serveur
def test_accountant_question_through_the_generic_query(services, observation):
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
