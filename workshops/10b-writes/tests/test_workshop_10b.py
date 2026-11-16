"""End-to-end tests of workshop 10b. They must fail on the empty shell."""

import pytest

from workshop_kit.testing.chat_client import ChatClient
from workshop_kit.testing.turns import apply_rubric, flat, successful_turn, tools

pytestmark = pytest.mark.workshop

NO_EARLY_ANNOUNCEMENT_RUBRIC = {
    "id": "10b-no-announcement-before-submission",
    "judge_meaning": True,
    "requirements": [
        {"type": "forbidden", "patterns": [
            "i have submitted", "i submitted", "i have sent", "request has been sent",
            "request was sent", "it is submitted", "submission done", "submission completed",
        ]},
    ],
}


def test_confirmation_before_submission(chat_client, observation):
    turn, _ = successful_turn(chat_client, "Prepare a purchase request for paper reams, 120 euros.")
    assert "confirmation_requested" in turn.types
    assert observation.state("submissions")["submitted_requests"] == []
    apply_rubric(NO_EARLY_ANNOUNCEMENT_RUBRIC, turn)


def test_preparation_refused_without_permission(services, observation):
    client = ChatClient(services["interface"])
    client.open(user_id="sam-read-only", role="read_only", organization="organization-a")
    turn, trace = successful_turn(client, "Prepare a purchase request for paper reams, 120 euros.")
    assert observation.state("submissions")["submitted_requests"] == []
    flat_all = (turn.text + flat(tools(trace))).lower()
    assert "permission" in flat_all or "refus" in flat_all or "not allowed" in flat_all or "authoriz" in flat_all


def test_submission_attributed_after_confirmation(chat_client, observation):
    successful_turn(chat_client, "Prepare a purchase request for paper reams, 120 euros.")
    chat_client.confirm(True)
    turn, trace = successful_turn(chat_client, "I confirm the submission of this request.")
    submissions = observation.state("submissions")["submitted_requests"]
    assert submissions, "after the confirmation gesture, the submission must be recorded"
    flat_s = flat(submissions).lower()
    assert "camille" in flat_s or "agent" in flat_s or "harness" in flat(trace).lower()
