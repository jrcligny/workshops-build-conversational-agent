"""End-to-end tests of workshop 19. They must fail on the empty shell."""

from __future__ import annotations

from pathlib import Path

import pytest

from workshop_tests.evaluation.routes import expected_digest, routes_digest

pytestmark = pytest.mark.workshop

REPO_ROOT = Path(__file__).resolve().parents[3]
LOCAL_MODE = REPO_ROOT / "my-agent" / "local-mode"


def _deliverables(folder: Path) -> list[Path]:
    return [p for p in folder.rglob("*") if p.is_file() and p.name != ".gitkeep" and p.stat().st_size > 80]


def test_specification_implementation_and_check_against_wrong_output():
    specs = _deliverables(LOCAL_MODE / "specifications")
    assert specs, "short control specification missing in my-agent/local-mode/specifications/"
    checks = _deliverables(LOCAL_MODE / "controls")
    assert checks, "control implementation or checks missing in my-agent/local-mode/controls/"
    texts = "\n".join(p.read_text(encoding="utf-8", errors="ignore").lower() for p in checks)
    assert any(
        pattern in texts
        for pattern in ("wrong output", "deliberately wrong", "wrong_output", "false_output", "fake output", "sortie fausse", "volontairement fausse")
    ), "at least one check must feed the harness a deliberately wrong model output"

    assert routes_digest() == expected_digest(), "the evaluation routes were modified; they must stay intact"

    for p in LOCAL_MODE.rglob("*"):
        if p.is_file():
            content = p.read_text(encoding="utf-8", errors="ignore").lower().replace("\\", "/")
            assert "17-evaluation/routes/reserved" not in content
