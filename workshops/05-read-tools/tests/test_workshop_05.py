"""End-to-end tests of workshop 05. They must fail on the empty shell."""

import pytest

from workshop_kit.testing.turns import successful_turn, tools

pytestmark = pytest.mark.workshop


def test_namesakes_several_candidates(chat_client):
    turn, trace = successful_turn(chat_client, "Quelles sont les commandes de Léa Martin ?")
    text = turn.text.lower()
    assert "lille" in text and "lyon" in text
    # the agent does not pick one of the two on behalf of the user
    assert "laquelle" in text or "plusieurs" in text or "homonym" in text or "deux" in text or "?" in turn.text
    assert tools(trace)


def test_late_filter_applied_by_the_tool(chat_client, observation):
    observation.reset("volume")
    turn, trace = successful_turn(chat_client, "Quelles sont les commandes en retard de Transports Morel ?")
    assert turn.text
    assert tools(trace)
    assert "late" in str(tools(trace)).lower()
    # the filter is in the call, not only in a selection made afterwards by the model
    assert any("late" in str(t.get("arguments") or t.get("parameters") or t).lower() for t in tools(trace))
