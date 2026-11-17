"""End-to-end tests of workshop 07. They must fail on the empty shell.

Three steps share one scenario (a buyer prepares a purchase request): `identite` (the user's
identity, exchanged at the entry), `ecritures` (prepare, then submit only after the gesture),
`confinement` (sandbox, limits, secrets); `workshop check 07 --etape <step>` runs one of them.
The checks (and the contract they read) are in `checks.py`; the cases in `cases.yaml`.
"""

import pytest

from agent_testkit.cases import load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__)
REFUSED = CASES["request_without_identity_refused"]


@pytest.fixture(scope="module")
def mcp_server_url():
    yield from checks.serve_mcp_server()


@pytest.mark.etape("identite")
def test_token_exchange(services, observation):
    checks.token_exchange(services, observation, CASES["token_exchange"])


@pytest.mark.etape("identite")
@pytest.mark.parametrize("scenario", REFUSED["scenarios"], ids=lambda s: s["id"])
def test_request_without_identity_refused(services, observation, scenario):
    checks.request_without_identity_refused(services, observation, scenario, REFUSED)


@pytest.mark.etape("identite")
def test_caches_partitioned_by_organization(services, observation):
    checks.caches_partitioned_by_organization(services, observation, CASES["caches_partitioned_by_organization"])


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
def test_text_confirmation_is_not_a_gesture(services, observation):
    case = CASES["text_confirmation_is_not_a_gesture"]
    checks.text_confirmation_is_not_a_gesture(services, observation, case, case["typed"])


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
def test_turn_stopped_at_the_limit(services, reset_state):
    checks.turn_stopped_at_the_limit(services, CASES["turn_stopped_at_the_limit"])
