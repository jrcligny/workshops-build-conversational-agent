# Workshop tooling

This Python project provides the `workshop` command and the six-service launcher.
Source lives in `src/workshop_tools/cli.py` and `src/workshop_tools/devstack.py`.
It owns its `pyproject.toml`, `uv.lock` and `.venv`; there is no root Python project.

Run from the repository root:

```powershell
uv sync --project workshop_kit/bootstrap --locked --python 3.13
uv run --project workshop_kit/bootstrap workshop serve
uv run --project workshop_kit/bootstrap workshop start 03
```

`python start.py` is a standard-library-only bootstrap: it synchronizes this
project and invokes `workshop serve`, never installing test dependencies. The
launcher synchronizes each of the six application projects independently with
its own lockfile and environment. Ctrl+C stops only the services it started.

Workshop checks delegate to the separate [test environment](../../workshop_tests/README.md).
Prepare it before checking:

```powershell
uv sync --project workshop_tests --locked --python 3.13
uv run --project workshop_kit/bootstrap workshop check 03
uv run --project workshop_kit/bootstrap workshop check 07 --non-regression
uv run --project workshop_kit/bootstrap workshop check-shell
```

Acceptance tests stay red until the workshop is implemented; `check-shell`
succeeds when every workshop test fails on the empty shell. See
[installation](../../docs/installation.md) for service options and ports.