"""End-to-end tests of workshop 17. They must fail on the empty shell."""

from pathlib import Path

import pytest

from workshop_kit.testing.turns import flat, successful_turn

pytestmark = pytest.mark.workshop

# Edge cases listed in the retained choice of chapter 17.
EDGE_CASES = [
    "approximate-reference",
    "namesakes",
    "truncated-result-total",
    "out-of-scope-request",
    "write-after-attachment",
    "question-without-documentary-answer",
    "user-without-write-permission",
    "duplicate-invoice",
]

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_masked_traces(chat_client, traces):
    successful_turn(chat_client, "What is the status of order CMD-1042?")
    flat_t = flat(traces.last()).lower()
    assert "authorization" not in flat_t and "bearer " not in flat_t
    assert "azure_openai_api_key" not in flat_t


def test_route_set_and_report():
    root = REPO_ROOT / "my-agent"
    report = root / "route-report.md"
    if not report.exists():
        candidates = (
            list(root.glob("*route*report*"))
            + list(root.glob("*route*.json"))
            + list(root.glob("*route*.md"))
        )
        assert candidates, "route report missing (one report per route)"
        report = candidates[0]
    text = report.read_text(encoding="utf-8").lower()
    for case in EDGE_CASES:
        variants = {case, case.replace("-", " "), case.replace("-", "_")}
        assert any(v in text for v in variants), (
            f"the route set must cover the edge case {case!r} and the report must account for it"
        )
    assert "repeat" in text or "k/" in text or "runs" in text
    assert "fact" in text or "deterministic" in text
