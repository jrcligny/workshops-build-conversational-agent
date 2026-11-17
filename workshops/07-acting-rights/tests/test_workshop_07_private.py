"""Private tests of workshop 07 (not given to students): same checks (`checks.py`), other cases
(`cases_private.yaml`).

identite: other users (paul-buyer, nina-accountant, omar-buyer-b), another order (CMD-2010), a
positive read in organization-b (CMD-B-100). ecritures: another buyer in another organization,
another amount (85,50 €), other phrasings of the typed confirmation, a refused gesture.
confinement: destinations that look like the business application, each limit on its own,
another way to ask for the secret.
"""

import pytest

from agent_testkit.cases import PRIVATE_CASES, load_cases, load_checks
from agent_testkit.chat_client import ChatClient
from agent_testkit.expect import expect_event, mentions_any
from agent_testkit.turns import business_log, successful_turn
from business_api.auth import issue_token

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)
REFUSED = CASES["request_without_identity_refused"]


@pytest.fixture(scope="module")
def mcp_server_url():
    yield from checks.serve_mcp_server()


@pytest.mark.etape("identite")
def test_token_exchange_for_another_user(services, observation):
    checks.token_exchange(services, observation, CASES["token_exchange"])


@pytest.mark.etape("identite")
@pytest.mark.parametrize("scenario", REFUSED["scenarios"], ids=lambda s: s["id"])
def test_request_without_identity_refused(services, observation, scenario):
    checks.request_without_identity_refused(services, observation, scenario, REFUSED)


@pytest.mark.etape("identite")
def test_caches_partitioned_by_organization(services, observation):
    checks.caches_partitioned_by_organization(services, observation, CASES["caches_partitioned_by_organization"])


@pytest.mark.etape("identite")
def test_other_organization_reads_its_own_order(services, observation):
    # Private only: the organization-b user does read the orders of organization-b.
    case = CASES["other_organization_reads_its_own_order"]
    user = case["user"]
    client = ChatClient(services["interface"])
    client.open(**user, app_token=issue_token(user["user_id"], user["role"], user["organization"], typ="entry"))
    turn, _ = successful_turn(client, case["question"])
    log = checks.data_log(observation)
    assert log and {e.get("user_id") for e in log} == {user["user_id"]}
    assert any(e.get("code") == 200 for e in log), "the organization-b user reads the orders of organization-b"
    mentions_any(turn, case["answer_status"], "the answer gives the status read in organization-b")


@pytest.mark.etape("identite")
def test_mcp_server_requires_the_entry_token(mcp_server_url, observation):
    checks.mcp_server_requires_the_entry_token(mcp_server_url, observation, CASES["mcp_server_requires_the_entry_token"])


@pytest.mark.etape("ecritures")
def test_confirmation_before_submission(services, observation):
    checks.confirmation_before_submission(services, observation, CASES["confirmation_before_submission"])


@pytest.mark.etape("ecritures")
def test_preparation_refused_without_permission(services, observation):
    checks.preparation_refused_without_permission(services, observation, CASES["preparation_refused_without_permission"])


@pytest.mark.etape("ecritures")
@pytest.mark.parametrize("typed", CASES["text_confirmation_is_not_a_gesture"]["typed"])
def test_text_confirmation_is_not_a_gesture(services, observation, typed):
    checks.text_confirmation_is_not_a_gesture(services, observation, CASES["text_confirmation_is_not_a_gesture"], typed)


@pytest.mark.etape("ecritures")
def test_refused_gesture_submits_nothing(services, observation):
    # Private only: a refused confirmation gesture submits nothing, not even an attempt.
    case = CASES["refused_gesture_submits_nothing"]
    client = checks.open_client(services, case["buyer"])
    turn, _ = successful_turn(client, case["request"])
    draft_id = expect_event(turn, "confirmation_requested", message="a confirmation is requested")[0].get("draft_id")
    assert draft_id and observation.state("submissions")["drafts"], "a draft is prepared and waits for the gesture"
    client.confirm(False)
    successful_turn(client, case["refusal"])
    assert observation.state("submissions")["submitted_requests"] == [], "a refused confirmation submits nothing"
    submits = [e for e in business_log(observation) if e.get("method") == "POST" and str(e.get("route", "")).endswith("/submit")]
    assert not submits, "no submission is even attempted after a refused gesture"


@pytest.mark.etape("ecritures")
def test_submission_attributed_after_confirmation(services, observation):
    checks.submission_attributed_after_confirmation(services, observation, CASES["submission_attributed_after_confirmation"])


@pytest.mark.etape("confinement")
def test_destination_outside_allowlist_refused(chat_client, services):
    checks.destination_outside_allowlist_refused(chat_client, services, CASES["destination_outside_allowlist_refused"])


@pytest.mark.etape("confinement")
def test_write_turn_stays_confined(services, observation):
    checks.write_turn_stays_confined(services, CASES["write_turn_stays_confined"])


@pytest.mark.etape("confinement")
@pytest.mark.parametrize("case", CASES["turn_stopped_at_each_limit"], ids=lambda c: c["id"])
def test_turn_stopped_at_each_limit(services, reset_state, case):
    checks.turn_stopped_at_the_limit(services, case)
