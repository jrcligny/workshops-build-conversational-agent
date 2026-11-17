"""Private tests of workshop 05 (not given to students): same checks (`checks.py`), other cases
(`cases_private.yaml`): another pair of namesakes (Hugo Petit, Bordeaux and Strasbourg) and the
late filter on another customer, on both datasets, whose expected total (read from the API) is not
the public one.
"""

import pytest

from testkit.cases import PRIVATE_CASES, load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)


def test_namesakes_several_candidates(chat_client):
    checks.namesakes_several_candidates(chat_client, CASES["namesakes_several_candidates"])


@pytest.mark.parametrize("case", CASES["late_filter_applied_by_the_tool"], ids=lambda c: c["dataset"])
def test_late_filter_applied_by_the_tool(chat_client, observation, business_client, case):
    checks.late_filter_applied_by_the_tool(chat_client, observation, business_client, case)
