"""End-to-end tests of workshop 05. They must fail on the empty shell.

Trace contract read here: `tools[]` (`name`, `arguments`, `result.status`). The late filter
is an argument of the tool call: `filter: "late"`, the value used by the business API.
"""

import pytest

from workshop_tests.testing.turns import successful_turn, tool_arguments, tool_result, tool_status, tools

pytestmark = pytest.mark.workshop


def test_namesakes_several_candidates(chat_client):
    turn, trace = successful_turn(chat_client, "Quelles sont les commandes de Léa Martin ?")
    results = " ".join(str(tool_result(c)) for c in tools(trace) if tool_status(c) == "ok")
    assert "C-MARTIN-LILLE" in results and "C-MARTIN-LYON" in results, (
        "the customer search must return every namesake (Lille and Lyon)"
    )
    text = turn.text.lower()
    assert "lille" in text and "lyon" in text, "the answer presents both candidates"
    assert "CMD-2010" not in turn.text, "the agent must not pick one namesake and list its orders on behalf of the user"


def test_late_filter_applied_by_the_tool(chat_client, observation, business_client):
    observation.reset("volume")
    customer = business_client.get("/customers", params={"name": "Transports Morel"}).json()[0]
    expected = business_client.get(f"/customers/{customer['id']}/orders", params={"filter": "late"}).json()["total"]
    turn, trace = successful_turn(chat_client, "Combien de commandes en retard a Transports Morel ?")
    filtered = [c for c in tools(trace) if tool_arguments(c).get("filter") == "late"]
    assert filtered, "the late filter is an argument of the tool call (filter: \"late\"), not a selection made by the model"
    result = tool_result(filtered[-1])
    assert expected in (result.get("total"), result.get("count")), "result.total (or result.count) is the number of late orders"
    assert str(expected) in turn.text, f"the answer must give the number of late orders read from the tool ({expected})"
