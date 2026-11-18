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
        "uv", "run", "--project", str(start.TOOLS), "--no-sync", "python", "-m", "workshop_tools",
        "serve", "--port-offset", "10", "--reset-data",
    ]
    assert all(call.kwargs["cwd"] == ROOT for call in run.call_args_list)
    assert all("VIRTUAL_ENV" not in call.kwargs["env"] for call in run.call_args_list)
    pythonpath = run.call_args_list[1].kwargs["env"]["PYTHONPATH"].split(start.os.pathsep)
    assert pythonpath[: len(start.SOURCE_ROOTS)] == [str(path) for path in start.SOURCE_ROOTS]


def test_source_roots_do_not_depend_on_editable_pth_files():
    """start.py, the launcher and pytest share one list of import roots, independent of `.pth` files."""
    import tomllib

    from workshop_tools import devstack

    assert start.SOURCE_ROOTS == devstack.SOURCE_ROOTS
    assert all(path.is_dir() for path in start.SOURCE_ROOTS)
    config = tomllib.loads((start.TOOLS / "pyproject.toml").read_text(encoding="utf-8"))
    pythonpath = config["tool"]["pytest"]["ini_options"]["pythonpath"]
    assert [(start.TOOLS / p).resolve() for p in pythonpath] == start.SOURCE_ROOTS


def test_hidden_pth_files_are_unhidden(monkeypatch, tmp_path):
    hidden = 0x8000
    site = tmp_path / ".venv" / "lib" / "python3.13" / "site-packages"
    site.mkdir(parents=True)
    (site / "_editable_impl_workshop_tools.pth").write_text("/src\n")
    (site / "visible.pth").write_text("/src\n")
    flags = {"_editable_impl_workshop_tools.pth": hidden | 1, "visible.pth": 0}
    real_lstat = Path.lstat
    monkeypatch.setattr(start.stat, "UF_HIDDEN", hidden, raising=False)
    monkeypatch.setattr(
        Path, "lstat", lambda self: SimpleNamespace(st_flags=flags.get(self.name, 0)) if self.name in flags else real_lstat(self)
    )
    chflags = Mock()
    monkeypatch.setattr(start.os, "chflags", chflags, raising=False)
    assert start.unhide_pth_files([tmp_path]) == [site / "_editable_impl_workshop_tools.pth"]
    chflags.assert_called_once_with(site / "_editable_impl_workshop_tools.pth", 1)


@pytest.mark.parametrize(
    "folder, expected",
    [
        ("/Users/me/Library/Mobile Documents/com~apple~CloudDocs/Téléchargements/repo", True),
        ("/Users/me/Library/CloudStorage/OneDrive-Perso/repo", True),
        ("/Users/me/workshops/repo", False),
    ],
)
def test_cloud_synced_folder_is_explained(capsys, folder, expected):
    assert start.cloud_synced(Path(folder)) is expected
    start.warn_about_hidden_pth([], Path(folder))
    err = capsys.readouterr().err
    assert ("Move the repository outside iCloud Drive" in err) is expected
    assert ("Troubleshooting" in err) is expected


def test_hidden_pth_outside_cloud_is_reported(capsys):
    start.warn_about_hidden_pth([Path("x.pth")], Path("/Users/me/workshops/repo"))
    assert "Cleared the hidden flag on 1" in capsys.readouterr().err


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