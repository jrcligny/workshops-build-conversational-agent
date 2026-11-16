"""End-to-end tests of workshop 10a. They must fail on the empty shell.

The checks (and the contract they read) are in `checks.py`; the cases in `cases.yaml`.
"""

import pytest

from workshop_tests.testing.cases import load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__)
REFUSED = CASES["request_without_identity_refused"]


def test_token_exchange(services, observation):
    checks.token_exchange(services, observation, CASES["token_exchange"])


@pytest.mark.parametrize("scenario", REFUSED["scenarios"], ids=lambda s: s["id"])
def test_request_without_identity_refused(services, observation, scenario):
    checks.request_without_identity_refused(services, observation, scenario, REFUSED)


def test_other_organization_sees_nothing(services, observation):
    checks.other_organization_sees_nothing(services, observation, CASES["other_organization_sees_nothing"])


@pytest.fixture(scope="module")
def mcp_server_url():
    yield from checks.serve_mcp_server()


def test_mcp_server_requires_the_entry_token(mcp_server_url, observation):
    checks.mcp_server_requires_the_entry_token(mcp_server_url, observation, CASES["mcp_server_requires_the_entry_token"])
