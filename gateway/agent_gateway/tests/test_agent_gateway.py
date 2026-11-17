"""Agent gateway: health and test identities."""

import httpx
import pytest

pytestmark = pytest.mark.shell


def test_interface_health(services):
    r = httpx.get(f"{services['interface']}/health", timeout=5)
    assert r.status_code == 200


def test_users_lists_the_seeded_identities(services):
    from business_api.seed_data import USERS

    users = httpx.get(f"{services['interface']}/users", timeout=5).json()["users"]
    assert [(u["user_id"], u["role"], u["organization"]) for u in users] == [(u, r, o) for u, _, r, o in USERS]


def test_model_calls_of_a_turn_are_saved_under_the_conversation(chat_client):
    from model_gateway import calls

    conversation_id = chat_client.open()
    chat_client.turn("Bonjour")
    chat_client.turn("Merci")
    saved = calls.calls(conversation_id)
    assert saved, "the bootstrap calls the model through the proxy"
    assert [c["turn"] for c in saved][0] == 1 and saved[-1]["turn"] == 2
    assert saved[-1]["request"]["messages"][-1] == {"role": "user", "content": "Merci"}
