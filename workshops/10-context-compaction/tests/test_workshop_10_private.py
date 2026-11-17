"""Private tests of workshop 10 (not given to students): same checks (`checks.py`), other cases
(`cases_private.yaml`): another threshold and number of kept turns (the agent must read them, not
hard-code 8 and 2), another namesake choice, order, amount and status; plus the Lyon namesake.
"""

import pytest

from agent_testkit.cases import PRIVATE_CASES, load_cases, load_checks
from agent_testkit.turns import successful_turn

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)
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


def test_lyon_namesake_chosen(chat_client):
    # Private only: the other namesake, chosen at once (no compaction involved).
    case = CASES["lyon_namesake_chosen"]
    successful_turn(chat_client, case["request"])
    _, trace = successful_turn(chat_client, case["choice"])
    state = trace.get("state")
    assert isinstance(state, dict) and state, "trace.state must hold the conversation state as an object"
    customer = state.get("current_customer") or {}
    assert customer.get("city") == case["city"] and customer.get("id") == case["id"]
    assert not state.get("candidates"), "the candidates are dropped once the choice is made"


def test_customer_change_without_ambiguity(chat_client):
    checks.customer_change_without_ambiguity(chat_client, CASES["customer_change_without_ambiguity"])
