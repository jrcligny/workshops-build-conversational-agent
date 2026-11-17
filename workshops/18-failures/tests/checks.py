"""Checks of workshop 18, shared by the public and the private tests (one function per criterion).

Contract read here:
- business log (`method`, `route`, `code`): `POST /drafts/{id}/submit` attempted once only,
  even when the application answers 504 (outcome unknown);
- model proxy log (`route`, `model`, `code`): the primary model fails (503), the agent calls
  the fallback model (its `model` contains "fallback") once, then ends the turn;
- trace `fallback` (`{from, to, reason}`) when the fallback is used, and `unknown_outcome`
  (`{draft_id}`) when a submission's outcome is unknown;
- trace `versions`: an object with non-empty `instructions`, `tools`, `skills` and `index` versions.
Purchase requests are written by the `buyer` role (paul-buyer).
"""

import httpx

from workshop_config import settings
from agent_testkit.chat_client import ChatClient
from agent_testkit.expect import expect_event, mentions_any, mentions_none
from agent_testkit.turns import apply_rubric_repeatedly, business_log, model_calls, successful_turn


def submissions(observation) -> list[dict]:
    return [e for e in business_log(observation) if e.get("method") == "POST" and str(e.get("route", "")).endswith("/submit")]


def rebuild_index(services, include_retired: bool) -> None:
    r = httpx.post(
        f"{services['docs_search']}/indexing/rebuild",
        headers={"Authorization": f"Bearer {settings.observation_token}"},
        json={"include_retired": include_retired},
        timeout=30,
    )
    assert r.status_code == 200


def submission_never_replayed(services, observation, case: dict) -> None:
    user = case["user"]

    def run():
        observation.reset("standard")
        client = ChatClient(services["interface"])
        client.open(user_id=user["user_id"], role=user["role"], organization=user["organization"])
        turn, _ = successful_turn(client, case["purchase"])
        draft_id = expect_event(turn, "confirmation_requested", message="a confirmation is requested")[0].get("draft_id")
        assert draft_id, "a draft is prepared and confirmation_requested carries its draft_id"
        observation.arm_failure("unknown_outcome", True)
        client.confirm(True)
        turn, trace = successful_turn(client, case["confirm"])
        attempts = submissions(observation)
        assert len(attempts) == 1 and attempts[0]["code"] == 504, "one submission attempt, answered 504, is never replayed"
        assert (trace.get("unknown_outcome") or {}).get("draft_id") == draft_id, "trace.unknown_outcome names the draft"
        assert observation.state("submissions")["submitted_requests"] == []
        # The user insists, without a new confirmation gesture: the unknown outcome must not be replayed.
        again, _ = successful_turn(client, case["retry"])
        assert len(submissions(observation)) == 1, "asked to retry, the agent does not submit the draft a second time"
        mentions_none(again, case["claims"], "asked to retry, the agent does not claim it submitted again")
        return turn, trace

    apply_rubric_repeatedly(case["rubric"], run)


def single_fallback_then_end(chat_client, services, case: dict) -> None:
    httpx.post(f"{services['proxy']}/_test/failures", json={"type": "primary_model", "active": True}, timeout=10)
    turn, trace = successful_turn(chat_client, case["question"])
    calls = model_calls(services)
    failed = [c for c in calls if c.get("code") == 503]
    fallback = [c for c in calls if "fallback" in str(c.get("model", "")).lower()]
    assert failed, "the primary model is called first and fails"
    assert fallback and all(c.get("code") == 200 for c in fallback), "the fallback model is then called"
    assert len(failed) == 1, "the primary model is not retried in a loop once it failed"
    assert (trace.get("fallback") or {}).get("to"), "trace.fallback records the switch"
    mentions_any(turn, case["answer_status"], "the turn still answers")
    apply_rubric_repeatedly(case["rubric"], lambda: (turn, trace), k=1, n=1)


def versions_in_the_trace(chat_client, services, case: dict) -> None:
    _, trace = successful_turn(chat_client, case["question"])
    versions = trace.get("versions") or {}
    for component in ("instructions", "tools", "skills", "index"):
        assert str(versions.get(component) or "").strip(), f"trace.versions.{component} names the version in use"
    _, again = successful_turn(chat_client, case["follow_up"])
    assert again.get("versions") == versions, "same configuration, same versions from one turn to the next"
    try:
        rebuild_index(services, include_retired=True)  # the retired procedure 1.0 enters the index
        _, rebuilt = successful_turn(chat_client, case["after_rebuild"])
        assert (rebuilt.get("versions") or {}).get("index") != versions["index"], (
            "versions.index is read from the index in use: it changes when the index is rebuilt"
        )
        assert {k: v for k, v in rebuilt["versions"].items() if k != "index"} == {k: v for k, v in versions.items() if k != "index"}
    finally:
        rebuild_index(services, include_retired=False)
