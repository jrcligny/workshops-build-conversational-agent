"""Framework and empty shell: interface health, explicit shell error, workshop folders."""

import httpx
import pytest

from workshop_tools.cli import WORKSHOP_IDS, workshop_tests_dir, workshop_dir

pytestmark = pytest.mark.shell


def test_interface_health(services):
    r = httpx.get(f"{services['interface']}/health", timeout=5)
    assert r.status_code == 200


def test_shell_returns_an_explicit_error(chat_client):
    turn = chat_client.turn("Quel est le statut de la commande CMD-1042 de Martin Durand ?")
    assert turn.ok is False
    assert turn.error
    assert "workshop 03" in turn.error.lower() or "system prompt" in turn.error.lower()
    assert "end" in turn.types


def test_every_workshop_folder_exists():
    missing = [i for i in WORKSHOP_IDS if not workshop_tests_dir(i).is_dir()]
    assert missing == []
    assert all((workshop_dir(i) / "README.md").is_file() for i in WORKSHOP_IDS)
    assert all((workshop_dir(i) / "state.yaml").is_file() for i in WORKSHOP_IDS)


def test_no_trace_on_the_shell(chat_client, traces):
    chat_client.turn("bonjour")
    assert traces.all() == []
