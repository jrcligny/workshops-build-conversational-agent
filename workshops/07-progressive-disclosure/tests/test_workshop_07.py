"""End-to-end tests of workshop 07: discovering the context progressively. They must fail on the empty shell.

The checks (and the contract they read) are in `checks.py`; the cases in `cases.yaml`.
"""

import pytest

from testkit.cases import load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__)


def test_bounded_summary_list_with_declared_total(chat_client, observation):
    checks.bounded_summary_list_with_declared_total(
        chat_client, observation, None, CASES["bounded_summary_list_with_declared_total"]
    )


def test_next_portion_without_repeating_rows(chat_client, observation):
    checks.next_portions_without_repeating_rows(chat_client, observation, CASES["next_portion_without_repeating_rows"])


def test_total_is_a_minimum_at_the_retrieval_cap(chat_client, observation):
    checks.total_is_a_minimum_at_the_retrieval_cap(chat_client, observation, CASES["total_is_a_minimum_at_the_retrieval_cap"])


def test_count_mode(chat_client, observation):
    checks.count_mode(chat_client, observation, None, CASES["count_mode"])


def test_detail_through_the_consultation_tool(chat_client, observation, business_client):
    checks.detail_through_the_consultation_tool(
        chat_client, observation, business_client, CASES["detail_through_the_consultation_tool"]
    )
