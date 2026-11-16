"""End-to-end tests of workshop 10b. They must fail on the empty shell."""

import pytest

from workshop_kit.testing.chat_client import ChatClient
from workshop_kit.testing.turns import apply_rubric, flat, successful_turn, tools

pytestmark = pytest.mark.workshop

NO_EARLY_ANNOUNCEMENT_RUBRIC = {
    "id": "10b-no-announcement-before-submission",
    "criterion": "The agent, answering in French, never announces a submission that has not happened yet.",
    "judge_meaning": True,
    "requirements": [
        {"type": "forbidden", "patterns": [
            "j'ai soumis", "j'ai envoyé", "demande a été envoyée", "demande a été soumise",
            "demande est soumise", "c'est soumis", "soumission effectuée", "soumission faite",
        ]},
    ],
}


def test_confirmation_before_submission(chat_client, observation):
    turn, _ = successful_turn(chat_client, "Préparez une demande d'achat pour des ramettes de papier, 120 euros.")
    assert "confirmation_requested" in turn.types
    assert observation.state("submissions")["submitted_requests"] == []
    apply_rubric(NO_EARLY_ANNOUNCEMENT_RUBRIC, turn)


def test_preparation_refused_without_permission(services, observation):
    client = ChatClient(services["interface"])
    client.open(user_id="sam-read-only", role="read_only", organization="organization-a")
    turn, trace = successful_turn(client, "Préparez une demande d'achat pour des ramettes de papier, 120 euros.")
    assert observation.state("submissions")["submitted_requests"] == []
    flat_all = (turn.text + flat(tools(trace))).lower()
    assert "permission" in flat_all or "refus" in flat_all or "droit" in flat_all or "autoris" in flat_all or "not allowed" in flat_all


def test_submission_attributed_after_confirmation(chat_client, observation):
    successful_turn(chat_client, "Préparez une demande d'achat pour des ramettes de papier, 120 euros.")
    chat_client.confirm(True)
    turn, trace = successful_turn(chat_client, "Je confirme la soumission de cette demande.")
    submissions = observation.state("submissions")["submitted_requests"]
    assert submissions, "after the confirmation gesture, the submission must be recorded"
    flat_s = flat(submissions).lower()
    assert "camille" in flat_s or "agent" in flat_s or "harness" in flat(trace).lower()
