"""End-to-end tests of workshop 10a. They must fail on the empty shell."""

import pytest

from workshop_kit.apps.business_api.auth import issue_token
from workshop_kit.testing.chat_client import ChatClient
from workshop_kit.testing.turns import business_log, flat, successful_turn

pytestmark = pytest.mark.workshop


def test_token_exchange(chat_client, observation, services):
    token = observation.token("camille-renard")
    chat_client.open(app_token=token["app_token"])
    turn, trace = successful_turn(chat_client, "What is the status of order CMD-1042?")
    log = business_log(observation)
    assert log, "the application must receive a call on behalf of the user"
    flat_log = flat(log).lower()
    assert "camille-renard" in flat_log or "camille" in flat_log
    assert "service-account" not in flat_log
    assert trace.get("identity") or any("application" in str(e).lower() for e in log)


def test_request_without_identity_refused(services, observation):
    # An entry token (typ=entry) is not accepted by the application: the tool server
    # must exchange it, not relay it. A turn without exchange lets the API refuse.
    wrong = issue_token("camille-renard", "customer_service", "organization-a", typ="entry")
    client = ChatClient(services["interface"])
    client.open(app_token=wrong)
    turn, trace = successful_turn(client, "What is the status of order CMD-1042?")
    log = business_log(observation)
    # either no business call went through (refused upstream), or the API answered 401
    codes = [e.get("code") or e.get("status") for e in log]
    assert (not log) or any(c in {401, 403, "401", "403"} for c in codes) or "refus" in flat(trace).lower() or "identity" in turn.text.lower()
