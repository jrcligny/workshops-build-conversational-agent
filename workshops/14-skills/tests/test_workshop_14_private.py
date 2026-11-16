"""Private tests of workshop 14 (not given to students): same checks (`checks.py`), other cases
(`cases_private.yaml`): another invoice (FAC-4410), another skill name outside the catalog,
another user without the permission (camille-renard, customer service) and another compaction
threshold.
"""

import pytest

from workshop_config import settings
from workshop_tests.testing.cases import PRIVATE_CASES, load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)


def test_skill_loaded_before_write(services, observation):
    checks.skill_loaded_before_write(services, observation, CASES["skill_loaded_before_write"])


def test_skill_outside_catalog_refused(chat_client):
    checks.skill_outside_catalog_refused(chat_client, CASES["skill_outside_catalog_refused"])


def test_write_according_to_permissions(services, observation):
    checks.write_according_to_permissions(services, observation, CASES["write_according_to_permissions"])


def test_skill_still_present_after_compaction(services, reset_state, monkeypatch):
    case = CASES["skill_still_present_after_compaction"]
    monkeypatch.setattr(settings, "compaction_message_threshold", case["compaction_threshold"])
    checks.skill_still_present_after_compaction(services, case)
