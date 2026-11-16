"""Private tests of workshop 05 (not given to students): same criteria, other inputs.

Another pair of namesakes (Hugo Petit, Bordeaux and Strasbourg) and the late filter on another
customer, whose expected total (read from the API) is not the public one.
"""

import pytest

from workshop_tests.testing.turns import successful_turn, tool_arguments, tool_result, tool_status, tools

pytestmark = pytest.mark.workshop


def test_namesakes_several_candidates(chat_client):
    turn, trace = successful_turn(chat_client, "Je voudrais voir les commandes du client Hugo Petit.")
    results = " ".join(str(tool_result(c)) for c in tools(trace) if tool_status(c) == "ok")
    assert "C-PETIT-BORDEAUX" in results and "C-PETIT-STRASBOURG" in results, (
        "the customer search must return every namesake (Bordeaux and Strasbourg)"
    )
    text = turn.text.lower()
    assert "bordeaux" in text and "strasbourg" in text, "the answer presents both candidates"
    assert "CMD-3105" not in turn.text and "CMD-3110" not in turn.text, (
        "the agent must not pick one namesake and list its orders on behalf of the user"
    )


@pytest.mark.parametrize("dataset", ["standard", "volume"])
def test_late_filter_applied_by_the_tool(chat_client, observation, business_client, dataset):
    observation.reset(dataset)
    customer = business_client.get("/customers", params={"name": "Martin Durand"}).json()[0]
    expected = business_client.get(f"/customers/{customer['id']}/orders", params={"filter": "late"}).json()["total"]
    turn, trace = successful_turn(chat_client, "Martin Durand a-t-il des commandes en retard ? Combien ?")
    filtered = [c for c in tools(trace) if tool_arguments(c).get("filter") == "late"]
    assert filtered, "the late filter is an argument of the tool call (filter: \"late\"), not a selection made by the model"
    result = tool_result(filtered[-1])
    assert expected in (result.get("total"), result.get("count")), "result.total (or result.count) is the number of late orders"
    text = turn.text.lower()
    assert str(expected) in text or (expected == 0 and "aucune" in text), (
        f"the answer must give the number of late orders read from the tool ({expected})"
    )
    assert "CMD-1042" not in turn.text, "a delivered order is not presented as late"
