"""Readers of the student's data (sandbox policy, skills catalog, attachments) on the empty bootstrap."""

from __future__ import annotations

from workshop_config import repo_path, settings

from agent_sdk.attachments import folder as attachments_folder
from agent_sdk.attachments import attached_record, list_attachments
from agent_sdk.sandbox import is_egress_allowed, is_policy_enforced, policy, policy_file
from agent_sdk.skills import catalog_dir, load_manifest, skill_folders

MY_AGENT = repo_path(settings.my_agent_dir)


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


def test_attachments_area_empty():
    assert attachments_folder() == MY_AGENT / "attachments"
    assert list_attachments() == []


def test_attachment_record_from_manifest(tmp_path, monkeypatch):
    (tmp_path / "quote.txt").write_text("Devis", encoding="utf-8")
    (tmp_path / "orphan.txt").write_text("Sans enregistrement", encoding="utf-8")
    (tmp_path / "attachments.yaml").write_text("quote.txt:\n  record: orders/CMD-2010\n", encoding="utf-8")
    monkeypatch.setattr(settings, "attachments_dir", str(tmp_path))
    assert attached_record("quote.txt") == "orders/CMD-2010"
    assert attached_record("orphan.txt") is None
    assert {a["id"]: a["record"] for a in list_attachments()} == {"orphan.txt": None, "quote.txt": "orders/CMD-2010"}
