"""Judge: during design, a structural rubric or a replayed verdict; later, through the Azure proxy."""

from __future__ import annotations

import re
from typing import Any

# The agent built in the workshops converses in French: every rubric judges a French answer.
AGENT_LANGUAGE = "fr"
JUDGE_INSTRUCTIONS = (
    "The agent converses in French. Judge the French answer below against the rubric "
    "criterion. An answer that is not in French fails, whatever its content."
)

_FRENCH_WORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "et", "est", "pas", "je", "vous",
    "ne", "que", "qui", "pour", "sur", "dans", "au", "aux", "avec", "sont", "cette", "ce",
    "il", "elle", "nous", "mais", "ou", "votre", "aucun", "aucune", "commande", "été",
}
_ENGLISH_WORDS = {
    "the", "a", "an", "and", "is", "are", "not", "i", "you", "that", "which", "for", "on",
    "in", "with", "this", "it", "we", "but", "or", "your", "no", "order", "have", "was",
}


def looks_french(text: str) -> bool:
    """Cheap structural language check used until the real judge model is calibrated."""
    words = re.findall(r"[a-zàâäçéèêëîïôöùûüÿœ']+", text.lower())
    words = [w.split("'")[-1] for w in words]
    fr = sum(w in _FRENCH_WORDS for w in words)
    en = sum(w in _ENGLISH_WORDS for w in words)
    return fr > 0 and fr >= en


def judge(rubric: dict[str, Any], dialogue: dict[str, Any], expected_verdict: str | None = None) -> dict[str, Any]:
    """Applies a written rubric.

    During design (no real judge model): the structural requirements
    (patterns required or forbidden in the response or in the trace) are
    checked by code. Meaning assessment, when the rubric asks for it, is
    flagged "to calibrate" and does not fail once the structural requirements
    are met. The agent converses in French: an answer that does not look French
    fails (see JUDGE_INSTRUCTIONS, also sent to the real judge in phase B).
    A hand-written replay verdict, when given, takes precedence.
    """
    if expected_verdict:
        return {
            "passed": expected_verdict == "passed",
            "rationale": "replayed verdict (design phase)",
            "excerpts": [],
            "mode": "replay",
            "rubric": rubric.get("id"),
            "criterion": rubric.get("criterion"),
        }

    response = dialogue.get("response") or ""
    trace = str(dialogue.get("trace") or "")
    sources = {
        "response": response,
        "trace": trace,
        "all": response + "\n" + trace,
    }
    failures: list[str] = []
    excerpts: list[str] = []
    if rubric.get("language", AGENT_LANGUAGE) == "fr" and response.strip() and not looks_french(response):
        failures.append("the answer is not in French (the agent converses in French)")
    for requirement in rubric.get("requirements") or []:
        kind = requirement.get("type")
        patterns = [str(p) for p in (requirement.get("patterns") or [])]
        field = requirement.get("field", "response")
        text = sources.get(field, response).lower()
        if kind == "forbidden":
            for pattern in patterns:
                if pattern.lower() in text:
                    failures.append(f"forbidden pattern found ({pattern!r})")
                    excerpts.append(pattern)
        elif kind == "required_any":
            if patterns and not any(pattern.lower() in text for pattern in patterns):
                failures.append("none of the required patterns appears: " + ", ".join(patterns))
        elif kind == "required_all":
            missing = [p for p in patterns if p.lower() not in text]
            if missing:
                failures.append("required patterns missing: " + ", ".join(missing))

    if not response.strip() and (rubric.get("requirements") or rubric.get("judge_meaning")):
        return {
            "passed": False,
            "rationale": "no assistant response to judge",
            "excerpts": [],
            "mode": "simulated",
            "rubric": rubric.get("id"),
            "criterion": rubric.get("criterion"),
        }
    if failures:
        return {
            "passed": False,
            "rationale": "; ".join(failures),
            "excerpts": excerpts,
            "mode": "simulated",
            "rubric": rubric.get("id"),
            "criterion": rubric.get("criterion"),
        }
    rationale = "structural requirements of the rubric met"
    if rubric.get("judge_meaning"):
        rationale += "; meaning assessment to calibrate in phase B (real judge)"
    return {
        "passed": True,
        "rationale": rationale,
        "excerpts": [response[:200]] if response else [],
        "mode": "simulated",
        "rubric": rubric.get("id"),
        "criterion": rubric.get("criterion"),
        "to_calibrate": bool(rubric.get("judge_meaning")),
    }
