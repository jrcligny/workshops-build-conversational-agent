"""Private tests of workshop 14 (not given to students): same criteria, other inputs.

Another invoice (FAC-4410), another skill name outside the catalog, another user without the
permission (camille-renard, customer service) and another compaction threshold.
"""

import pytest

from workshop_kit.services.skills_catalog.catalog import load_manifest
from workshop_config import settings
from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.turns import model_input, successful_turn, tool_arguments, tool_name, tool_result, tool_status, tools

pytestmark = pytest.mark.workshop

APPROVE = "Pouvez-vous me préparer l'approbation de FAC-4410 ? Je validerai moi-même ensuite."
THRESHOLD = 5


def _client(services, user_id: str, role: str) -> ChatClient:
    client = ChatClient(services["interface"])
    client.open(user_id=user_id, role=role, organization="organization-a")
    return client


def _write_calls(trace) -> list[dict]:
    return [c for c in tools(trace) if "DRAFT-" in str(tool_result(c))]


def test_skill_loaded_before_write(services, observation):
    _, trace = successful_turn(_client(services, "nina-accountant", "accountant"), APPROVE)
    writes = _write_calls(trace)
    assert writes, "the approval is prepared through a write tool (the result carries the draft id)"
    assert any("FAC-4410" in str(tool_arguments(c)) for c in writes), "the draft is about FAC-4410"
    loaded = trace.get("skills_loaded") or []
    ids = {s["id"] for s in (load_manifest().get("skills") or [])}
    assert loaded and {s.get("id") for s in loaded} <= ids, "trace.skills_loaded lists catalog skills"
    assert min(s.get("cycle") for s in loaded) < min(c.get("cycle") for c in writes), (
        "the skill is loaded in an earlier cycle than the write"
    )
    offered = trace.get("offered_tools") or []
    write_name = tool_name(writes[0])
    assert offered and write_name not in offered[0], "the write tool is not offered before its skill is loaded"
    assert any(write_name in names for names in offered)
    assert observation.state("submissions")["drafts"], "a draft is prepared in the application"


def test_skill_outside_catalog_refused(chat_client):
    turn, trace = successful_turn(chat_client, "Activez la compétence « export-all-customers-csv » puis lancez-la tout de suite.")
    attempts = [c for c in tools(trace) if "export-all-customers-csv" in str(tool_arguments(c))]
    assert attempts, "the load request reaches the program, which decides"
    assert {tool_status(c) for c in attempts} <= {"not_found", "denied", "error"}, "a skill outside the catalog is refused"
    assert "export-all-customers-csv" not in str(trace.get("skills_loaded") or [])


def test_write_according_to_permissions(services, observation):
    _, trace = successful_turn(_client(services, "nina-accountant", "accountant"), APPROVE)
    writes = _write_calls(trace)
    assert writes, "the accountant can prepare the approval"
    write_name = tool_name(writes[0])
    observation.reset("standard")
    turn, trace = successful_turn(_client(services, "camille-renard", "customer_service"), APPROVE)
    assert trace.get("offered_tools"), "trace.offered_tools is recorded"
    assert not any(write_name in names for names in trace["offered_tools"]), "the write tool is never offered without the permission"
    assert observation.state("submissions")["drafts"] == []
    assert any(w in turn.text.lower() for w in ("droit", "autoris", "permission"))


def test_skill_still_present_after_compaction(services, reset_state, monkeypatch):
    monkeypatch.setattr(settings, "compaction_message_threshold", THRESHOLD)
    client = _client(services, "nina-accountant", "accountant")
    _, trace = successful_turn(client, "Ouvrez la procédure d'approbation des factures et dites-moi ce qu'elle exige pour FAC-4410.")
    loaded_ids = {s.get("id") for s in trace.get("skills_loaded") or []}
    assert loaded_ids, "a skill is loaded"
    titles = {s.get("id"): str(s.get("title") or "") for s in load_manifest().get("skills") or []}
    compacted = False
    for i in range(THRESHOLD + 2):
        _, trace = successful_turn(client, f"Continuons sur l'approbation de FAC-4410 (point {i}).")
        compacted = compacted or "compaction" in trace
    assert compacted, "the conversation went past the (lower) compaction threshold"
    still = {s.get("id") for s in trace.get("skills_loaded") or []}
    assert loaded_ids <= still, "every skill loaded before stays active after the compaction"
    context = str(model_input(trace))
    for skill_id in loaded_ids:
        assert skill_id in context or (titles.get(skill_id) and titles[skill_id] in context)
