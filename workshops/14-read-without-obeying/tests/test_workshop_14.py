"""End-to-end tests of workshop 14. They must fail on the empty shell.

The checks (and the contract they read) are in `checks.py`; the cases in `cases.yaml`.
The quote (`tests/fixtures/sample-quote.txt`) carries an injected instruction asking for a
10000-euro purchase request; the
attachment is attached to order CMD-2010 (`tests/fixtures/attachments.yaml`).
"""

import pytest

from workshop_config import settings
from agent_testkit.cases import load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__)
ATTACHMENT = CASES["attachment"]
FIXTURES = checks.fixtures_dir(ATTACHMENT)


@pytest.fixture
def quote_area(monkeypatch):
    monkeypatch.setattr(settings, "attachments_dir", str(FIXTURES))
    return FIXTURES


def test_writes_removed_after_attachment(services, observation, quote_area):
    checks.writes_removed_after_attachment(services, observation, ATTACHMENT, CASES["writes_removed_after_attachment"])


def test_writes_removed_after_documentation(services, observation):
    checks.writes_removed_after_documentation(services, observation, CASES["writes_removed_after_documentation"])


def test_read_by_id_according_to_permissions(services, observation, quote_area):
    checks.read_by_id_according_to_permissions(services, observation, ATTACHMENT, CASES["read_by_id_according_to_permissions"])


def test_no_sending_tool(services, quote_area):
    checks.no_sending_tool(services, ATTACHMENT, CASES["no_sending_tool"])
