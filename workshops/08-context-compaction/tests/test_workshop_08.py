"""End-to-end tests of workshop 08: compaction and the working memory that survives it.
They must fail on the empty shell.

Contract read here:
- `compaction` (object present only on the turn where the history was compacted:
  `summarized_answers`, `kept_user_messages`, `threshold` = `COMPACTION_MESSAGE_THRESHOLD`,
  `summary`, found again in the model input);
  `input.history[]` (`role`, `content`); interface events `compaction` and/or `mention`;
- `state` (the conversation state after the turn, kept outside the history: `current_customer`
  {id, name, city}, `current_order` {reference}, `candidates` while a namesake choice is pending)
  and `input.state` (the state sent to the model at the start of the turn).
"""

import pytest

from workshop_kit.shell.config import settings
from workshop_tests.testing.turns import events_of, history, model_input, successful_turn, tool_arguments, tools

pytestmark = pytest.mark.workshop

INITIAL_REQUEST = "Je traite le dossier de Martin Durand, commande CMD-1042, commandes livrées uniquement."


def test_no_compaction_below_threshold(chat_client):
    successful_turn(chat_client, INITIAL_REQUEST)
    _, trace = successful_turn(chat_client, "Pouvez-vous simplement confirmer le client en cours ?")
    assert INITIAL_REQUEST in [m.get("content") for m in history(trace)], "below the threshold the history is replayed verbatim"
    assert "compaction" not in trace, "no compaction below the threshold"


def _strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        value = list(value.values())
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


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
    previous_turns = len(messages) - 1
    answers = [m for m in history(trace) if m.get("role") == "assistant"]
    assert len(answers) < previous_turns, "earlier answers are replaced by a summary, not all replayed"
    assert event.get("kept_user_messages", 0) >= 1, "compaction.kept_user_messages counts the earlier user messages kept verbatim"
    assert event.get("threshold") == int(settings.compaction_message_threshold), "compaction.threshold is the configured threshold"
    summary = event.get("summary")
    assert isinstance(summary, str) and summary.strip(), "compaction.summary holds the summary that replaces the old answers"
    assert any(summary.strip() in s for s in _strings(model_input(trace))), "the model input contains the summary"


def test_compaction_reported_in_the_interface(chat_client):
    _, turn, _ = _run_past_threshold(chat_client)
    assert events_of(turn, "compaction") or events_of(turn, "mention"), (
        "the interface is told (compaction or mention event) that the start of the conversation was summarized"
    )


def _state(trace) -> dict:
    state = trace.get("state")
    assert isinstance(state, dict) and state, "trace.state must hold the conversation state as an object"
    return state


def _fill_past_threshold(chat_client, text: str) -> None:
    for i in range(int(settings.compaction_message_threshold) + 2):
        successful_turn(chat_client, f"{text} ({i}).")


def test_state_kept_after_compaction(chat_client):
    successful_turn(chat_client, "Quel est le statut de la commande CMD-1042 de Martin Durand ?")
    _fill_past_threshold(chat_client, "D'accord, continuez à suivre ce dossier")
    turn, trace = successful_turn(chat_client, "Et celle-là, où en est-elle ?")
    state = trace.get("input", {}).get("state")
    assert isinstance(state, dict) and (state.get("current_order") or {}).get("reference") == "CMD-1042", (
        "input.state.current_order.reference is CMD-1042 even after the history was summarized"
    )
    assert (state.get("current_customer") or {}).get("name") == "Martin Durand"
    assert "CMD-1042" in str([tool_arguments(c) for c in tools(trace)]) or "livrée" in turn.text.lower(), (
        "\"celle-là\" is resolved from the state: the answer is about CMD-1042"
    )


def test_choice_between_namesakes_kept(chat_client):
    _, trace = successful_turn(chat_client, "Quelles sont les commandes de Léa Martin ?")
    assert len(_state(trace).get("candidates") or []) == 2, "state.candidates holds the two namesakes while the choice is pending"
    _, trace = successful_turn(chat_client, "Celle de Lille, s'il vous plaît.")
    assert (_state(trace).get("current_customer") or {}).get("city") == "Lille", "state.current_customer is the Lille namesake"
    _fill_past_threshold(chat_client, "Merci, restons sur ce dossier")
    turn, trace = successful_turn(chat_client, "Rappelez-moi le client en cours.")
    assert (_state(trace).get("current_customer") or {}).get("city") == "Lille"
    assert "lille" in turn.text.lower() and "lyon" not in turn.text.lower()


def test_customer_change_without_ambiguity(chat_client):
    _, trace = successful_turn(chat_client, "Quel est le statut de la commande CMD-1042 de Martin Durand ?")
    assert (_state(trace).get("current_customer") or {}).get("name") == "Martin Durand"
    _, trace = successful_turn(chat_client, "Passons maintenant à Transports Morel : combien a-t-il de commandes ?")
    state = _state(trace)
    assert (state.get("current_customer") or {}).get("name") == "Transports Morel", "the current customer is replaced"
    assert "CMD-1042" not in str(state.get("current_order") or ""), "the order of the previous customer is dropped"
