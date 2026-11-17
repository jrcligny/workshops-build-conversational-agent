import pytest

from testkit.chat_client import Turn
from testkit.expect import (
    called_with,
    expect_event,
    expect_no_event,
    mentions_all,
    mentions_any,
    mentions_none,
    no_tool_called,
    state_of,
)


def turn(text: str, events=()) -> Turn:
    return Turn(events=list(events), text=text, ok=True, error=None)


def test_case_and_accents_are_folded_by_default():
    mentions_any(turn("La commande est LIVREE."), ["livrée"])
    mentions_all("Léa Martin, Lille", ["lea martin", "LILLE"])
    with pytest.raises(AssertionError, match=r"the order stays hidden: found \['expédiée'\]"):
        mentions_none("commande expediee", ["expédiée"], "the order stays hidden")


def test_strict_compares_exact_substrings():
    mentions_all("Voir CMD-1042", ["CMD-1042"], strict=True)
    with pytest.raises(AssertionError, match=r"missing \['CMD-1042'\]"):
        mentions_all("voir cmd-1042", ["CMD-1042"], strict=True)
    mentions_none("voir cmd-1042", "CMD-1042", strict=True)


def test_failure_message_shows_the_criterion_and_the_answer():
    with pytest.raises(AssertionError) as error:
        mentions_any("Je ne sais pas.", ["livrée", "delivered"], "the answer gives the status")
    assert str(error.value) == "the answer gives the status: none of ['livrée', 'delivered'] in 'Je ne sais pas.'"


def test_events_and_tool_calls():
    t = turn("ok", [("mention", {"content": "partiel"}), ("step", {"tool": "x"})])
    assert expect_event(t, "compaction", "mention") == [{"content": "partiel"}]
    with pytest.raises(AssertionError, match="no interruption event"):
        expect_event(t, "interruption")
    with pytest.raises(AssertionError, match="step"):
        expect_no_event(t, "step")
    trace = {"tools": [{"name": "get_order", "arguments": {"reference": "CMD-1042"}}]}
    assert called_with(trace, "CMD-1042")
    with pytest.raises(AssertionError, match="get_order"):
        no_tool_called(trace)
    with pytest.raises(AssertionError, match="trace.state"):
        state_of({"state": {}})
