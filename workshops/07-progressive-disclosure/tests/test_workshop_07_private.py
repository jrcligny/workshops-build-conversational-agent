"""Private tests of workshop 07 (not given to students): same checks (`checks.py`), other cases
(`cases_private.yaml`): other phrasings, totals read from the business API (never hard-coded),
a third portion, the detail of another row of the list.
"""

import pytest

from agent_testkit.cases import PRIVATE_CASES, load_cases, load_checks
from agent_testkit.turns import successful_turn

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)


def test_bounded_summary_list_with_declared_total(chat_client, observation, business_client):
    checks.bounded_summary_list_with_declared_total(
        chat_client, observation, business_client, CASES["bounded_summary_list_with_declared_total"]
    )


def test_small_list_is_not_declared_partial(chat_client, observation, business_client):
    # Private only: on the standard dataset, a list under the display limit is complete.
    expected = checks.late_total(business_client)  # standard dataset: fewer late orders than the display limit
    assert 0 < expected <= checks.DISPLAY_LIMIT
    _, trace = successful_turn(chat_client, CASES["small_list_is_not_declared_partial"]["question"])
    listings = checks.listings(trace)
    assert listings, "a list of orders is expected in a tool result (result.orders)"
    result = listings[-1]
    assert (result.get("total"), result.get("total_status"), result.get("truncated")) == (expected, "exact", False)
    assert result.get("returned") == len(result["orders"]) == expected


def test_two_next_portions_without_repeating_rows(chat_client, observation):
    checks.next_portions_without_repeating_rows(chat_client, observation, CASES["two_next_portions_without_repeating_rows"])


def test_total_is_a_minimum_at_the_retrieval_cap(chat_client, observation):
    checks.total_is_a_minimum_at_the_retrieval_cap(chat_client, observation, CASES["total_is_a_minimum_at_the_retrieval_cap"])


def test_count_mode(chat_client, observation, business_client):
    checks.count_mode(chat_client, observation, business_client, CASES["count_mode"])


def test_detail_through_the_consultation_tool(chat_client, observation, business_client):
    checks.detail_through_the_consultation_tool(
        chat_client, observation, business_client, CASES["detail_through_the_consultation_tool"]
    )
