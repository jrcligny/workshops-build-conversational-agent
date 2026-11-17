"""Written conversations (`conversation:` in the workshop cases): converted to chat messages, loaded
through the gateway, and consistent with the business application they claim to have read."""

from pathlib import Path

import httpx
import pytest
import yaml

from workshop_tests.testing.conversation import to_messages, tool_results

pytestmark = pytest.mark.shell

WORKSHOPS = Path(__file__).resolve().parents[2] / "workshops"
SAMPLE = [
    {
        "user": "Où en est la commande CMD-2010 ?",
        "tools": [{"name": "get_order", "arguments": {"reference": "CMD-2010"}, "result": {"status": "ok", "order": {"reference": "CMD-2010", "status": "shipped"}}}],
        "answer": "La commande CMD-2010 est expédiée.",
    },
    {"user": "Merci.", "answer": "Avec plaisir."},
]


def _written_conversations():
    found = []

    def walk(node, where):
        if isinstance(node, dict):
            if isinstance(node.get("conversation"), list):
                found.append(pytest.param(node["conversation"], node.get("dataset", "standard"), id=where))
            for key, value in node.items():
                walk(value, f"{where}:{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{where}[{index}]")

    for path in sorted(WORKSHOPS.glob("*/tests/cases*.yaml")):
        walk(yaml.safe_load(path.read_text(encoding="utf-8")) or {}, f"{path.parent.parent.name}/{path.name}")
    return found


def test_written_turns_become_linked_chat_messages():
    messages = to_messages(SAMPLE)
    assert [m["role"] for m in messages] == ["user", "assistant", "tool", "assistant", "user", "assistant"]
    call = messages[1]["tool_calls"][0]
    assert call["id"] == messages[2]["tool_call_id"] == "call_1_1" and call["function"]["name"] == "get_order"
    assert '"shipped"' in messages[2]["content"]
    assert tool_results(SAMPLE)[0]["turn"] == 1


def test_loaded_history_becomes_the_context_and_the_transcript(services, chat_client):
    from agent_sdk.context import context

    assert chat_client.load(SAMPLE) == 2
    ctx = context(chat_client.conversation_id)
    assert ctx.messages == to_messages(SAMPLE) and ctx.summary == ""
    unknown = httpx.post(f"{services['interface']}/conversations/nope/history", json={"messages": []}, timeout=5)
    assert unknown.status_code == 404


def _same_fields(written: dict, actual: dict, what: str) -> None:
    for key, value in written.items():
        if key in actual:
            assert actual[key] == value, f"{what}: written {key}={value!r}, business application {actual[key]!r}"


@pytest.mark.parametrize("conversation,dataset", _written_conversations())
def test_written_tool_results_match_the_business_application(business_client, observation, conversation, dataset):
    observation.reset(dataset)
    for call in tool_results(conversation):
        name, args, result = call["name"], call["arguments"], call["result"] or {}
        what = f"turn {call['turn']} {name}({args})"
        if name == "get_order":
            r = business_client.get(f"/orders/{args['reference']}")
            if result.get("status") == "not_found":
                assert r.status_code == 404, what
            else:
                assert r.status_code == 200, what
                _same_fields(result.get("order") or {}, r.json(), what)
        elif name == "search_customers":
            found = {c["id"]: c for c in business_client.get("/customers", params={"name": args["name"]}).json()}
            written = result.get("customers") or []
            assert {c["id"] for c in written} == set(found), what
            for customer in written:
                _same_fields(customer, found[customer["id"]], what)
        elif name == "list_orders":
            params = {k: v for k, v in args.items() if k != "customer_id"}
            listed = business_client.get(f"/customers/{args['customer_id']}/orders", params=params).json()
            orders = {o["reference"]: o for o in listed["orders"]}
            for order in result.get("orders") or []:
                assert order["reference"] in orders, what
                _same_fields(order, orders[order["reference"]], what)
            if "total" in result:
                assert result["total"] == listed["total"], what
        else:
            pytest.fail(f"{what}: unknown neutral tool (get_order, search_customers, list_orders)")
