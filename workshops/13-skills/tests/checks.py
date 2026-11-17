"""Checks of workshop 13, shared by the public and the private tests (one function per criterion).

Contract read here:
- `my-agent/skills/manifest.yaml`: `skills[]` with `id`, `title`, `version`, `path` (folder
  under `my-agent/skills/` holding the procedure);
- trace `skills_loaded`: list of `{"id", "version", "cycle"}` (skills loaded in the turn or
  still active in the conversation); trace `offered_tools`: one list of tool names per model
  call, in order (what the model could call at that cycle);
- `tools[].cycle` (workshop 06), `tools[].result.status`; application state `drafts`.
Invoice approval is written by the `accountant` role (nina-accountant).
"""

from agent_sdk.skills import catalog_dir, load_manifest
from workshop_config import settings
from agent_testkit.chat_client import ChatClient
from agent_testkit.expect import business_writes, mentions_any
from agent_testkit.turns import model_input, successful_turn, tool_arguments, tool_name, tool_status, tools


def client(services, user: dict) -> ChatClient:
    chat = ChatClient(services["interface"])
    chat.open(user_id=user["user_id"], role=user["role"], organization="organization-a")
    return chat


def versioned_catalog_of_three_skills() -> None:
    skills = load_manifest().get("skills") or []
    assert len(skills) == 3, "the versioned catalog contains exactly the three planned skills"
    assert len({s.get("id") for s in skills}) == 3
    for skill in skills:
        assert skill.get("version") and skill.get("title"), "each skill has a title and a version"
        folder = catalog_dir() / str(skill.get("path") or "")
        assert folder.is_dir() and any(p.stat().st_size for p in folder.rglob("*") if p.is_file()), (
            f"the folder of skill {skill.get('id')} holds its procedure"
        )


def skill_loaded_before_write(services, observation, case: dict) -> None:
    turn, trace = successful_turn(client(services, case["user"]), case["message"])
    writes = business_writes(trace)
    assert writes, "the approval is prepared through a write tool (the result carries the draft id)"
    if case.get("draft_about"):
        assert any(case["draft_about"] in str(tool_arguments(c)) for c in writes), f"the draft is about {case['draft_about']}"
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


def skill_outside_catalog_refused(chat_client, case: dict) -> None:
    skill = case["skill"]
    turn, trace = successful_turn(chat_client, case["message"])
    attempts = [c for c in tools(trace) if skill in str(tool_arguments(c))]
    assert attempts, "the load request reaches the program, which decides"
    assert {tool_status(c) for c in attempts} <= {"not_found", "denied", "error"}, "a skill outside the catalog is refused"
    assert skill not in str(trace.get("skills_loaded") or [])


def write_according_to_permissions(services, observation, case: dict) -> None:
    _, trace = successful_turn(client(services, case["writer"]), case["message"])
    writes = business_writes(trace)
    assert writes, "the accountant can prepare the approval"
    write_name = tool_name(writes[0])
    observation.reset("standard")
    turn, trace = successful_turn(client(services, case["denied_user"]), case["message"])
    assert trace.get("offered_tools"), "trace.offered_tools is recorded"
    assert not any(write_name in names for names in trace["offered_tools"]), "the write tool is never offered without the permission"
    assert observation.state("submissions")["drafts"] == []
    mentions_any(turn, case["refusal_words"], "the user is told they cannot approve")


def skill_still_present_after_compaction(services, case: dict) -> None:
    chat = client(services, case["user"])
    _, trace = successful_turn(chat, case["message"])
    loaded_ids = {s.get("id") for s in trace.get("skills_loaded") or []}
    assert loaded_ids, "a skill is loaded"
    titles = {s.get("id"): str(s.get("title") or "") for s in load_manifest().get("skills") or []}
    assert len(case["conversation"]) > int(settings.compaction_message_threshold), "the written exchange passes the threshold"
    chat.load(case["conversation"], append=True)
    _, trace = successful_turn(chat, case["follow_up"])
    assert "compaction" in trace, "the conversation went past the compaction threshold"
    still = {s.get("id") for s in trace.get("skills_loaded") or []}
    assert loaded_ids <= still, "every skill loaded before stays active after the compaction (whatever the order of the list)"
    context = str(model_input(trace))
    for skill_id in loaded_ids:
        assert skill_id in context or (titles.get(skill_id) and titles[skill_id] in context), (
            f"the loaded skill {skill_id} is still in the model input after the compaction"
        )
