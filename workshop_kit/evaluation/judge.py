"""Judge: during design, a structural rubric or a replayed verdict; later, through the Azure proxy."""

from __future__ import annotations

from typing import Any


def judge(rubric: dict[str, Any], dialogue: dict[str, Any], expected_verdict: str | None = None) -> dict[str, Any]:
    """Applies a written rubric.

    During design (no real judge model): the structural requirements
    (patterns required or forbidden in the response or in the trace) are
    checked by code. Meaning assessment, when the rubric asks for it, is
    flagged "to calibrate" and does not fail once the structural requirements
    are met. A hand-written replay verdict, when given, takes precedence.
    """
    if expected_verdict:
        return {
            "passed": expected_verdict == "passed",
            "rationale": "replayed verdict (design phase)",
            "excerpts": [],
            "mode": "replay",
            "rubric": rubric.get("id"),
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
        }
    if failures:
        return {
            "passed": False,
            "rationale": "; ".join(failures),
            "excerpts": excerpts,
            "mode": "simulated",
            "rubric": rubric.get("id"),
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
        "to_calibrate": bool(rubric.get("judge_meaning")),
    }
