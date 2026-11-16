"""End-to-end tests of workshop 10b. They must fail on the empty shell.

Contract read here: interface event `confirmation_requested` (data: `draft_id`, `summary`),
the application state `observation.state("submissions")` (`drafts`, `submitted_requests`
with `on_behalf_of` and `assigned_to`), and `tools[].result.status` ("denied" on a refused
preparation). Purchase requests are written by the `buyer` role (paul-buyer).
"""

import pytest

from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.turns import apply_rubric_repeatedly, events_of, successful_turn, tool_status, tools

pytestmark = pytest.mark.workshop

REQUEST = "Préparez une demande d'achat pour des ramettes de papier, 120 euros."

NO_EARLY_ANNOUNCEMENT_RUBRIC = {
    "id": "10b-no-announcement-before-submission",
    "criterion": (
        "Before the user's confirmation, the agent presents the prepared request and asks for "
        "confirmation; it never says the request was sent or submitted."
    ),
    "judge_meaning": True,
    "requirements": [
        {"type": "required_any", "patterns": ["confirm"]},
        {"type": "forbidden", "patterns": [
            "j'ai soumis", "j'ai envoyé", "a été envoyée", "a été soumise", "est soumise",
            "c'est soumis", "soumission effectuée", "soumission faite", "c'est fait",
        ]},
    ],
}


def _buyer(services) -> ChatClient:
    client = ChatClient(services["interface"])
    client.open(user_id="paul-buyer", role="buyer", organization="organization-a")
    return client


def test_confirmation_before_submission(services, observation):
    def run():
        client = _buyer(services)
        turn, trace = successful_turn(client, REQUEST)
        requested = events_of(turn, "confirmation_requested")
        assert requested and requested[0].get("draft_id"), "confirmation_requested carries the draft_id of the prepared draft"
        state = observation.state("submissions")
        assert [d["id"] for d in state["drafts"]][-1:] == [requested[0]["draft_id"]], "a draft is prepared in the application"
        assert state["submitted_requests"] == [], "nothing is submitted before the confirmation gesture"
        return turn, trace

    apply_rubric_repeatedly(NO_EARLY_ANNOUNCEMENT_RUBRIC, run)


def test_preparation_refused_without_permission(services, observation):
    client = ChatClient(services["interface"])
    client.open(user_id="sam-read-only", role="read_only", organization="organization-a")
    turn, trace = successful_turn(client, REQUEST)
    state = observation.state("submissions")
    assert state["drafts"] == [] and state["submitted_requests"] == [], "nothing is prepared nor submitted"
    assert "denied" in [tool_status(c) for c in tools(trace)] or not tools(trace), (
        "the refusal comes from the permission check (result.status denied) or the write tool is not offered"
    )
    assert "confirmation_requested" not in turn.types
    assert any(w in turn.text.lower() for w in ("droit", "autoris", "permission")), "the user is told they lack the right"


def test_text_confirmation_is_not_a_gesture(services, observation):
    client = _buyer(services)
    turn, _ = successful_turn(client, REQUEST)
    assert events_of(turn, "confirmation_requested"), "the request is prepared and a confirmation is requested"
    assert observation.state("submissions")["drafts"], "a draft exists in the application"
    successful_turn(client, "Oui, je confirme, soumettez-la.")
    assert observation.state("submissions")["submitted_requests"] == [], (
        "a confirmation typed in the conversation is not the interface gesture"
    )


def test_submission_attributed_after_confirmation(services, observation):
    client = _buyer(services)
    successful_turn(client, REQUEST)
    client.confirm(True)
    turn, _ = successful_turn(client, "Je confirme la soumission de cette demande.")
    submissions = observation.state("submissions")["submitted_requests"]
    assert len(submissions) == 1, "exactly one request is submitted after the confirmation gesture"
    assert submissions[0]["on_behalf_of"] == "paul-buyer" and submissions[0]["assigned_to"] == "agent", (
        "the submission is attributed: done by the agent on behalf of the user"
    )
    assert submissions[0]["amount"] == 120
    assert submissions[0]["id"] in turn.text, "the answer gives the reference of the submitted request"
