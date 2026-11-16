"""Private tests of workshop 08 (not given to students): same criteria, other inputs.

Another threshold (the configured value is changed: the agent must read it, not hard-code 8),
another initial request, the Lyon namesake, another order in the state, another customer change.
"""

import pytest

from workshop_config import settings
from workshop_tests.testing.turns import events_of, history, model_input, successful_turn, tool_arguments, tools

pytestmark = pytest.mark.workshop

THRESHOLD = 5
INITIAL_REQUEST = "Dossier Léa Martin de Lille, commande CMD-2010 : je ne veux voir que les commandes expédiées."


@pytest.fixture(autouse=True)
def other_threshold(monkeypatch):
    monkeypatch.setattr(settings, "compaction_message_threshold", THRESHOLD)


def _strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        value = list(value.values())
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


def _state(trace) -> dict:
    state = trace.get("state")
    assert isinstance(state, dict) and state, "trace.state must hold the conversation state as an object"
    return state


def _fill_past_threshold(chat_client, text: str) -> None:
    for i in range(THRESHOLD + 2):
        successful_turn(chat_client, f"{text} ({i}).")


def test_no_compaction_below_threshold(chat_client):
    successful_turn(chat_client, INITIAL_REQUEST)
    _, trace = successful_turn(chat_client, "Quel client suivons-nous ?")
    assert INITIAL_REQUEST in [m.get("content") for m in history(trace)], "below the threshold the history is replayed verbatim"
    assert "compaction" not in trace, "no compaction below the threshold"


def _run_past_threshold(chat_client):
    messages = [INITIAL_REQUEST]
    turn, trace = successful_turn(chat_client, INITIAL_REQUEST)
    compacted = None
    for i in range(THRESHOLD + 3):
        msg = f"Point {i} : on reste sur les commandes expédiées de CMD-2010, rien d'autre."
        messages.append(msg)
        turn, trace = successful_turn(chat_client, msg)
        if isinstance(trace.get("compaction"), dict):
            compacted = (list(messages), turn, trace)
    assert compacted, "a trace past the (changed) threshold must contain a compaction object"
    return compacted


def test_compaction_follows_the_configured_threshold(chat_client):
    messages, turn, trace = _run_past_threshold(chat_client)
    event = trace["compaction"]
    assert event.get("threshold") == THRESHOLD, "compaction.threshold is the configured threshold, read at run time"
    assert event.get("summarized_answers", 0) >= 1
    assert event.get("kept_user_messages", 0) >= 1
    replayed = [m.get("content") for m in history(trace) if m.get("role") == "user"]
    missing = [m for m in messages[:-1] if m not in replayed]
    assert not missing, f"user messages are replayed verbatim after compaction; missing: {missing[:2]}"
    assert model_input(trace).get("message") == messages[-1]
    answers = [m for m in history(trace) if m.get("role") == "assistant"]
    assert len(answers) < len(messages) - 1, "earlier answers are replaced by a summary, not all replayed"
    summary = event.get("summary")
    assert isinstance(summary, str) and summary.strip()
    assert any(summary.strip() in s for s in _strings(model_input(trace))), "the model input contains the summary"
    assert events_of(turn, "compaction") or events_of(turn, "mention"), "the interface is told about the compaction"


def test_state_kept_after_compaction(chat_client):
    successful_turn(chat_client, "Où en est la commande CMD-2010 de Léa Martin à Lille ?")
    _fill_past_threshold(chat_client, "Bien noté, gardez ce dossier sous la main")
    turn, trace = successful_turn(chat_client, "Et du coup, elle arrive quand, celle-ci ?")
    state = trace.get("input", {}).get("state")
    assert isinstance(state, dict) and (state.get("current_order") or {}).get("reference") == "CMD-2010", (
        "input.state.current_order.reference is CMD-2010 even after the history was summarized"
    )
    customer = state.get("current_customer") or {}
    assert customer.get("name") == "Léa Martin" and customer.get("city") == "Lille"
    assert "CMD-2010" in str([tool_arguments(c) for c in tools(trace)]) or "expédiée" in turn.text.lower(), (
        "\"celle-ci\" is resolved from the state: the answer is about CMD-2010"
    )


def test_choice_between_namesakes_kept(chat_client):
    _, trace = successful_turn(chat_client, "Je cherche le client Hugo Petit.")
    assert len(_state(trace).get("candidates") or []) == 2, "state.candidates holds the two namesakes while the choice is pending"
    _, trace = successful_turn(chat_client, "C'est celui de Strasbourg.")
    assert (_state(trace).get("current_customer") or {}).get("city") == "Strasbourg"
    _fill_past_threshold(chat_client, "Parfait, on continue avec lui")
    turn, trace = successful_turn(chat_client, "Dans quelle ville est le client que nous suivons ?")
    assert (_state(trace).get("current_customer") or {}).get("city") == "Strasbourg"
    assert "strasbourg" in turn.text.lower() and "bordeaux" not in turn.text.lower()


def test_lyon_namesake_chosen(chat_client):
    successful_turn(chat_client, "Montrez-moi les commandes de Léa Martin.")
    _, trace = successful_turn(chat_client, "La cliente de Lyon.")
    customer = _state(trace).get("current_customer") or {}
    assert customer.get("city") == "Lyon" and customer.get("id") == "C-MARTIN-LYON"
    assert not _state(trace).get("candidates"), "the candidates are dropped once the choice is made"


def test_customer_change_without_ambiguity(chat_client):
    _, trace = successful_turn(chat_client, "Où en est la commande CMD-2010 de Léa Martin à Lille ?")
    assert (_state(trace).get("current_order") or {}).get("reference") == "CMD-2010"
    _, trace = successful_turn(chat_client, "Laissons ce dossier : regardons Martin Durand, a-t-il des commandes en retard ?")
    state = _state(trace)
    assert (state.get("current_customer") or {}).get("name") == "Martin Durand", "the current customer is replaced"
    assert "CMD-2010" not in str(state.get("current_order") or ""), "the order of the previous customer is dropped"
