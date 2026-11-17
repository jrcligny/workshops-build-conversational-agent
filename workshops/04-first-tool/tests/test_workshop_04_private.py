"""Private tests of workshop 04 (not given to students): same checks (`checks.py`), other cases
(`cases_private.yaml`): another order (CMD-2010, shipped), another swapped reference
(CMD-2001 → CMD-2010), other excluded orders (CMD-3150 deleted, CMD-0770 rejected: hidden from
customer service) and another malformed reference.
"""

import pytest

from agent_testkit.cases import PRIVATE_CASES, load_cases, load_checks
from agent_testkit.turns import successful_turn, tool_result, tool_status

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)


def test_exact_order_lookup(chat_client, services):
    checks.exact_order_lookup(chat_client, services, CASES["exact_order_lookup"])


def test_swapped_reference_reported(chat_client):
    checks.swapped_reference_reported(chat_client, CASES["swapped_reference_reported"])


@pytest.mark.parametrize("case", CASES["excluded_order_never_returned"], ids=lambda c: c["reference"])
def test_excluded_order_never_returned(chat_client, case):
    checks.excluded_order_never_returned(chat_client, case)


def test_excluded_order_not_suggested_for_a_close_reference(chat_client):
    # Private only: a rejected order is never proposed as a close reference.
    turn, trace = successful_turn(chat_client, "Quel est le statut de la commande CMD-0707 ?")
    call = checks.only_call(trace)
    result = tool_result(call)
    assert tool_status(call) in {"approximate", "not_found"}
    assert "CMD-0770" not in str(result) and "CMD-0770" not in turn.text, (
        "CMD-0770 is hidden from customer service: it is never proposed as a close reference"
    )


def test_invalid_reference_rejected_before_the_call(chat_client, observation):
    checks.invalid_reference_rejected_before_the_call(chat_client, observation, CASES["invalid_reference_rejected_before_the_call"])


def test_tool_result_replayed_next_turn(chat_client):
    checks.tool_result_replayed_next_turn(chat_client, CASES["tool_result_replayed_next_turn"])
