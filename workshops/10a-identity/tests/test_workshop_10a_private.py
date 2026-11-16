"""Private tests of workshop 10a (not given to students): same checks (`checks.py`), other cases
(`cases_private.yaml`).

Other users (paul-buyer, nina-accountant, omar-buyer-b, ines-service-b), another order
(CMD-2010), a positive read in organization-b (CMD-B-100) and the MCP server called with
another user's entry token.
"""

import pytest

from business_api.auth import issue_token
from workshop_tests.testing.cases import PRIVATE_CASES, load_cases, load_checks
from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.turns import successful_turn

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)
REFUSED = CASES["request_without_identity_refused"]


def test_token_exchange_for_another_user(services, observation):
    checks.token_exchange(services, observation, CASES["token_exchange"])


@pytest.mark.parametrize("scenario", REFUSED["scenarios"], ids=lambda s: s["id"])
def test_request_without_identity_refused(services, observation, scenario):
    checks.request_without_identity_refused(services, observation, scenario, REFUSED)


def test_other_organization_sees_nothing(services, observation):
    checks.other_organization_sees_nothing(services, observation, CASES["other_organization_sees_nothing"])


def test_other_organization_reads_its_own_order(services, observation):
    # Private only: the organization-b user does read the orders of organization-b.
    client = ChatClient(services["interface"])
    token = issue_token("ines-service-b", "customer_service", "organization-b", typ="entry")
    client.open(user_id="ines-service-b", role="customer_service", organization="organization-b", app_token=token)
    turn, _ = successful_turn(client, "Quel est le statut de la commande CMD-B-100 ?")
    log = checks.data_log(observation)
    assert log and {e.get("user_id") for e in log} == {"ines-service-b"}
    assert any(e.get("code") == 200 for e in log), "the organization-b user reads the orders of organization-b"
    assert "livrée" in turn.text.lower()


@pytest.fixture(scope="module")
def mcp_server_url():
    yield from checks.serve_mcp_server()


def test_mcp_server_requires_the_entry_token(mcp_server_url, observation):
    checks.mcp_server_requires_the_entry_token(mcp_server_url, observation, CASES["mcp_server_requires_the_entry_token"])
