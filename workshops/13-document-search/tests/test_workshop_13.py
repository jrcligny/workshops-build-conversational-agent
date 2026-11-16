"""End-to-end tests of workshop 13. They must fail on the empty shell."""

import pytest

from workshop_kit.testing.turns import flat, successful_turn, tools

pytestmark = pytest.mark.workshop


def test_document_search_and_sources(chat_client):
    turn, trace = successful_turn(chat_client, "What does the procedure say when a delivery arrives incomplete?")
    assert "sources" in turn.types, "the displayed sources are established by the program (sources event)"
    assert tools(trace)
    assert "procedure" in turn.text.lower() or "incomplete" in turn.text.lower()


def test_empty_result_declared(chat_client):
    turn, _ = successful_turn(chat_client, "What does the documentation say about space travel of xyzzy-42 invoices?")
    text = turn.text.lower()
    assert "no " in text or "not found" in text or "nothing" in text or "empty" in text or "none" in text


def test_permission_filtering(chat_client):
    turn, trace = successful_turn(chat_client, "Give me the internal definition of the invoice statuses, in particular \"paid\".")
    flat_t = (turn.text + flat(tools(trace))).lower()
    # camille works in customer service: the accounting document must not be served to her
    assert "accountant" not in flat_t or "not allowed" in flat_t or "no access" in flat_t or "permission" in flat_t or "no " in flat_t


def test_retired_version_absent(chat_client):
    turn, trace = successful_turn(chat_client, "What is the current version of the incomplete deliveries procedure?")
    flat_t = (turn.text + flat(tools(trace))).lower()
    assert "2.1" in flat_t or "version" in flat_t
    assert "1.0" not in flat_t or "retired" in flat_t


def test_documentation_distinguished_from_data(chat_client):
    turn, _ = successful_turn(
        chat_client,
        "What does the procedure say for an incomplete delivery, and what is the status of CMD-1042?",
    )
    text = turn.text.lower()
    assert "documentation" in text or "procedure" in text or "sources" in turn.types
    assert "cmd-1042" in text or "order" in text or "deliver" in text
