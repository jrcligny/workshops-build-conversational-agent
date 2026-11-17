"""Empty bases of my-agent/: locations and contracts exist, contents are empty."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from testkit.cases import load_checks

pytestmark = pytest.mark.shell

REPO_ROOT = Path(__file__).resolve().parents[3]
MY_AGENT = REPO_ROOT / "my-agent"
routes = load_checks(str(REPO_ROOT / "workshops" / "17-evaluation" / "tests" / "routes.py"), "routes.py")


def test_attachments_entry_point_empty(services):
    r = httpx.get(f"{services['interface']}/attachments", timeout=5)
    assert r.status_code == 200
    assert r.json()["attachments"] == []


def test_local_mode_coding_agent_landing_empty():
    root = REPO_ROOT / "my-agent" / "local-mode"
    assert (root / "README.md").is_file()
    assert (root / "specifications").is_dir()
    assert (root / "controls").is_dir()
    deliverables = [
        p
        for sub in (root / "specifications", root / "controls")
        for p in sub.iterdir()
        if p.name != ".gitkeep"
    ]
    assert deliverables == []


def test_evaluation_routes_checksum():
    assert routes.routes_digest() == routes.expected_digest()


def test_student_files_only_in_my_agent():
    """Student assets stay in my-agent; the SDK and the gateways hold only code and project files."""
    project_files = {"pyproject.toml", "uv.lock", ".python-version", "README.md"}
    data_files = []
    for top in (REPO_ROOT / "agent_sdk", REPO_ROOT / "gateway"):
        for folder, directories, filenames in top.walk():
            directories[:] = [d for d in directories if d not in {"__pycache__", ".venv", ".pytest_cache"}]
            data_files.extend(
                (folder / name).relative_to(REPO_ROOT).as_posix()
                for name in filenames
                if Path(name).suffix != ".py" and name not in project_files
            )
    assert data_files == []
    ui = REPO_ROOT / "clients" / "chat_ui"
    assert (ui / "pyproject.toml").is_file()
    assert (ui / "uv.lock").is_file()
    assert (ui / "src" / "chat_ui" / "welcome.md").is_file()
    cli = REPO_ROOT / "tooling" / "cli"
    assert (cli / "pyproject.toml").is_file()
    assert (cli / "uv.lock").is_file()
