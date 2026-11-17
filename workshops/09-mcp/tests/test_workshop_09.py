"""End-to-end tests of workshop 09. They must fail on the empty shell.

The checks (and the contract they read) are in `checks.py`; the cases in `cases.yaml`.
"""

import pytest

from testkit.cases import load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__)


@pytest.fixture(scope="module")
def mcp_server_url():
    yield from checks.serve_mcp_server()


def test_two_clients_get_the_same_catalog(mcp_server_url):
    checks.two_clients_get_the_same_catalog(mcp_server_url, CASES["two_clients_get_the_same_catalog"])


def test_tools_served_by_mcp(chat_client, observation, mcp_server_url):
    checks.tools_served_by_mcp(chat_client, observation, mcp_server_url, CASES["tools_served_by_mcp"])


def test_malformed_filter_actionable_error(chat_client):
    checks.malformed_filter_actionable_error(chat_client, CASES["malformed_filter_actionable_error"])


def test_accountant_question_through_the_generic_query(services, observation):
    checks.accountant_aggregate_through_the_generic_query(services, observation, CASES["accountant_aggregate"])
