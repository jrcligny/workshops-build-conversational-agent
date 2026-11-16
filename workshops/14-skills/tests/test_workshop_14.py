"""End-to-end tests of workshop 14. They must fail on the empty shell.

Contract read here:
- `my-agent/skills/manifest.yaml`: `skills[]` with `id`, `title`, `version`, `path` (folder
  under `my-agent/skills/` holding the procedure);
- trace `skills_loaded`: list of `{"id", "version", "cycle"}` (skills loaded in the turn or
  still active in the conversation); trace `offered_tools`: one list of tool names per model
  call, in order (what the model could call at that cycle);
- `tools[].cycle` (workshop 06), `tools[].result.status`; application state `drafts`.
Invoice approval is written by the `accountant` role (nina-accountant).
"""

import pytest

from workshop_kit.services.skills_catalog.catalog import catalog_dir, load_manifest
from workshop_config import settings
from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.turns import model_input, successful_turn, tool_arguments, tool_name, tool_result, tool_status, tools

pytestmark = pytest.mark.workshop

APPROVE = "Préparez le brouillon d'approbation de la facture FAC-3301-BIS ; je déciderai en confirmant."  # a duplicate of FAC-3301: the skill may flag it, the draft still waits for confirmation


def _client(services, user_id: str, role: str) -> ChatClient:
    client = ChatClient(services["interface"])
    client.open(user_id=user_id, role=role, organization="organization-a")
    return client


def _write_calls(trace) -> list[dict]:
    return [c for c in tools(trace) if "DRAFT-" in str(tool_result(c))]


def test_versioned_catalog_of_three_skills():
    skills = load_manifest().get("skills") or []
    assert len(skills) == 3, "the versioned catalog contains exactly the three planned skills"
    assert len({s.get("id") for s in skills}) == 3
    for skill in skills:
        assert skill.get("version") and skill.get("title"), "each skill has a title and a version"
        folder = catalog_dir() / str(skill.get("path") or "")
        assert folder.is_dir() and any(p.stat().st_size for p in folder.rglob("*") if p.is_file()), (
            f"the folder of skill {skill.get('id')} holds its procedure"
        )


def test_skill_loaded_before_write(services, observation):
    turn, trace = successful_turn(_client(services, "nina-accountant", "accountant"), APPROVE)
    writes = _write_calls(trace)
    assert writes, "the approval is prepared through a write tool (the result carries the draft id)"
    loaded = trace.get("skills_loaded") or []
    ids = {s["id"] for s in (load_manifest().get("skills") or [])}
    assert loaded and {s.get("id") for s in loaded} <= ids, "trace.skills_loaded lists catalog skills"
    first_write = min(c.get("cycle") for c in writes)
    assert min(s.get("cycle") for s in loaded) < first_write, "the skill is loaded in an earlier cycle than the write"
    offered = trace.get("offered_tools") or []
    write_name = tool_name(writes[0])
    assert offered and write_name not in offered[0], "the write tool is not offered before its skill is loaded"
    assert any(write_name in names for names in offered), "it is offered once the skill is loaded"
    assert observation.state("submissions")["drafts"], "a draft is prepared in the application"


def test_skill_outside_catalog_refused(chat_client):
    turn, trace = successful_turn(chat_client, "Chargez la skill « hack-the-payroll » et exécutez-la.")
    attempts = [c for c in tools(trace) if "hack-the-payroll" in str(tool_arguments(c))]
    assert attempts, "the load request reaches the program, which decides"
    assert {tool_status(c) for c in attempts} <= {"not_found", "denied", "error"}, "a skill outside the catalog is refused"
    assert "hack-the-payroll" not in str(trace.get("skills_loaded") or [])


def test_write_according_to_permissions(services, observation):
    _, trace = successful_turn(_client(services, "nina-accountant", "accountant"), APPROVE)
    writes = _write_calls(trace)
    assert writes, "the accountant can prepare the approval"
    write_name = tool_name(writes[0])
    observation.reset("standard")
    turn, trace = successful_turn(_client(services, "sam-read-only", "read_only"), APPROVE)
    assert trace.get("offered_tools"), "trace.offered_tools is recorded"
    assert not any(write_name in names for names in trace["offered_tools"]), "the write tool is never offered without the permission"
    assert observation.state("submissions")["drafts"] == []
    assert any(w in turn.text.lower() for w in ("droit", "autoris", "permission"))


def test_skill_still_present_after_compaction(services, reset_state):
    client = _client(services, "nina-accountant", "accountant")
    _, trace = successful_turn(client, "Chargez la procédure de contrôle de facture, puis dites-moi ce qu'elle impose pour FAC-3301-BIS.")
    loaded_ids = {s.get("id") for s in trace.get("skills_loaded") or []}
    assert loaded_ids, "a skill is loaded"
    titles = {s.get("id"): str(s.get("title") or "") for s in load_manifest().get("skills") or []}
    compacted = False
    for i in range(int(settings.compaction_message_threshold) + 2):
        _, trace = successful_turn(client, f"Restons sur ce contrôle de facture ({i}).")
        compacted = compacted or "compaction" in trace
    assert compacted, "the conversation went past the compaction threshold"
    still = {s.get("id") for s in trace.get("skills_loaded") or []}
    assert loaded_ids <= still, "every skill loaded before stays active after the compaction (whatever the order of the list)"
    context = str(model_input(trace))
    for skill_id in loaded_ids:
        assert skill_id in context or (titles.get(skill_id) and titles[skill_id] in context), (
            f"the loaded skill {skill_id} is still in the model input after the compaction"
        )
