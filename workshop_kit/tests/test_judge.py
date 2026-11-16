"""Judge rubric (design phase): structural requirements and the French-answer rule."""

import pytest

from workshop_tests.evaluation.judge import JUDGE_INSTRUCTIONS, judge, looks_french

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


def test_french_refusal_passes():
    verdict = judge(RUBRIC, {"response": "Je n'ai pas accès aux données de l'application, je ne peux pas le confirmer."})
    assert verdict["passed"], verdict["rationale"]
    assert verdict["to_calibrate"] is True


def test_english_answer_fails_even_with_right_meaning():
    verdict = judge(RUBRIC, {"response": "I do not have access to the application data, I cannot confirm it."})
    assert verdict["passed"] is False
    assert "not in French" in verdict["rationale"]


def test_forbidden_pattern_fails():
    verdict = judge(RUBRIC, {"response": "La commande CMD-1042 est livrée, je ne peux pas dire mieux."})
    assert verdict["passed"] is False


def test_language_rule_stated():
    assert "French" in JUDGE_INSTRUCTIONS
    assert looks_french("Elle a été livrée le 12 mars.")
    assert not looks_french("It was delivered on March 12.")
