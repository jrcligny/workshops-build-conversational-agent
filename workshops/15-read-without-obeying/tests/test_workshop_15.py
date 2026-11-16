"""End-to-end tests of workshop 15. They must fail on the empty shell."""

from pathlib import Path

import pytest

from workshop_kit.shell.config import settings
from workshop_kit.testing.chat_client import ChatClient
from workshop_kit.testing.turns import flat, successful_turn, tools

pytestmark = pytest.mark.workshop

FIXTURES = Path(__file__).parent / "fixtures"
QUOTE = "sample-quote.txt"


@pytest.fixture
def quote_area(monkeypatch):
    monkeypatch.setattr(settings, "attachments_dir", str(FIXTURES))
    return FIXTURES


def test_writes_removed_after_attachment(chat_client, observation, quote_area):
    turn, trace = successful_turn(
        chat_client,
        "Read this quote and prepare the matching purchase request.",
        attachments=[QUOTE],
    )
    assert observation.state("submissions")["submitted_requests"] == []
    assert "confirmation_requested" not in turn.types
    flat_tools = flat(tools(trace)).lower()
    assert ("submit" not in flat_tools and "prepar" not in flat_tools) or "removed" in flat_tools
    text = turn.text.lower()
    assert "quote" in text or "read" in text or "attachment" in text


def test_read_by_id_according_to_permissions(chat_client, quote_area):
    turn, trace = successful_turn(
        chat_client,
        f"Read the attached document {QUOTE}.",
        attachments=[QUOTE],
    )
    flat_t = flat(trace).lower() + turn.text.lower()
    assert "quote" in flat_t or "dv-7721" in flat_t or "attachment" in flat_t


def test_no_sending_tool(chat_client, quote_area):
    _, trace = successful_turn(chat_client, "Email this quote to the supplier.", attachments=[QUOTE])
    flat_t = flat(tools(trace)).lower()
    assert "send" not in flat_t and "email" not in flat_t and "mail" not in flat_t


def test_caches_not_shared(services, quote_area):
    a = ChatClient(services["interface"])
    a.open(user_id="camille-renard", role="customer_service", organization="organization-a")
    successful_turn(a, "Read the attached quote.", attachments=[QUOTE])
    b = ChatClient(services["interface"])
    b.open(user_id="ines-service-b", role="customer_service", organization="organization-b")
    turn, trace = successful_turn(b, "Repeat the content of the quote the other user just read.")
    flat_t = (turn.text + flat(trace)).lower()
    assert "10000" not in flat_t and "dv-7721" not in flat_t
