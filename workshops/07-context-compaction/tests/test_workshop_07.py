"""End-to-end tests of workshop 07. They must fail on the empty shell.

Trace contract read here: `tools[].result` with `total`, `truncated` and, in count mode,
`count`; `model.calls[].context_size` (size of the context sent at each cycle); `compaction`
(object present only on the turn where the history was compacted: `summarized_answers`,
`kept_user_messages`, `threshold`). Interface events: `compaction` and/or `mention`.
"""

import pytest

from workshop_kit.shell.config import settings
from workshop_tests.testing.turns import (
    apply_rubric,
    events_of,
    history,
    model_input,
    successful_turn,
    tool_arguments,
    tool_result,
    tools,
)

pytestmark = pytest.mark.workshop

INITIAL_REQUEST = "Je traite le dossier de Martin Durand, commande CMD-1042, commandes livrées uniquement."

PARTIAL_RUBRIC = {
    "id": "07-partial-result-announced",
    "criterion": "The agent says in French that it shows only part of the list and gives the total read from the tool.",
    "judge_meaning": True,
    "requirements": [{"type": "required_any", "patterns": ["partiel", "partielle", "une partie", "extrait", "premières"]}],
}


def _late_total(business_client) -> int:
    customer = business_client.get("/customers", params={"name": "Transports Morel"}).json()[0]
    return business_client.get(f"/customers/{customer['id']}/orders", params={"filter": "late"}).json()["total"]


def test_bounded_list_and_declared_total(chat_client, observation, business_client):
    observation.reset("volume")
    expected = _late_total(business_client)
    turn, trace = successful_turn(chat_client, "Quelles sont les commandes en retard de Transports Morel ?")
    listings = [tool_result(c) for c in tools(trace) if isinstance(tool_result(c).get("orders"), list)]
    assert listings, "a list of orders is expected in a tool result (result.orders)"
    result = listings[-1]
    assert len(result["orders"]) < expected, "the tool bounds the rows returned to the model"
    assert result.get("truncated") is True and result.get("total") == expected, "result.truncated and result.total declare the cut"
    assert str(expected) in turn.text, f"the answer gives the total ({expected})"
    apply_rubric(PARTIAL_RUBRIC, turn, trace)
    sizes = [c.get("context_size") for c in (trace.get("model") or {}).get("calls") or []]
    assert sizes and all(sizes), "model.calls[].context_size records the context size at each cycle"


def test_count_mode(chat_client, observation, business_client):
    observation.reset("volume")
    expected = _late_total(business_client)
    turn, trace = successful_turn(
        chat_client, "Combien de commandes en retard a Transports Morel ? Je veux seulement le nombre, pas les lignes."
    )
    counted = [c for c in tools(trace) if tool_result(c).get("count") == expected]
    assert counted, "a count-mode call returns result.count, the number without the rows"
    assert not tool_result(counted[-1]).get("orders"), "count mode returns no rows"
    assert tool_arguments(counted[-1]).get("mode") == "count", "count mode is a tool argument (mode: \"count\")"
    assert str(expected) in turn.text


def test_no_compaction_below_threshold(chat_client):
    successful_turn(chat_client, INITIAL_REQUEST)
    _, trace = successful_turn(chat_client, "Pouvez-vous simplement confirmer le client en cours ?")
    assert INITIAL_REQUEST in [m.get("content") for m in history(trace)], "below the threshold the history is replayed verbatim"
    assert "compaction" not in trace, "no compaction below the threshold"


def _run_past_threshold(chat_client) -> tuple[list[str], object, dict]:
    messages = [INITIAL_REQUEST]
    turn, trace = successful_turn(chat_client, INITIAL_REQUEST)
    compacted = None
    for i in range(int(settings.compaction_message_threshold) + 2):
        msg = f"Détail numéro {i} : je veux seulement les commandes livrées de CMD-1042."
        messages.append(msg)
        turn, trace = successful_turn(chat_client, msg)
        if isinstance(trace.get("compaction"), dict):
            compacted = (list(messages), turn, trace)
    assert compacted, "a trace past the threshold must contain a compaction object"
    return compacted


def test_compaction_above_threshold_keeps_user_messages(chat_client):
    messages, _, trace = _run_past_threshold(chat_client)
    event = trace["compaction"]
    assert event.get("summarized_answers", 0) >= 1, "compaction.summarized_answers counts the summarized answers"
    replayed = [m.get("content") for m in history(trace) if m.get("role") == "user"]
    missing = [m for m in messages[:-1] if m not in replayed]
    assert not missing, f"user messages are replayed verbatim after compaction; missing: {missing[:2]}"
    assert model_input(trace).get("message") == messages[-1]
    assert len(history(trace)) < 2 * len(messages) - 1, "the replayed history is shorter than the full history"


def test_compaction_reported_in_the_interface(chat_client):
    _, turn, _ = _run_past_threshold(chat_client)
    assert events_of(turn, "compaction") or events_of(turn, "mention"), (
        "the interface is told (compaction or mention event) that the start of the conversation was summarized"
    )
