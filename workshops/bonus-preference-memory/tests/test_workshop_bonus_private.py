"""Private tests of the bonus workshop (not given to students): same checks (`checks.py`), other cases
(`cases_private.yaml`): another user and topic (paul-buyer, answer_format = table), other users
that must not see it (camille-renard, omar-buyer-b), forgetting one topic only, other data that
must not be kept (IBAN, customer name) and another order to reread (CMD-2010).
"""

import pytest

from agent_testkit.cases import PRIVATE_CASES, load_cases, load_checks
from agent_testkit.turns import successful_turn

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)


def test_preference_recalled_in_a_new_conversation(services, reset_state):
    checks.preference_recalled_in_a_new_conversation(services, CASES["preference_recalled_in_a_new_conversation"])


def test_memory_partitioned_by_user_and_organization(services, reset_state):
    checks.memory_partitioned_by_user_and_organization(services, CASES["memory_partitioned_by_user_and_organization"])


def test_forget_one_topic_only(services, reset_state):
    # Private only: two topics are kept, then only one is forgotten.
    paul = CASES["users"]["paul"]
    client = checks.conversation(services, paul)
    successful_turn(client, CASES["remember_table"]["message"])
    _, trace = successful_turn(client, "Et retenez aussi que je veux les montants toutes taxes comprises.")
    assert [e for e in checks.entries(trace, "written", "amount_display") if e.get("value") == "including_tax"]

    client = checks.conversation(services, paul)
    _, trace = successful_turn(client, "Oubliez seulement ma préférence de format de réponse, gardez le reste.")
    deleted = checks.memory(trace).get("deleted") or []
    assert [e.get("topic") for e in deleted] == ["answer_format"], "only the named topic is forgotten"

    client = checks.conversation(services, paul)
    _, trace = successful_turn(client, "Que savez-vous de mes préférences ?")
    loaded = checks.memory(trace).get("loaded") or []
    assert [(e.get("topic"), e.get("value")) for e in loaded] == [("amount_display", "including_tax")]
    stored = checks.stored_text()
    assert "including_tax" in stored and "table" not in stored, "the deletion of one topic reaches the storage"


def test_only_planned_topics_are_kept(services, reset_state):
    checks.only_planned_topics_are_kept(services, CASES["only_planned_topics_are_kept"])


def test_rereads_rather_than_assumes(chat_client, observation):
    checks.rereads_rather_than_assumes(chat_client, observation, CASES["rereads_rather_than_assumes"])
