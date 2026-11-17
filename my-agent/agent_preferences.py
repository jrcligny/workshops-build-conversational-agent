"""No memory between conversations (workshop 11): a durable preference is reported, never kept.

The agent keeps nothing from one conversation to the next and says so when a conversation opens. When the
user states one of the planned preferences, the harness reports it in the turn's trace
(`preference_reports`: topic and value, no user) for the publisher; the report is never read back.
The model reports through the report_preference tool, handled by the harness, and must quote the user's
current message: a preference is never inferred.
"""

from __future__ import annotations

import re

REPORT = "report_preference"
TOPICS = {
    "amount_display": {"excluding_tax": "montants hors taxes (HT)", "including_tax": "montants toutes taxes comprises (TTC)"},
    "answer_format": {"table": "réponses sous forme de tableau", "text": "réponses en texte suivi"},
}
OPENING_NOTICE = (
    "Je ne garde rien d'une conversation à l'autre : aucune mémoire entre les conversations. "
    "Redonnez vos préférences dans chaque nouvelle conversation."
)
NOTE = (
    "Aucune mémoire : tu ne gardes rien d'une conversation à l'autre. Une préférence durable énoncée par "
    "l'utilisateur (affichage des montants HT ou TTC, format tableau ou texte) : signale-la avec report_preference, "
    "applique-la dans cette conversation seulement, et dis qu'elle vaut pour cette conversation et ne sera pas "
    "gardée ; ne promets jamais de t'en souvenir."
)


def _normalized(text: str) -> str:
    return " ".join(re.findall(r"\w+", (text or "").casefold()))


def expressed(request: str, quote: str) -> bool:
    """The model never infers a preference: it quotes the user's current message, where the preference is stated."""
    excerpt = _normalized(quote)
    return len(excerpt.split()) >= 2 and excerpt in _normalized(request)


def report(topic: str, value: str, request: str = "", quote: str = "") -> tuple[dict, dict | None]:
    """Reports one planned preference; returns (tool result, report or None). Nothing is stored."""
    if not expressed(request, quote):
        return {
            "status": "refused",
            "error": "user_words must quote the user's current message where they state this preference",
            "fix": "report only a preference the user explicitly states in this message",
        }, None
    if topic not in TOPICS or value not in TOPICS[topic]:
        return {
            "status": "refused",
            "error": "only the planned preferences are reported",
            "allowed": {t: sorted(v) for t, v in TOPICS.items()},
        }, None
    return {
        "status": "reported",
        "topic": topic,
        "value": value,
        "meaning": TOPICS[topic][value],
        "kept": False,
        "note": "applies to this conversation only; nothing is kept for the next one: say so, promise nothing",
    }, {"topic": topic, "value": value}


def tool_specs() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": REPORT,
                "description": "Reports ONE planned preference the user states in their current message: "
                "amount_display (excluding_tax | including_tax) or answer_format (table | text). Nothing is kept "
                "between conversations. Anything else (business data, IBAN, supplier) is never reported.",
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
    ]
