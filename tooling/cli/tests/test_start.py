"""The cross-platform bootstrap needs only Python's standard library and uv."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("workshop_start", ROOT / "start.py")
start = importlib.util.module_from_spec(spec)
spec.loader.exec_module(start)


def test_bootstrap_syncs_then_serves_from_repo_root(monkeypatch, tmp_path):
    run = Mock(return_value=SimpleNamespace(returncode=0))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VIRTUAL_ENV", "unrelated")
    monkeypatch.setattr(start.shutil, "which", lambda _: "uv")
    monkeypatch.setattr(start.subprocess, "run", run)
    assert start.main(["--port-offset", "10", "--reset-data"]) == 0
    assert run.call_args_list[0].args[0] == ["uv", "sync", "--project", str(start.TOOLS), "--locked"]
    assert run.call_args_list[1].args[0] == [
        "uv", "run", "--project", str(start.TOOLS), "--no-sync", "workshop", "serve", "--port-offset", "10", "--reset-data",
    ]
    assert all(call.kwargs["cwd"] == ROOT for call in run.call_args_list)
    assert all("VIRTUAL_ENV" not in call.kwargs["env"] for call in run.call_args_list)


def test_sync_failure_does_not_start_services(monkeypatch):
    run = Mock(return_value=SimpleNamespace(returncode=2))
    monkeypatch.setattr(start.shutil, "which", lambda _: "uv")
    monkeypatch.setattr(start.subprocess, "run", run)
    assert start.main([]) == 2
    assert run.call_count == 1


def test_missing_uv_is_actionable(monkeypatch, capsys):
    monkeypatch.setattr(start.shutil, "which", lambda _: None)
    assert start.main([]) == 1
    assert "uv is required" in capsys.readouterr().err


@pytest.mark.parametrize("offset", ["-1", "57456"])
def test_invalid_offset_is_rejected(offset):
    with pytest.raises(SystemExit) as exc:
        start.main(["--port-offset", offset])
    assert exc.value.code == 2


def test_ctrl_c_is_handled(monkeypatch):
    monkeypatch.setattr(start.shutil, "which", lambda _: "uv")
    monkeypatch.setattr(start.subprocess, "run", Mock(side_effect=KeyboardInterrupt))
    assert start.main([]) == 130


def test_root_is_not_a_python_project_and_bootstrap_owns_its_dependencies():
    assert not (ROOT / "pyproject.toml").exists()
    assert not (ROOT / "uv.lock").exists()
    assert not (ROOT / "conftest.py").exists()
    assert start.TOOLS == ROOT / "tooling" / "cli"
    assert (start.TOOLS / "pyproject.toml").is_file()
    assert (start.TOOLS / "uv.lock").is_file()