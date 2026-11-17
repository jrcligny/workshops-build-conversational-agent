"""End-to-end tests of workshop 12: a persistent preference memory. They must fail on the empty shell.

The checks (and the contract they read) are in `checks.py`; the cases in `cases.yaml`.
"""

import pytest

from agent_testkit.cases import load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__)


def test_memory_announced_on_opening(chat_client):
    checks.memory_announced_on_opening(chat_client, CASES["memory_announced_on_opening"])


def test_preference_recalled_in_a_new_conversation(services, reset_state):
    checks.preference_recalled_in_a_new_conversation(services, CASES["preference_recalled_in_a_new_conversation"])


def test_memory_partitioned_by_user_and_organization(services, reset_state):
    checks.memory_partitioned_by_user_and_organization(services, CASES["memory_partitioned_by_user_and_organization"])


def test_consult_correct_forget(services, reset_state):
    checks.consult_correct_forget(services, CASES["consult_correct_forget"])


def test_only_planned_topics_are_kept(services, reset_state):
    checks.only_planned_topics_are_kept(services, CASES["only_planned_topics_are_kept"])


def test_rereads_rather_than_assumes(chat_client, observation):
    checks.rereads_rather_than_assumes(chat_client, observation, CASES["rereads_rather_than_assumes"])
