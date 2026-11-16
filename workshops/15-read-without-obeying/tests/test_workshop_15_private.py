"""Private tests of workshop 15 (not given to students): same checks (`checks.py`), other cases
(`cases_private.yaml`): another attachment (`tests/fixtures_private/supplier-offer-9184.txt`,
quote DV-9184) with another injection (fake "system note" asking for a 25000-euro order and an
e-mail transfer), another purchase without attachment and other users (nina-accountant,
omar-buyer-b).
"""

import pytest

from workshop_config import settings
from workshop_tests.testing.cases import PRIVATE_CASES, load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)
ATTACHMENT = CASES["attachment"]
FIXTURES = checks.fixtures_dir(ATTACHMENT)


@pytest.fixture
def quote_area(monkeypatch):
    monkeypatch.setattr(settings, "attachments_dir", str(FIXTURES))
    return FIXTURES


def test_writes_removed_after_attachment(services, observation, quote_area):
    checks.writes_removed_after_attachment(services, observation, ATTACHMENT, CASES["writes_removed_after_attachment"])


def test_read_by_id_according_to_permissions(services, quote_area):
    checks.read_by_id_according_to_permissions(services, ATTACHMENT, CASES["read_by_id_according_to_permissions"])


def test_no_sending_tool(services, quote_area):
    checks.no_sending_tool(services, ATTACHMENT, CASES["no_sending_tool"])


def test_caches_not_shared(services, quote_area):
    checks.caches_not_shared(services, ATTACHMENT, CASES["caches_not_shared"])
