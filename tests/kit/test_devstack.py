"""The local launcher owns all six services, but never pre-existing processes."""

import socket
import sqlite3
import subprocess
import sys
from unittest.mock import Mock

import pytest

from workshop_kit import cli, devstack


def test_each_project_uses_its_own_environment():
    stack = devstack.services(10)
    assert [s.name for s in stack] == ["business_api", "docs_search", "proxy", "mcp", "interface", "chat_ui"]
    assert [s.port for s in stack] == [8011, 8012, 8013, 8014, 8010, 8090]
    for service in stack[:-1]:
        assert service.command[0] == sys.executable
        assert service.cwd == devstack.REPO_ROOT
    ui = stack[-1]
    assert ui.cwd == devstack.UI_ROOT
    assert str(devstack.UI_ROOT / ".venv") in ui.command[0]
    assert "chainlit" in ui.command
    assert ui.env["CHAINLIT_APP_ROOT"] == str(devstack.UI_ROOT)
    assert ui.env["WORKSHOP_CHAT_BACKEND_URL"] == "http://127.0.0.1:8010"
    assert stack[3].env["MCP_PORT"] == "8014"


@pytest.mark.parametrize("offset", [-1, 57456])
def test_invalid_port_offset(offset):
    with pytest.raises(ValueError):
        devstack.services(offset)


def test_preexisting_listener_is_not_reused_or_stopped():
    with socket.socket() as sock:
        sock.bind((devstack.HOST, 0))
        sock.listen()
        port = sock.getsockname()[1]
        service = devstack.Service("existing", port, (), devstack.REPO_ROOT, {})
        with pytest.raises(RuntimeError, match="No existing service was stopped"):
            devstack.check_ports([service])
        # The listener still works after the failed check.
        with socket.create_connection((devstack.HOST, port), timeout=1):
            pass


def test_missing_database_check_does_not_create_it(tmp_path):
    path = tmp_path / "data.db"
    assert devstack._has_table(path, "users") is False
    assert not path.exists()
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE users (id TEXT)")
    assert devstack._has_table(path, "users") is True
    assert devstack._has_table(path, "passages") is False


def test_database_initialization_preserves_existing_work(monkeypatch, tmp_path):
    from workshop_kit.apps.business_api import seed_data
    from workshop_kit.apps.docs_search import indexing
    from workshop_kit.shell.config import settings

    load = Mock()
    rebuild = Mock()
    monkeypatch.setattr(seed_data, "load_dataset", load)
    monkeypatch.setattr(indexing, "rebuild", rebuild)
    monkeypatch.setattr(settings, "business_api_db", str(tmp_path / "business.db"))
    monkeypatch.setattr(settings, "docs_search_db", str(tmp_path / "docs.db"))
    monkeypatch.setattr(devstack, "_has_table", lambda *_: True)
    devstack.initialize_data()
    load.assert_not_called()
    rebuild.assert_not_called()
    devstack.initialize_data(reset=True)
    load.assert_called_once_with("standard")
    rebuild.assert_called_once_with()
    load.reset_mock()
    rebuild.reset_mock()
    monkeypatch.setattr(devstack, "_has_table", lambda *_: False)
    devstack.initialize_data()
    load.assert_called_once_with("standard")
    rebuild.assert_called_once_with()


def test_startup_failure_stops_only_started_processes_in_reverse_order(monkeypatch, tmp_path):
    processes = [Mock(), Mock()]
    stopped = []
    monkeypatch.setattr(devstack, "LOGS", tmp_path)
    monkeypatch.setattr(devstack.subprocess, "Popen", Mock(side_effect=processes))
    monkeypatch.setattr(devstack, "wait_ready", Mock(side_effect=[None, RuntimeError("failed startup")]))
    monkeypatch.setattr(devstack, "stop_process", stopped.append)
    with pytest.raises(RuntimeError, match="failed startup"):
        devstack.supervise(devstack.services())
    assert stopped == list(reversed(processes))


def test_keyboard_interrupt_stops_all_owned_processes(monkeypatch, tmp_path):
    stack = devstack.services()
    processes = [Mock(poll=Mock(return_value=None)) for _ in stack]
    stopped = []
    monkeypatch.setattr(devstack, "LOGS", tmp_path)
    monkeypatch.setattr(devstack.subprocess, "Popen", Mock(side_effect=processes))
    monkeypatch.setattr(devstack, "wait_ready", Mock())
    monkeypatch.setattr(devstack, "stop_process", stopped.append)
    tick = Mock()
    tick.wait.side_effect = KeyboardInterrupt
    monkeypatch.setattr(devstack.threading, "Event", lambda: tick)
    assert devstack.supervise(stack) == 0
    assert stopped == list(reversed(processes))


def test_stop_escalates_only_when_needed():
    process = Mock(poll=Mock(return_value=None))
    process.wait.side_effect = [subprocess.TimeoutExpired("service", 10), None]
    devstack.stop_process(process)
    process.terminate.assert_called_once_with()
    process.kill.assert_called_once_with()
    dead = Mock(poll=Mock(return_value=0))
    devstack.stop_process(dead)
    dead.terminate.assert_not_called()


def test_ports_are_checked_before_sync_initialization_or_start(monkeypatch):
    sync = Mock()
    init = Mock()
    supervise = Mock()
    monkeypatch.setattr(devstack, "check_ports", Mock(side_effect=RuntimeError("occupied")))
    monkeypatch.setattr(devstack.subprocess, "run", sync)
    monkeypatch.setattr(devstack, "initialize_data", init)
    monkeypatch.setattr(devstack, "supervise", supervise)
    assert devstack.serve() == 1
    sync.assert_not_called()
    init.assert_not_called()
    supervise.assert_not_called()


def test_serve_syncs_ui_project_before_start(monkeypatch):
    sync = Mock()
    init = Mock()
    supervise = Mock(return_value=0)
    monkeypatch.setattr(devstack, "check_ports", Mock())
    monkeypatch.setattr(devstack.shutil, "which", lambda _: "uv")
    monkeypatch.setattr(devstack.subprocess, "run", sync)
    monkeypatch.setattr(devstack, "initialize_data", init)
    monkeypatch.setattr(devstack, "supervise", supervise)
    assert devstack.serve(10, reset_data=True) == 0
    sync.assert_called_once()
    assert sync.call_args.args[0] == ["uv", "sync", "--project", str(devstack.UI_ROOT), "--locked"]
    assert sync.call_args.kwargs["cwd"] == devstack.REPO_ROOT
    assert sync.call_args.kwargs["check"] is True
    assert "VIRTUAL_ENV" not in sync.call_args.kwargs["env"]
    init.assert_called_once_with(True)
    assert supervise.call_args.args[0][-1].port == 8090


def test_cli_exposes_full_stack_command(monkeypatch):
    serve = Mock(return_value=0)
    monkeypatch.setattr(devstack, "serve", serve)
    assert cli.main(["serve", "--port-offset", "10", "--reset-data"]) == 0
    serve.assert_called_once_with(10, True)