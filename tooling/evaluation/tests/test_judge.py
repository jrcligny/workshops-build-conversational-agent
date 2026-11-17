"""Judge rubric: structural layer and meaning layer (k-out-of-n repetition: testkit/tests/test_turns.py)."""

import json

import httpx
import pytest

from workshop_config import settings
from evaluation.judge import JUDGE_INSTRUCTIONS, judge, looks_french, model_meaning_judge

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


def test_french_refusal_passes_without_judge_model(no_judge_model):
    verdict = judge(RUBRIC, {"response": FRENCH_REFUSAL})
    assert verdict["passed"], verdict["rationale"]
    assert verdict["meaning"] == "not assessed"


def test_english_answer_fails_even_with_right_meaning(no_judge_model):
    verdict = judge(RUBRIC, {"response": "I do not have access to the application data, I cannot confirm it."})
    assert verdict["passed"] is False
    assert "not in French" in verdict["rationale"]


def test_forbidden_pattern_fails(no_judge_model):
    verdict = judge(RUBRIC, {"response": "La commande CMD-1042 est livrée, je ne peux pas dire mieux."})
    assert verdict["passed"] is False


def test_negative_meaning_verdict_fails_the_rubric(no_judge_model):
    verdict = judge(RUBRIC, {"response": FRENCH_REFUSAL}, meaning_judge=lambda r, d: {"passed": False, "rationale": "evasive"})
    assert verdict["passed"] is False
    assert verdict["meaning"] == "failed"


def test_semantic_mode_requires_a_judge_model(monkeypatch, no_judge_model):
    monkeypatch.setattr(settings, "judge_mode", "semantic")
    verdict = judge(RUBRIC, {"response": FRENCH_REFUSAL})
    assert verdict["passed"] is False
    assert "no judge model" in verdict["rationale"]


def test_model_meaning_judge_reads_an_openai_compatible_answer(monkeypatch):
    monkeypatch.setattr(settings, "judge_base_url", "http://judge.invalid/v1")
    monkeypatch.setattr(settings, "azure_openai_judge_deployment", "judge")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        content = '{"passed": false, "rationale": "asserts the delivery"}'
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        verdict = model_meaning_judge(RUBRIC, {"response": FRENCH_REFUSAL}, client=client)
    assert verdict == {"passed": False, "rationale": "asserts the delivery"}
    assert seen["body"]["messages"][0]["content"] == JUDGE_INSTRUCTIONS
    assert RUBRIC["criterion"] in seen["body"]["messages"][1]["content"]


def test_language_rule_stated():
    assert "French" in JUDGE_INSTRUCTIONS
    assert looks_french("Elle a été livrée le 12 mars.")
    assert not looks_french("It was delivered on March 12.")
