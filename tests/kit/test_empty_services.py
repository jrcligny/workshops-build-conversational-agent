"""Empty bases of the shell: locations and contracts exist, contents are empty."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import yaml

from workshop_kit.evaluation.routes import expected_digest, routes_digest
from workshop_kit.services.attachments.registry import list_attachments
from workshop_kit.services.sandbox.interface import is_egress_allowed, is_policy_enforced, policy

pytestmark = pytest.mark.shell

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICES = REPO_ROOT / "workshop_kit" / "services"


def test_sandbox_interface_without_policy():
    pol = policy()
    assert pol["active"] is False
    assert pol["allowlist"] == []
    assert is_policy_enforced() is False
    assert is_egress_allowed("https://example.invalid") is None
    assert (SERVICES / "sandbox" / "policy.yaml").is_file()


def test_skills_catalog_empty():
    manifest = yaml.safe_load((SERVICES / "skills_catalog" / "manifest.yaml").read_text(encoding="utf-8"))
    assert "skills" in manifest
    assert manifest["skills"] == []
    folder = SERVICES / "skills_catalog" / "skills"
    assert folder.is_dir()
    assert [p for p in folder.iterdir() if p.name != ".gitkeep"] == []


def test_attachments_area_empty_and_entry_point(services):
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
