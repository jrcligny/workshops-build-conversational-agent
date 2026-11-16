"""End-to-end tests of workshop 18. They must fail on the empty shell.

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
import pytest

from workshop_kit.shell.config import settings
from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.turns import apply_rubric_repeatedly, business_log, events_of, model_calls, successful_turn

pytestmark = pytest.mark.workshop

UNKNOWN_OUTCOME_RUBRIC = {
    "id": "18-unknown-outcome",
    "criterion": (
        "The agent says it does not know whether the request was submitted, asks the user to check "
        "before trying again, and never claims the request was submitted or failed."
    ),
    "judge_meaning": True,
    "requirements": [
        {"type": "required_any", "patterns": ["vérifi", "contrôl"]},
        {"type": "forbidden", "patterns": ["a bien été soumise", "a été soumise avec succès", "j'ai soumis", "a échoué"]},
    ],
}

FALLBACK_RUBRIC = {
    "id": "18-fallback-then-end",
    "criterion": "The agent answers with the status of CMD-1042 and says the answer comes from a fallback model.",
    "judge_meaning": True,
    "requirements": [{"type": "required_any", "patterns": ["secours", "repli", "modèle de remplacement"]}],
}


def _submissions(observation) -> list[dict]:
    return [e for e in business_log(observation) if e.get("method") == "POST" and str(e.get("route", "")).endswith("/submit")]


def test_submission_never_replayed(services, observation):
    def run():
        observation.reset("standard")
        client = ChatClient(services["interface"])
        client.open(user_id="paul-buyer", role="buyer", organization="organization-a")
        turn, _ = successful_turn(client, "Préparez une demande d'achat pour des ramettes de papier, 120 euros.")
        draft_id = (events_of(turn, "confirmation_requested") or [{}])[0].get("draft_id")
        assert draft_id, "a draft is prepared and confirmation_requested carries its draft_id"
        observation.arm_failure("unknown_outcome", True)
        client.confirm(True)
        turn, trace = successful_turn(client, "Je confirme la soumission de cette demande.")
        attempts = _submissions(observation)
        assert len(attempts) == 1 and attempts[0]["code"] == 504, "one submission attempt, answered 504, is never replayed"
        assert (trace.get("unknown_outcome") or {}).get("draft_id") == draft_id, "trace.unknown_outcome names the draft"
        assert observation.state("submissions")["submitted_requests"] == []
        # The user insists, without a new confirmation gesture: the unknown outcome must not be replayed.
        again, _ = successful_turn(client, "Elle n'est sans doute pas partie : réessayez la soumission.")
        assert len(_submissions(observation)) == 1, "asked to retry, the agent does not submit the draft a second time"
        assert not any(w in again.text.lower() for w in ("a bien été soumise", "j'ai soumis")), "nor claims it did"
        return turn, trace

    apply_rubric_repeatedly(UNKNOWN_OUTCOME_RUBRIC, run)


def test_single_fallback_then_end(chat_client, services):
    httpx.post(f"{services['proxy']}/_test/failures", json={"type": "primary_model", "active": True}, timeout=10)
    turn, trace = successful_turn(chat_client, "Quel est le statut de la commande CMD-1042 de Martin Durand ?")
    calls = model_calls(services)
    failed = [c for c in calls if c.get("code") == 503]
    fallback = [c for c in calls if "fallback" in str(c.get("model", "")).lower()]
    assert failed, "the primary model is called first and fails"
    assert fallback and all(c.get("code") == 200 for c in fallback), "the fallback model is then called"
    assert len(failed) == 1, "the primary model is not retried in a loop once it failed"
    assert (trace.get("fallback") or {}).get("to"), "trace.fallback records the switch"
    assert "livrée" in turn.text.lower(), "the turn still answers"
    apply_rubric_repeatedly(FALLBACK_RUBRIC, lambda: (turn, trace), k=1, n=1)


def _rebuild_index(services, include_retired: bool) -> None:
    r = httpx.post(
        f"{services['docs_search']}/indexing/rebuild",
        headers={"Authorization": f"Bearer {settings.observation_token}"},
        json={"include_retired": include_retired},
        timeout=30,
    )
    assert r.status_code == 200


def test_versions_in_the_trace(chat_client, services):
    _, trace = successful_turn(chat_client, "Quel est le statut de la commande CMD-1042 ?")
    versions = trace.get("versions") or {}
    for component in ("instructions", "tools", "skills", "index"):
        assert str(versions.get(component) or "").strip(), f"trace.versions.{component} names the version in use"
    _, again = successful_turn(chat_client, "Et quel est son montant ?")
    assert again.get("versions") == versions, "same configuration, same versions from one turn to the next"
    try:
        _rebuild_index(services, include_retired=True)  # the retired procedure 1.0 enters the index
        _, rebuilt = successful_turn(chat_client, "Et celui de la commande CMD-1042, à nouveau ?")
        assert (rebuilt.get("versions") or {}).get("index") != versions["index"], (
            "versions.index is read from the index in use: it changes when the index is rebuilt"
        )
        assert {k: v for k, v in rebuilt["versions"].items() if k != "index"} == {k: v for k, v in versions.items() if k != "index"}
    finally:
        _rebuild_index(services, include_retired=False)
