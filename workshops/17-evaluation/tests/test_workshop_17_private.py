"""Private test of workshop 17 (not given to students): same check (`checks.py`), other case
(`cases_private.yaml`): masked and observable traces on another turn (another user, a turn that
chains several tool calls). The catalog and route tests have no input to vary and have no
private variant.
"""

import pytest

from workshop_tests.testing.cases import PRIVATE_CASES, load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)


def test_masked_and_observable_traces(services, traces):
    case = CASES["masked_and_observable_traces"]
    checks.masked_and_observable_traces(checks.client(services, case["user"]), traces, case)
