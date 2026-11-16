"""Empty bases of the shell: locations and contracts exist, contents are empty."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from workshop_tests.evaluation.routes import expected_digest, routes_digest
from workshop_kit.services.attachments.registry import list_attachments
from workshop_kit.services.sandbox.interface import is_egress_allowed, is_policy_enforced, policy, policy_file
from workshop_kit.services.skills_catalog.catalog import catalog_dir, load_manifest, skill_folders
from workshop_kit.services.attachments.registry import folder as attachments_folder

pytestmark = pytest.mark.shell

REPO_ROOT = Path(__file__).resolve().parents[3]
MY_AGENT = REPO_ROOT / "my-agent"


def test_sandbox_interface_without_policy():
    pol = policy()
    assert pol["active"] is False
    assert pol["allowlist"] == []
    assert is_policy_enforced() is False
    assert is_egress_allowed("https://example.invalid") is None
    assert policy_file() == MY_AGENT / "sandbox" / "policy.yaml"
    assert policy_file().is_file()


def test_skills_catalog_empty():
    assert catalog_dir() == MY_AGENT / "skills"
    manifest = load_manifest()
    assert "skills" in manifest
    assert manifest["skills"] == []
    assert skill_folders() == []


def test_attachments_area_empty_and_entry_point(services):
    assert attachments_folder() == MY_AGENT / "attachments"
    assert list_attachments() == []
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
    assert routes_digest() == expected_digest()


def test_student_files_only_in_my_agent():
    """Student assets stay in my-agent; the kit UI owns only its infrastructure resources."""
    kit = REPO_ROOT / "workshop_kit"
    data_files = []
    for folder, directories, filenames in kit.walk():
        directories[:] = [d for d in directories if d not in {"__pycache__", ".venv", ".pytest_cache"}]
        if folder == kit:
            directories.remove("chat-ui")
            directories.remove("bootstrap")
        data_files.extend(
            (folder / name).relative_to(REPO_ROOT).as_posix()
            for name in filenames if Path(name).suffix != ".py"
            and not (name in {"pyproject.toml", "uv.lock", ".python-version"} and folder in {
                kit / "apps" / "business_api", kit / "apps" / "docs_search",
                kit / "llm_proxy", kit / "shell",
            })
        )
    assert data_files == []
    ui = kit / "chat-ui"
    assert (ui / "pyproject.toml").is_file()
    assert (ui / "uv.lock").is_file()
    assert (ui / "workshop_chat_ui" / "welcome.md").is_file()
    bootstrap = kit / "bootstrap"
    assert (bootstrap / "pyproject.toml").is_file()
    assert (bootstrap / "uv.lock").is_file()
