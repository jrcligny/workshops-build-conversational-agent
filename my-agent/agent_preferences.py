"""Long-term memory (workshop 12): a few planned user preferences, kept on disk between conversations.

Only planned topics and values are ever written, at the user's explicit request (through the
remember_preference tool, handled by the harness, never by the tool server). One file per user and
organization under MEMORY_DIR, read at call time; one entry per topic.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

REMEMBER = "remember_preference"
FORGET = "forget_preferences"
TOPICS = {
    "amount_display": {"excluding_tax": "montants hors taxes (HT)", "including_tax": "montants toutes taxes comprises (TTC)"},
    "answer_format": {"table": "réponses sous forme de tableau", "text": "réponses en texte suivi"},
}
OPENING_NOTICE = (
    "Mémoire entre conversations : à votre demande, je peux retenir l'affichage des montants (HT ou TTC) et le "
    "format de mes réponses (tableau ou texte), rien d'autre. Demandez-moi à tout moment de les consulter, de "
    "les corriger ou de les oublier."
)


def _root() -> Path:
    configured = os.environ.get("MEMORY_DIR")
    return Path(configured) if configured else Path(__file__).resolve().parent / "memory"


def _file(user) -> Path:
    safe = lambda value: re.sub(r"[^A-Za-z0-9_.-]", "_", str(value))  # noqa: E731
    return _root() / safe(user.organization) / f"{safe(user.id)}.json"


def load(user) -> list[dict]:
    path = _file(user)
    if not path.is_file():
        return []
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [
        e for e in entries
        if isinstance(e, dict) and e.get("value") in TOPICS.get(e.get("topic"), {})
        and e.get("user") == user.id and e.get("organization") == user.organization
    ]


def _save(user, entries: list[dict]) -> None:
    path = _file(user)
    if not entries:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(re.findall(r"\w+", (text or "").casefold()))


def expressed(request: str, quote: str) -> bool:
    """The model never infers a preference: it quotes the user's current message, where the preference is stated."""
    excerpt = _normalized(quote)
    return len(excerpt.split()) >= 2 and excerpt in _normalized(request)


def remember(user, topic: str, value: str, request: str = "", quote: str = "") -> tuple[dict, dict | None]:
    """Writes one planned preference; returns (tool result, written entry or None)."""
    if not expressed(request, quote):
        return {
            "status": "refused",
            "error": "user_words must quote the user's current message where they state this preference; nothing was stored",
            "fix": "store only a preference the user explicitly states in this message; otherwise say what you can keep",
        }, None
    if topic not in TOPICS or value not in TOPICS[topic]:
        return {
            "status": "refused",
            "error": "only the planned preferences can be kept; nothing was stored",
            "allowed": {t: sorted(v) for t, v in TOPICS.items()},
            "fix": "say that you cannot keep this information from one conversation to the next",
        }, None
    entry = {
        "topic": topic,
        "value": value,
        "origin": "user",
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "user": user.id,
        "organization": user.organization,
    }
    _save(user, [e for e in load(user) if e["topic"] != topic] + [entry])
    return {"status": "written", "topic": topic, "value": value, "meaning": TOPICS[topic][value]}, entry


def forget(user, topic: str | None = None) -> tuple[dict, list[dict]]:
    """Deletes one topic, or every preference of the user when no topic is given."""
    entries = load(user)
    deleted = [e for e in entries if topic in (None, "", "all") or e["topic"] == topic]
    _save(user, [e for e in entries if e not in deleted])
    return {"status": "deleted", "deleted": [{"topic": e["topic"], "value": e["value"]} for e in deleted]}, deleted


def note(entries: list[dict]) -> str:
    if not entries:
        return "Préférences retenues de cet utilisateur (mémoire entre conversations) : aucune."
    lines = ["Préférences retenues de cet utilisateur (mémoire entre conversations ; applique-les) :"]
    lines += [f"- {e['topic']} = {e['value']} : {TOPICS[e['topic']][e['value']]} (retenu le {e['recorded_at'][:10]})"
              for e in entries]
    return "\n".join(lines)


def tool_specs() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": REMEMBER,
                "description": "Keeps ONE planned preference across conversations, only when the user explicitly asks "
                "to remember it: amount_display (excluding_tax | including_tax) or answer_format (table | text). "
                "Anything else (business data, card numbers, statuses) is never stored.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "enum": sorted(TOPICS)},
                        "value": {"type": "string", "enum": sorted({v for vs in TOPICS.values() for v in vs})},
                        "user_words": {
                            "type": "string",
                            "description": "Exact words of the user's current message stating this preference.",
                        },
                    },
                    "required": ["topic", "value", "user_words"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": FORGET,
                "description": "Forgets the user's kept preferences: one topic, or all of them when topic is omitted. "
            "Only when the user explicitly asks to forget or erase them; never to answer what is kept.",
                "parameters": {
                    "type": "object",
                    "properties": {"topic": {"type": "string", "enum": sorted(TOPICS)}},
                },
            },
        },
    ]
