"""End-to-end tests of workshop 18. They must fail on the empty shell."""

import httpx
import pytest

from workshop_tests.testing.turns import apply_rubric, business_log, flat, successful_turn

pytestmark = pytest.mark.workshop

FALLBACK_RUBRIC = {
    "id": "18-fallback-then-end",
    "criterion": "The agent, answering in French, says the primary model failed, that it switched once to the fallback, and ends cleanly.",
    "judge_meaning": True,
    "requirements": [
        {
            "type": "required_any",
            "patterns": ["secours", "repli", "alternatif", "indisponible", "pas pu", "échec", "panne"],
        },
    ],
}


def test_submission_never_replayed(chat_client, observation):
    observation.arm_failure("unknown_outcome", True)
    turn, _ = successful_turn(chat_client, "Soumettez la demande d'achat déjà préparée.")
    assert "vérif" in turn.text.lower() or "contrôl" in turn.text.lower()
    submissions = [e for e in business_log(observation) if "submit" in str(e).lower()]
    assert len(submissions) <= 1


def test_single_fallback_then_end(chat_client, services):
    httpx.post(
        f"{services['proxy']}/_test/failures",
        json={"type": "primary_model", "active": True},
        timeout=10,
    )
    turn, trace = successful_turn(chat_client, "Quel est le statut de la commande CMD-1042 de Martin Durand ?")
    assert "fallback" in flat(trace).lower()
    apply_rubric(FALLBACK_RUBRIC, turn, trace)


def test_versions_in_the_trace(chat_client):
    _, trace = successful_turn(chat_client, "Quel est le statut de la commande CMD-1042 ?")
    flat_t = flat(trace).lower()
    assert "version" in flat_t
    for component in ("instructions", "skill", "tool", "index"):
        assert component in flat_t, f"the trace must carry the version of: {component}"
