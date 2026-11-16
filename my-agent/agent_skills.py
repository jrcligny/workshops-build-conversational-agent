"""Versioned skills, loaded on demand by the harness (workshop 14).

The catalog is my-agent/skills/manifest.yaml (read through the kit's `load_manifest`). Only its skills
load; any other id is refused. A loaded skill brings its instructions into the model input on every
turn of the conversation (as a system message, so compaction never drops it) and unlocks the write
tools it lists; the user's permissions still apply on top.
"""

from __future__ import annotations

from workshop_kit.services.skills_catalog.catalog import catalog_dir, load_manifest

LOAD_SKILL = "load_skill"


def catalog() -> dict[str, dict]:
    return {s["id"]: s for s in load_manifest().get("skills") or [] if s.get("id")}


def gated_tools() -> set[str]:
    """Write tools that are offered only once the skill that unlocks them is loaded."""
    return {tool for skill in catalog().values() for tool in skill.get("unlocks") or []}


def unlocked(loaded: dict[str, dict]) -> set[str]:
    return {tool for skill in loaded.values() for tool in skill.get("unlocks") or []}


def load(skill_id: str) -> dict:
    """Loads one skill of the catalog: its metadata and its instructions, or a refusal."""
    entries = catalog()
    entry = entries.get((skill_id or "").strip())
    if entry is None:
        return {
            "status": "not_found",
            "error": f"skill {skill_id!r} refusée : inconnue, hors catalogue",
            "catalog": sorted(entries),
        }
    root = catalog_dir().resolve()
    path = (root / entry["path"] / "SKILL.md").resolve()
    if root not in path.parents or not path.is_file():
        return {"status": "error", "error": f"skill {skill_id!r} refusée : fichier absent du catalogue"}
    return {
        "status": "loaded",
        "id": entry["id"],
        "title": entry.get("title"),
        "version": entry.get("version"),
        "unlocks": list(entry.get("unlocks") or []),
        "instructions": path.read_text(encoding="utf-8"),
    }


def tool_spec() -> dict:
    entries = catalog()
    listing = "; ".join(f"{s['id']} (v{s.get('version')}): {s.get('description', s.get('title'))}" for s in entries.values())
    return {
        "type": "function",
        "function": {
            "name": LOAD_SKILL,
            "description": (
                "Loads a business procedure (skill) of the versioned catalog before following it. "
                f"Catalog: {listing}. Whenever the user asks to load a skill, even one outside this catalog, call this "
                "tool with the requested id: the program decides and refuses any id outside the catalog."
            ),
            "parameters": {
                "type": "object",
                "properties": {"skill_id": {"type": "string", "description": "id of a skill of the catalog"}},
                "required": ["skill_id"],
            },
        },
    }


def render(loaded: dict[str, dict]) -> str:
    parts = [
        f"Skill chargée : {s['id']} v{s['version']}\n{s['instructions'].strip()}" for s in loaded.values()
    ]
    return "Skills chargées dans cette conversation (procédures à suivre) :\n\n" + "\n\n".join(parts)
