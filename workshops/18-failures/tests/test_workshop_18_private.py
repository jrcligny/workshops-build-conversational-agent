"""Private tests of workshop 18 (not given to students): same criteria, other inputs.

Another buyer and organization (omar-buyer-b), another purchase, another order for the fallback
(CMD-2010, shipped) and other questions around the index rebuild.
"""

import httpx
import pytest

from workshop_config import settings
from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.turns import apply_rubric_repeatedly, business_log, events_of, model_calls, successful_turn

pytestmark = pytest.mark.workshop

UNKNOWN_OUTCOME_RUBRIC = {
    "id": "18-unknown-outcome-private",
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
    "id": "18-fallback-then-end-private",
    "criterion": "The agent answers with the status of CMD-2010 and says the answer comes from a fallback model.",
    "judge_meaning": True,
    "requirements": [{"type": "required_any", "patterns": ["secours", "repli", "modèle de remplacement"]}],
}


def _submissions(observation) -> list[dict]:
    return [e for e in business_log(observation) if e.get("method") == "POST" and str(e.get("route", "")).endswith("/submit")]


def test_submission_never_replayed(services, observation):
    def run():
        observation.reset("standard")
        client = ChatClient(services["interface"])
        client.open(user_id="omar-buyer-b", role="buyer", organization="organization-b")
        turn, _ = successful_turn(client, "J'ai besoin d'une demande d'achat : 12 cartouches d'encre, 85,50 euros.")
        draft_id = (events_of(turn, "confirmation_requested") or [{}])[0].get("draft_id")
        assert draft_id, "a draft is prepared and confirmation_requested carries its draft_id"
        observation.arm_failure("unknown_outcome", True)
        client.confirm(True)
        turn, trace = successful_turn(client, "C'est bon pour moi, envoyez-la.")
        attempts = _submissions(observation)
        assert len(attempts) == 1 and attempts[0]["code"] == 504, "one submission attempt, answered 504, is never replayed"
        assert (trace.get("unknown_outcome") or {}).get("draft_id") == draft_id, "trace.unknown_outcome names the draft"
        assert observation.state("submissions")["submitted_requests"] == []
        again, _ = successful_turn(client, "Le système a dû planter, relancez l'envoi du même brouillon.")
        assert len(_submissions(observation)) == 1, "asked to retry, the agent does not submit the draft a second time"
        assert not any(w in again.text.lower() for w in ("a bien été soumise", "j'ai soumis")), "nor claims it did"
        return turn, trace

    apply_rubric_repeatedly(UNKNOWN_OUTCOME_RUBRIC, run)


def test_single_fallback_then_end(chat_client, services):
    httpx.post(f"{services['proxy']}/_test/failures", json={"type": "primary_model", "active": True}, timeout=10)
    turn, trace = successful_turn(chat_client, "Où en est la livraison de CMD-2010 pour Léa Martin à Lille ?")
    calls = model_calls(services)
    failed = [c for c in calls if c.get("code") == 503]
    fallback = [c for c in calls if "fallback" in str(c.get("model", "")).lower()]
    assert failed, "the primary model is called first and fails"
    assert fallback and all(c.get("code") == 200 for c in fallback), "the fallback model is then called"
    assert len(failed) == 1, "the primary model is not retried in a loop once it failed"
    assert (trace.get("fallback") or {}).get("to"), "trace.fallback records the switch"
    assert "expédiée" in turn.text.lower(), "the turn still answers"
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
    _, trace = successful_turn(chat_client, "Combien de commandes a passé Martin Durand ?")
    versions = trace.get("versions") or {}
    for component in ("instructions", "tools", "skills", "index"):
        assert str(versions.get(component) or "").strip(), f"trace.versions.{component} names the version in use"
    _, again = successful_turn(chat_client, "Et laquelle est la plus récente ?")
    assert again.get("versions") == versions, "same configuration, same versions from one turn to the next"
    try:
        _rebuild_index(services, include_retired=True)
        _, rebuilt = successful_turn(chat_client, "Quel est le délai de traitement d'une réclamation ?")
        assert (rebuilt.get("versions") or {}).get("index") != versions["index"], (
            "versions.index is read from the index in use: it changes when the index is rebuilt"
        )
        assert {k: v for k, v in rebuilt["versions"].items() if k != "index"} == {k: v for k, v in versions.items() if k != "index"}
    finally:
        _rebuild_index(services, include_retired=False)
