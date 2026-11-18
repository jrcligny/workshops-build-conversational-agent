#!/usr/bin/env python3
"""Cross-platform bootstrap: stdlib only, works before the kit is installed."""

import argparse
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tooling" / "cli"
# Same list as `workshop_tools.devstack.SOURCE_ROOTS` and the pytest `pythonpath`:
# imports must not depend on the editable `.pth` files, which Python skips when hidden.
SOURCE_ROOTS = [
    ROOT / "tooling" / "cli" / "src",
    ROOT / "agent_sdk" / "src",
    ROOT / "agent_testkit" / "src",
    ROOT / "shared" / "workshop_config" / "src",
    ROOT / "shared" / "text_vectors" / "src",
    ROOT / "business" / "business_api" / "src",
    ROOT / "business" / "docs_search" / "src",
    ROOT / "gateway" / "agent_gateway" / "src",
    ROOT / "gateway" / "model_gateway" / "src",
    ROOT / "clients" / "chat_ui" / "src",
]
CLOUD_MARKERS = ("/Library/Mobile Documents/", "/Library/CloudStorage/")
VENV_PROJECTS = [
    TOOLS,
    ROOT / "business" / "business_api",
    ROOT / "business" / "docs_search",
    ROOT / "gateway" / "model_gateway",
    ROOT / "gateway" / "agent_gateway",
    ROOT / "my-agent",
    ROOT / "clients" / "chat_ui",
]


def cloud_synced(root: Path = ROOT) -> bool:
    """iCloud Drive (and other macOS File Provider folders) may mark files in `.venv` as hidden."""
    return any(marker in f"{root.as_posix()}/" for marker in CLOUD_MARKERS)


def unhide_pth_files(projects: list[Path] = VENV_PROJECTS) -> list[Path]:
    """Clears the macOS hidden flag on the `.pth` files of the repository's `.venv` folders.

    Python 3.12+ silently skips hidden `.pth` files, which breaks editable installs
    (`ModuleNotFoundError: No module named 'workshop_tools'`)."""
    hidden_flag = getattr(stat, "UF_HIDDEN", 0)
    cleared = []
    if not hidden_flag:
        return cleared
    for pth in (p for project in projects for p in (project / ".venv").glob("lib/python*/site-packages/*.pth")):
        try:
            flags = getattr(pth.lstat(), "st_flags", 0)
            if flags & hidden_flag:
                os.chflags(pth, flags & ~hidden_flag)
                cleared.append(pth)
        except OSError:
            continue
    return cleared


def warn_about_hidden_pth(cleared: list[Path], root: Path = ROOT) -> None:
    if not cleared and not cloud_synced(root):
        return
    lines = ["", "Warning: macOS can mark the files of `.venv` as hidden in this folder."]
    if cleared:
        lines.append(f"Cleared the hidden flag on {len(cleared)} `.pth` file(s); Python 3.12+ ignores hidden `.pth` files.")
    if cloud_synced(root):
        lines.append(f"This folder is synchronized by iCloud Drive or another cloud provider: {root}")
    lines += [
        "`python start.py` and `workshop check` do not depend on these files, but a manual",
        "`uv run --project tooling/cli workshop ...` may fail with",
        "`ModuleNotFoundError: No module named 'workshop_tools'`.",
        "Move the repository outside iCloud Drive (for example to ~/workshops) and run `python start.py` again.",
        "See README.md, section Troubleshooting.",
        "",
    ]
    print("\n".join(lines), file=sys.stderr)


def source_env(env: dict[str, str]) -> dict[str, str]:
    paths = [str(path) for path in SOURCE_ROOTS]
    if env.get("PYTHONPATH"):
        paths.append(env["PYTHONPATH"])
    return {**env, "PYTHONPATH": os.pathsep.join(paths)}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install and start all workshop services.")
    parser.add_argument("--port-offset", type=int, default=0, help="Shift all six default ports")
    parser.add_argument("--reset-data", action="store_true", help="Discard existing business data and rebuild the index")
    args = parser.parse_args(argv)
    if not 0 <= args.port_offset <= 57455:
        parser.error("--port-offset must be between 0 and 57455")
    uv = shutil.which("uv")
    if uv is None:
        print("uv is required. Install it from https://docs.astral.sh/uv/", file=sys.stderr)
        return 1
    # Do not let an unrelated active environment influence project selection.
    env = source_env({key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"})
    sync = [uv, "sync", "--project", str(TOOLS), "--locked"]
    # `python -m` rather than the `workshop` script: imports resolve through PYTHONPATH.
    serve = [uv, "run", "--project", str(TOOLS), "--no-sync", "python", "-m", "workshop_tools",
             "serve", "--port-offset", str(args.port_offset)]
    if args.reset_data:
        serve.append("--reset-data")
    try:
        result = subprocess.run(sync, cwd=ROOT, env=env, check=False)
        if result.returncode:
            return result.returncode
        warn_about_hidden_pth(unhide_pth_files())
        return subprocess.run(serve, cwd=ROOT, env=env, check=False).returncode
    except KeyboardInterrupt:
        # The foreground launcher also receives Ctrl+C and stops its services.
        return 130
    except OSError as exc:
        print(f"Cannot start the workshop: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())