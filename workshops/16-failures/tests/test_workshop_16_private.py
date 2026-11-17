"""Private tests of workshop 16 (not given to students): same checks (`checks.py`), other cases
(`cases_private.yaml`): another buyer and organization (omar-buyer-b), another purchase, another
order for the fallback (CMD-2010, shipped) and other questions around the index rebuild.
"""

import pytest

from agent_testkit.cases import PRIVATE_CASES, load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)


def test_submission_never_replayed(services, observation):
    checks.submission_never_replayed(services, observation, CASES["submission_never_replayed"])


def test_single_fallback_then_end(chat_client, services):
    checks.single_fallback_then_end(chat_client, services, CASES["single_fallback_then_end"])


def test_versions_in_the_trace(chat_client, services):
    checks.versions_in_the_trace(chat_client, services, CASES["versions_in_the_trace"])
