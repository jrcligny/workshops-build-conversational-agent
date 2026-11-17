"""End-to-end tests of workshop 14. They must fail on the empty shell.

The checks (and the contract they read) are in `checks.py`; the cases in `cases.yaml`.
"""

import pytest

from agent_testkit.cases import load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__)


def test_versioned_catalog_of_three_skills():
    checks.versioned_catalog_of_three_skills()


def test_skill_loaded_before_write(services, observation):
    checks.skill_loaded_before_write(services, observation, CASES["skill_loaded_before_write"])


def test_skill_outside_catalog_refused(chat_client):
    checks.skill_outside_catalog_refused(chat_client, CASES["skill_outside_catalog_refused"])


def test_write_according_to_permissions(services, observation):
    checks.write_according_to_permissions(services, observation, CASES["write_according_to_permissions"])


def test_skill_still_present_after_compaction(services, reset_state):
    checks.skill_still_present_after_compaction(services, CASES["skill_still_present_after_compaction"])
