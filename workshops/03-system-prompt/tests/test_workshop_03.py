"""End-to-end tests of workshop 03. They must fail on the empty shell.

The checks (and the trace contract they read) are in `checks.py`; the cases in `cases.yaml`.
"""

import pytest

from agent_testkit.cases import load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__)


def test_contract_and_short_prompt(chat_client, services):
    checks.contract_and_short_prompt(chat_client, services, CASES["contract_and_short_prompt"])


@pytest.mark.superseded_by("04")
def test_no_tool_yet(chat_client, services):
    checks.no_tool_yet(chat_client, services, CASES["no_tool_yet"])


@pytest.mark.superseded_by("04")
def test_refusal_without_source_even_when_the_status_is_right(chat_client, observation, services):
    checks.refusal_without_source_even_when_the_status_is_right(
        chat_client, observation, services, CASES["refusal_without_source_even_when_the_status_is_right"]
    )


@pytest.mark.superseded_by("04")
def test_refusal_under_insistence(chat_client, observation, services):
    """The refusal holds when the user insists, over two insisting turns."""
    checks.refusal_under_insistence(chat_client, observation, services, CASES["refusal_under_insistence"])


def test_history_replayed_on_second_turn(chat_client):
    checks.history_replayed(chat_client, CASES["history_replayed_on_second_turn"])
