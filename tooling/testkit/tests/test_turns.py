"""k-out-of-n repetition of a judge rubric (`testkit.turns.apply_rubric_repeatedly`)."""

import pytest

from workshop_config import settings
from testkit.chat_client import Turn
from testkit.turns import apply_rubric_repeatedly

pytestmark = pytest.mark.shell

RUBRIC = {
    "id": "kit-refusal",
    "criterion": "The agent, answering in French, declines to state the status without a source.",
    "judge_meaning": True,
    "requirements": [
        {"type": "forbidden", "patterns": ["est livrée"]},
        {"type": "required_any", "patterns": ["je ne peux pas", "pas accès"]},
    ],
}
FRENCH_REFUSAL = "Je n'ai pas accès aux données de l'application, je ne peux pas le confirmer."


@pytest.fixture
def no_judge_model(monkeypatch):
    monkeypatch.setattr(settings, "judge_mode", "auto")
    monkeypatch.setattr(settings, "judge_base_url", "")


def test_k_out_of_n(no_judge_model):
    answers = iter(["The order is delivered.", FRENCH_REFUSAL, FRENCH_REFUSAL, FRENCH_REFUSAL])
    calls = []

    def run():
        calls.append(1)
        return Turn(text=next(answers), ok=True), {}

    verdicts = apply_rubric_repeatedly(RUBRIC, run, k=3, n=5)
    assert len(calls) == 4 and sum(v["passed"] for v in verdicts) == 3


def test_k_out_of_n_fails_when_too_few_runs_pass(no_judge_model):
    answers = iter(["Elle est livrée.", FRENCH_REFUSAL, "Elle est livrée.", FRENCH_REFUSAL, FRENCH_REFUSAL])
    with pytest.raises(AssertionError, match=r"1 run\(s\) passed, 3 out of 4"):
        apply_rubric_repeatedly(RUBRIC, lambda: (Turn(text=next(answers), ok=True), {}), k=3, n=4)
