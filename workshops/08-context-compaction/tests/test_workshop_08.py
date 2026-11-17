"""End-to-end tests of workshop 08: clearing old tool results, compacting with a dedicated prompt,
and the working memory that survives it. They must fail on the empty shell.

The checks (and the contract they read) are in `checks.py`; the cases, with the written
conversation loaded instead of played, in `cases.yaml`.
"""

import pytest

from testkit.cases import load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__)
SCENARIO = CASES["scenario"]


@pytest.fixture(autouse=True)
def thresholds(monkeypatch):
    checks.configure(monkeypatch, SCENARIO)


def test_no_compaction_below_threshold(chat_client):
    checks.no_compaction_below_threshold(chat_client, SCENARIO, CASES["no_compaction_below_threshold"])


def test_tool_results_cleared(chat_client):
    checks.tool_results_cleared(chat_client, SCENARIO, CASES["tool_results_cleared"])


def test_compaction_own_prompt_and_rolling_summary(chat_client, services):
    checks.compaction_own_prompt_and_rolling_summary(chat_client, services, SCENARIO, CASES["compaction_own_prompt_and_rolling_summary"])


def test_summary_keeps_tool_facts(chat_client):
    checks.summary_keeps_tool_facts(chat_client, SCENARIO, CASES["summary_keeps_tool_facts"])


def test_answer_from_summary_after_compaction(chat_client, observation):
    checks.answer_from_summary_after_compaction(chat_client, observation, SCENARIO, CASES["answer_from_summary_after_compaction"])


def test_compaction_reported_in_the_interface(chat_client):
    checks.compaction_reported_in_the_interface(chat_client, SCENARIO, CASES["compaction_reported_in_the_interface"])


def test_state_kept_after_compaction(chat_client):
    checks.state_kept_after_compaction(chat_client, SCENARIO, CASES["state_kept_after_compaction"])


def test_choice_between_namesakes_kept(chat_client):
    checks.choice_between_namesakes_kept(chat_client, SCENARIO, CASES["choice_between_namesakes_kept"])


def test_customer_change_without_ambiguity(chat_client):
    checks.customer_change_without_ambiguity(chat_client, CASES["customer_change_without_ambiguity"])
