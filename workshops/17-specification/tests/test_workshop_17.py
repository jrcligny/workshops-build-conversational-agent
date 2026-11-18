"""End-to-end tests of workshop 17. They must fail on the empty shell.

Contract read here (folder `my-agent/local-mode/`):
- `specifications/*.md`: the short specification of one harness control, with one heading per
  part: behaviour (`Comportement`), edge cases (`Cas limites`), undesirable results
  (`Résultats indésirables`), verification (`Vérification`), out of scope (`Hors périmètre`);
- `controls/test_*.py`: the checks of the control, run here with pytest. They pass with the
  control on, and at least one of them fails when the environment variable
  `MY_AGENT_DISABLE_CONTROL=1` disables the control: that check feeds the harness a deliberately
  wrong model output (for example through the proxy scripts) and expects the control to stop it;
- the official routes of workshop 15 are unchanged and the reserved part is never referenced.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

import pytest

from workshop_config import REPO_ROOT, repo_path, settings
from agent_testkit.cases import load_checks

pytestmark = pytest.mark.workshop

PARTS = {
    "behaviour": r"comportement",
    "edge cases": r"cas limites?",
    "undesirable results": r"r[ée]sultats? ind[ée]sirables?",
    "verification": r"v[ée]rification",
    "out of scope": r"hors[- ]p[ée]rim[èe]tre",
}

routes = load_checks(str(REPO_ROOT / "workshops" / "15-evaluation" / "tests" / "routes.py"), "routes.py")


def _local_mode():
    return repo_path(settings.my_agent_dir) / "local-mode"


def _run_controls(disabled: bool) -> subprocess.CompletedProcess:
    folder = _local_mode() / "controls"
    env = {**os.environ, "MY_AGENT_DISABLE_CONTROL": "1" if disabled else "0"}
    return subprocess.run(
        [sys.executable, "-m", "pytest", str(folder), "-q", "-p", "no:cacheprovider", "--rootdir", str(folder), "-o", "addopts="],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )


def test_specification_has_every_part():
    specs = sorted((_local_mode() / "specifications").glob("*.md"))
    assert specs, "a specification is written in my-agent/local-mode/specifications/"
    # Lines inside fenced code blocks (``` or ~~~) are never headings, even when they start with #.
    text = re.sub(r"^(```|~~~).*?^\1[^\n]*$", "", specs[0].read_text(encoding="utf-8"), flags=re.MULTILINE | re.DOTALL)
    headings = " ".join(line.lower() for line in text.splitlines() if re.match(r"\s{0,3}#{1,6}\s", line))
    missing = [name for name, pattern in PARTS.items() if not re.search(pattern, headings)]
    assert not missing, (
        f"{specs[0].name}: Markdown headings (# ...) missing for the parts {missing}; expected one heading per part: "
        "Comportement, Cas limites, Résultats indésirables, Vérification, Hors périmètre"
    )
    for name, pattern in PARTS.items():
        section = re.split(r"^\s{0,3}#{1,6}\s.*" + pattern + r".*$", text, flags=re.IGNORECASE | re.MULTILINE)
        body = re.split(r"^\s{0,3}#{1,6}\s", section[-1], flags=re.MULTILINE)[0] if len(section) > 1 else ""
        assert len(body.strip()) >= 40, (
            f"{specs[0].name}: the part '{name}' holds at least 40 characters of text under its heading"
        )


def test_checks_pass_with_the_control_and_catch_a_wrong_output():
    tests = list((_local_mode() / "controls").glob("test_*.py"))
    assert tests, "the checks of the control are in my-agent/local-mode/controls/test_*.py"
    on = _run_controls(disabled=False)
    assert on.returncode == 0, f"the checks pass with the control on:\n{on.stdout[-2000:]}"
    off = _run_controls(disabled=True)
    assert off.returncode == 1 and re.search(r"\d+ failed", off.stdout), (
        "with MY_AGENT_DISABLE_CONTROL=1, at least one check (the deliberately wrong output) fails:\n" + off.stdout[-2000:]
    )
    assert routes.routes_digest() == routes.expected_digest(), "the evaluation routes were modified; they must stay intact"
    for p in _local_mode().rglob("*"):
        if p.is_file():
            content = p.read_text(encoding="utf-8", errors="ignore").lower().replace("\\", "/")
            assert "15-evaluation/routes/reserved" not in content, f"{p.name} references the reserved routes"
