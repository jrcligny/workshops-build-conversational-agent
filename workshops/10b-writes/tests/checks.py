"""Checks of workshop 10b, shared by the public and the private tests (one function per criterion).

Contract read here: interface event `confirmation_requested` (data: `draft_id`, `summary`),
the application state `observation.state("submissions")` (`drafts`, `submitted_requests`
with `on_behalf_of` and `assigned_to`), and `tools[].result.status` ("denied" on a refused
preparation). Purchase requests are written by the `buyer` role.
"""

from agent_testkit.chat_client import ChatClient
from agent_testkit.expect import expect_event, expect_no_event, mentions_all, mentions_any, no_business_write
from agent_testkit.turns import apply_rubric_repeatedly, successful_turn, tool_status, tools


def open_client(services, user: dict) -> ChatClient:
    client = ChatClient(services["interface"])
    client.open(**user)
    return client


def confirmation_before_submission(services, observation, case: dict) -> None:
    def run():
        client = open_client(services, case["buyer"])
        turn, trace = successful_turn(client, case["request"])
        requested = expect_event(turn, "confirmation_requested", message="a confirmation is requested")
        assert requested[0].get("draft_id"), "confirmation_requested carries the draft_id of the prepared draft"
        state = observation.state("submissions")
        assert [d["id"] for d in state["drafts"]][-1:] == [requested[0]["draft_id"]], "a draft is prepared in the application"
        assert state["submitted_requests"] == [], "nothing is submitted before the confirmation gesture"
        return turn, trace

    apply_rubric_repeatedly(case["rubric"], run)


def preparation_refused_without_permission(services, observation, case: dict) -> None:
    client = open_client(services, case["user"])
    turn, trace = successful_turn(client, case["request"])
    no_business_write(observation)
    assert "denied" in [tool_status(c) for c in tools(trace)] or not tools(trace), (
        "the refusal comes from the permission check (result.status denied) or the write tool is not offered"
    )
    expect_no_event(turn, "confirmation_requested", "no confirmation is requested without the permission")
    mentions_any(turn, case["lack_of_right_words"], "the user is told they lack the right")


def text_confirmation_is_not_a_gesture(services, observation, case: dict, typed: str) -> None:
    client = open_client(services, case["buyer"])
    turn, _ = successful_turn(client, case["request"])
    expect_event(turn, "confirmation_requested", message="the request is prepared and a confirmation is requested")
    assert observation.state("submissions")["drafts"], "a draft exists in the application"
    successful_turn(client, typed)
    assert observation.state("submissions")["submitted_requests"] == [], (
        "a confirmation typed in the conversation is not the interface gesture"
    )


def submission_attributed_after_confirmation(services, observation, case: dict) -> None:
    client = open_client(services, case["buyer"])
    successful_turn(client, case["request"])
    client.confirm(True)
    turn, _ = successful_turn(client, case["confirmation"])
    submissions = observation.state("submissions")["submitted_requests"]
    assert len(submissions) == 1, "exactly one request is submitted after the confirmation gesture"
    assert submissions[0]["on_behalf_of"] == case["buyer"]["user_id"] and submissions[0]["assigned_to"] == "agent", (
        "the submission is attributed: done by the agent on behalf of the user"
    )
    assert submissions[0]["amount"] == case["amount"]
    mentions_all(turn, submissions[0]["id"], "the answer gives the reference of the submitted request", strict=True)
