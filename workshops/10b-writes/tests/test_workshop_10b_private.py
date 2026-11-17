"""Private tests of workshop 10b (not given to students): same checks (`checks.py`), other cases
(`cases_private.yaml`).

Another buyer in another organization (omar-buyer-b), another subject and amount (85,50 €),
another user without the write permission (camille-renard, customer service) and other
phrasings of the typed confirmation.
"""

import pytest

from agent_testkit.cases import PRIVATE_CASES, load_cases, load_checks
from agent_testkit.turns import business_log, events_of, successful_turn

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)


def test_confirmation_before_submission(services, observation):
    checks.confirmation_before_submission(services, observation, CASES["confirmation_before_submission"])


def test_preparation_refused_without_permission(services, observation):
    checks.preparation_refused_without_permission(services, observation, CASES["preparation_refused_without_permission"])


@pytest.mark.parametrize("typed", CASES["text_confirmation_is_not_a_gesture"]["typed"])
def test_text_confirmation_is_not_a_gesture(services, observation, typed):
    checks.text_confirmation_is_not_a_gesture(services, observation, CASES["text_confirmation_is_not_a_gesture"], typed)


def test_refused_gesture_submits_nothing(services, observation):
    # Private only: a refused confirmation gesture submits nothing, not even an attempt.
    case = CASES["refused_gesture_submits_nothing"]
    client = checks.open_client(services, case["buyer"])
    turn, _ = successful_turn(client, case["request"])
    draft_id = (events_of(turn, "confirmation_requested") or [{}])[0].get("draft_id")
    assert draft_id and observation.state("submissions")["drafts"], "a draft is prepared and waits for the gesture"
    client.confirm(False)
    turn, _ = successful_turn(client, case["refusal"])
    assert observation.state("submissions")["submitted_requests"] == [], "a refused confirmation submits nothing"
    submits = [e for e in business_log(observation) if e.get("method") == "POST" and str(e.get("route", "")).endswith("/submit")]
    assert not submits, "no submission is even attempted after a refused gesture"


def test_submission_attributed_after_confirmation(services, observation):
    checks.submission_attributed_after_confirmation(services, observation, CASES["submission_attributed_after_confirmation"])
