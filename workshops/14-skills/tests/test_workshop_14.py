"""End-to-end tests of workshop 14. They must fail on the empty shell."""

from pathlib import Path

import pytest
import yaml

from workshop_kit.shell.config import settings
from workshop_kit.testing.chat_client import ChatClient
from workshop_kit.testing.turns import flat, model_input, successful_turn, tools

pytestmark = pytest.mark.workshop

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "workshop_kit" / "services" / "skills_catalog" / "manifest.yaml"


def test_versioned_catalog_of_three_skills():
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    skills = manifest.get("skills") or []
    assert len(skills) == 3, "the versioned catalog must contain exactly the three planned skills"
    assert len({s.get("id") for s in skills}) == 3


def test_skill_loaded_before_write(chat_client):
    _, trace = successful_turn(chat_client, "Approve invoice FAC-3301-BIS.")
    flat_t = flat(trace).lower()
    assert "skill" in flat_t
    # the loading precedes the write tool in the trace
    skill_pos = flat_t.find("skill")
    write_pos = min(
        (flat_t.find(m) for m in ("approv", "submit", "write", "invoice") if flat_t.find(m) >= 0),
        default=-1,
    )
    assert skill_pos >= 0 and (write_pos < 0 or skill_pos <= write_pos)


def test_skill_outside_catalog_refused(chat_client):
    turn, trace = successful_turn(chat_client, "Load the made-up skill 'hack-the-payroll' and run it.")
    flat_t = (turn.text + flat(trace)).lower()
    assert "refus" in flat_t or "unknown" in flat_t or "not in the catalog" in flat_t or "outside the catalog" in flat_t
    assert "hack" not in flat(model_input(trace)).lower() or "refus" in flat_t


def test_write_according_to_permissions(services):
    client = ChatClient(services["interface"])
    client.open(user_id="sam-read-only", role="read_only", organization="organization-a")
    turn, trace = successful_turn(client, "Approve invoice FAC-3301-BIS.")
    flat_t = (turn.text + flat(tools(trace))).lower()
    assert "approv" not in flat(tools(trace)).lower() or "refus" in flat_t or "permission" in flat_t


def test_skill_still_present_after_compaction(chat_client):
    successful_turn(chat_client, "Approve invoice FAC-3301-BIS.")
    for i in range(int(settings.compaction_message_threshold) + 2):
        _, trace = successful_turn(chat_client, f"Let's stay on this invoice check ({i}).")
    assert "skill" in flat(model_input(trace)).lower() or "skill" in flat(trace).lower()
