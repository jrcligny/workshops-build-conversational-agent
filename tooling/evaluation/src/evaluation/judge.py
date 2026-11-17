"""Judge of the workshop rubrics, in two layers.

1. Structural layer (always): patterns required or forbidden in the answer or
   the trace, and the French-answer rule. Checked by code.
2. Meaning layer (when the rubric sets `judge_meaning`): a judge model reads the
   criterion and the French answer and returns a verdict. It runs whenever a
   judge model is configured (`JUDGE_BASE_URL` and `AZURE_OPENAI_JUDGE_DEPLOYMENT`,
   OpenAI-compatible chat completions); a negative verdict fails the rubric.
   `JUDGE_MODE=semantic` makes the meaning layer mandatory, `structural` disables it,
   `auto` (default) uses it when it is configured.

Rubrics are applied k times out of n on fresh conversations by
`testkit.turns.apply_rubric_repeatedly` (`JUDGE_K`, `JUDGE_N`).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

import httpx

from workshop_config import settings

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


MeaningJudge = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]

_VERDICT_PROMPT = (
    "Criterion: {criterion}\n\n"
    "Answer of the agent (French):\n<<<\n{response}\n>>>\n\n"
    "Turn trace excerpt (may be empty):\n<<<\n{trace}\n>>>\n\n"
    'Reply with a single JSON object: {{"passed": true|false, "rationale": "<one sentence>"}}.'
)


def judge_mode() -> str:
    return (settings.judge_mode or "auto").lower()


def meaning_judge_configured() -> bool:
    return bool(settings.judge_base_url and settings.azure_openai_judge_deployment)


def model_meaning_judge(rubric: dict[str, Any], dialogue: dict[str, Any], client: httpx.Client | None = None) -> dict[str, Any]:
    """Asks the judge model (OpenAI-compatible endpoint) whether the answer meets the criterion."""
    prompt = _VERDICT_PROMPT.format(
        criterion=rubric.get("criterion") or "",
        response=dialogue.get("response") or "",
        trace=str(dialogue.get("trace") or "")[:4000],
    )
    body = {
        "model": settings.azure_openai_judge_deployment,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": JUDGE_INSTRUCTIONS},
            {"role": "user", "content": prompt},
        ],
    }
    headers = {"Authorization": f"Bearer {settings.judge_api_key}"} if settings.judge_api_key else {}
    url = settings.judge_base_url.rstrip("/") + "/chat/completions"
    own = client is None
    client = client or httpx.Client(timeout=60)
    try:
        response = client.post(url, json=body, headers=headers)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"] or ""
    finally:
        if own:
            client.close()
    match = re.search(r"\{.*\}", content, re.DOTALL)
    try:
        verdict = json.loads(match.group(0) if match else content)
    except json.JSONDecodeError:
        return {"passed": False, "rationale": f"unreadable judge verdict: {content[:200]!r}"}
    return {"passed": bool(verdict.get("passed")), "rationale": str(verdict.get("rationale") or "")}


def _verdict(rubric: dict[str, Any], passed: bool, rationale: str, **extra: Any) -> dict[str, Any]:
    return {
        "passed": passed,
        "rationale": rationale,
        "rubric": rubric.get("id"),
        "criterion": rubric.get("criterion"),
        **extra,
    }


def judge(
    rubric: dict[str, Any],
    dialogue: dict[str, Any],
    expected_verdict: str | None = None,
    meaning_judge: MeaningJudge | None = None,
) -> dict[str, Any]:
    """Applies a written rubric to one dialogue (one answer and its trace).

    The structural layer runs first; the meaning layer (see the module docstring)
    runs only when the structural layer passes. `meaning` in the verdict is
    "passed", "failed" or "not assessed". A hand-written replay verdict, when
    given, takes precedence. `meaning_judge` overrides the configured judge model.
    """
    if expected_verdict:
        return _verdict(rubric, expected_verdict == "passed", "replayed verdict", excerpts=[], mode="replay")

    response = dialogue.get("response") or ""
    trace = str(dialogue.get("trace") or "")
    sources = {
        "response": response,
        "trace": trace,
        "all": response + "\n" + trace,
    }
    if not response.strip() and (rubric.get("requirements") or rubric.get("judge_meaning")):
        return _verdict(rubric, False, "no assistant response to judge", excerpts=[], mode="structural")

    failures: list[str] = []
    excerpts: list[str] = []
    if rubric.get("language", AGENT_LANGUAGE) == "fr" and not looks_french(response):
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
    if failures:
        return _verdict(rubric, False, "; ".join(failures), excerpts=excerpts, mode="structural", meaning="not assessed")

    rationale = "structural requirements of the rubric met"
    if not rubric.get("judge_meaning"):
        return _verdict(rubric, True, rationale, excerpts=[response[:200]], mode="structural", meaning="not assessed")

    mode = judge_mode()
    if meaning_judge is None and mode != "structural" and meaning_judge_configured():
        meaning_judge = model_meaning_judge
    if meaning_judge is None:
        if mode == "semantic":
            return _verdict(
                rubric, False,
                "JUDGE_MODE=semantic but no judge model is configured (JUDGE_BASE_URL, AZURE_OPENAI_JUDGE_DEPLOYMENT)",
                excerpts=[], mode="structural", meaning="not assessed",
            )
        return _verdict(
            rubric, True, rationale + "; meaning not assessed (no judge model configured)",
            excerpts=[response[:200]], mode="structural", meaning="not assessed",
        )
    meaning = meaning_judge(rubric, {"response": response, "trace": trace})
    passed = bool(meaning.get("passed"))
    return _verdict(
        rubric, passed, f"{rationale}; meaning: {meaning.get('rationale', '')}",
        excerpts=[response[:200]], mode="semantic", meaning="passed" if passed else "failed",
    )
