"""Framework and bootstrap of my-agent: interface health, bootstrap turn and trace, workshop folders."""

import httpx
import pytest

from workshop_tools.cli import WORKSHOP_IDS, workshop_tests_dir, workshop_dir

pytestmark = pytest.mark.shell


def test_interface_health(services):
    r = httpx.get(f"{services['interface']}/health", timeout=5)
    assert r.status_code == 200


def test_users_lists_the_seeded_identities(services):
    from workshop_kit.apps.business_api.seed_data import USERS

    users = httpx.get(f"{services['interface']}/users", timeout=5).json()["users"]
    assert [(u["user_id"], u["role"], u["organization"]) for u in users] == [(u, r, o) for u, _, r, o in USERS]


def test_bootstrap_answers_without_model_nor_tool(chat_client, traces):
    turn = chat_client.turn("Quel est le statut de la commande CMD-1042 de Martin Durand ?")
    assert turn.ok is True
    assert turn.types[-1] == "end" and "text" in turn.types
    assert "CMD-1042" not in turn.text, "the bootstrap asserts nothing about the data"
    (trace,) = traces.all()
    assert trace["tools"] == [] and trace["input"]["message"].startswith("Quel est le statut")
    prompt = trace["input"]["system_prompt"]
    assert prompt and "<!--" not in prompt, "system_prompt.md is loaded without its HTML comments"


def test_bootstrap_is_the_one_recorded_for_check_inert():
    from workshop_tools.cli import bootstrap_changes

    assert bootstrap_changes() == [], "my-agent/ bootstrap changed: regenerate workshop_tests/inert_agent/bootstrap.sha256"


def test_every_workshop_folder_exists():
    missing = [i for i in WORKSHOP_IDS if not workshop_tests_dir(i).is_dir()]
    assert missing == []
    assert all((workshop_dir(i) / "README.md").is_file() for i in WORKSHOP_IDS)
    assert all((workshop_dir(i) / "state.yaml").is_file() for i in WORKSHOP_IDS)

