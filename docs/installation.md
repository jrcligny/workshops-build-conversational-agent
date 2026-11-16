# Installation

Main target: **Windows**, with Python **3.13** from
[python.org](https://www.python.org/downloads/) or uv. Linux and macOS are
supported too. The Python projects require Python 3.13 or newer (`requires-python`).
The six applications and the test project select Python 3.13 using their own
`.python-version` files. There is no root `pyproject.toml`, `uv.lock`,
`conftest.py` or `.python-version`; run the commands below from the repository root
with an explicit project. The root `ruff.toml` is editor/static configuration only.

## Common requirements

- Python 3.13, **from python.org** (or from uv / Homebrew), not Apple's
  system Python nor, preferably, the Microsoft Store package
- [uv](https://docs.astral.sh/uv/)

Loading the **sqlite-vec** extension requires an interpreter whose SQLite
allows `enable_load_extension`. This is the case for the official python.org
builds and for the interpreters installed by `uv python install 3.13`. See below
if loading fails.

## Windows (PowerShell)

1. Install Python 3.13 from [python.org](https://www.python.org/downloads/windows/)
   (official **64-bit** installer). Tick **Add python.exe to PATH**.
2. Install uv, in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
```

3. Close and reopen the terminal, then:

```powershell
git clone https://github.com/jrcligny/workshops-build-conversational-agent.git
cd workshops-build-conversational-agent
uv python install 3.13
uv sync --project tooling/cli --locked --python 3.13
uv sync --project workshop_tests --locked --python 3.13
Copy-Item .env.example .env
uv run --project workshop_tests pytest -c workshop_tests/pyproject.toml agent_sdk business gateway tooling workshop_tests
uv run --project tooling/cli workshop check-bootstrap
```

The `workshop` command is provided by the tooling project
(`uv run --project tooling/cli workshop ...`). It uses neither `fork` nor
POSIX signals; it works on Windows. Its check commands delegate to the separate
test project's environment and pytest configuration.

## Linux and macOS

```bash
git clone https://github.com/jrcligny/workshops-build-conversational-agent.git
cd workshops-build-conversational-agent
uv python install 3.13
uv sync --project tooling/cli --locked --python 3.13
uv sync --project workshop_tests --locked --python 3.13
cp .env.example .env
uv run --project workshop_tests pytest -c workshop_tests/pyproject.toml agent_sdk business gateway tooling workshop_tests
uv run --project tooling/cli workshop check-bootstrap
```

On macOS, do not use `/usr/bin/python3` (often built without SQLite extension
loading). Prefer `uv python install 3.13`, Homebrew (`brew install python@3.13`)
or the python.org installer.

## sqlite-vec: diagnostics

If the document index refuses to start, the error message gives the
interpreter, the SQLite version and the cause. Check:

```powershell
uv run --project business/docs_search python -c "import sqlite3; print(hasattr(sqlite3.Connection, 'enable_load_extension'), sqlite3.sqlite_version)"
```

The expected values are `True` and a recent SQLite version (3.41 or newer
recommended). Then run
`uv sync --project business/docs_search --locked --python 3.13` again
with an official interpreter (or select `workshop_tests` if the failure is in tests).

## Check the framework

`uv run --project tooling/cli workshop check-bootstrap` succeeds if, and only if, every workshop test
**fails** on the bootstrap of `my-agent/`, except those listed in `workshop_tests/bootstrap_passes.txt`
(the bootstrap already converses through the model). This is the expected behaviour.

The `.env` file must never be committed. The `AZURE_OPENAI_API_KEY` key stays
empty during design: the `simulated` mode is enough.

## Start the complete environment

The French Chainlit chat is a standard component, not an optional extra. Start
all six services with the same Python script on Windows and Linux:

```powershell
python start.py
```

On Linux, use `python3 start.py` if needed. Only Python and uv need to be
installed beforehand; the script uses the standard library and does not require
an activated virtual environment. It works from any directory when given its
absolute path. `--port-offset 10` and `--reset-data` work on both platforms.

The script synchronizes only `tooling/cli/` with its lockfile, then runs
`uv run --project tooling/cli --no-sync workshop serve`. It never installs
test dependencies. Alternatively, from the repository root on any supported OS:

```bash
uv run --project tooling/cli workshop serve
```

The launcher synchronizes each application's own dependencies, initializes missing
databases, checks readiness, and prints the chat URL. Existing business data
and document indexes are preserved. **Ctrl+C** stops all processes started by
the launcher; unrelated processes are never reused or stopped.

| Component | Default address |
|---|---|
| Conversation API | <http://127.0.0.1:8000> |
| Business API | <http://127.0.0.1:8001> |
| Document search | <http://127.0.0.1:8002> |
| Model proxy | <http://127.0.0.1:8003> |
| MCP | <http://127.0.0.1:8004/mcp> |
| Chainlit UI | <http://127.0.0.1:8080> |

Use `uv run --project tooling/cli workshop serve --port-offset 10` (or `python start.py --port-offset 10`)
to shift **all six** ports by 10 when defaults are occupied. The UI then opens
on port 8090, connected to the conversation API on 8010. Logs are written to
`.workshop/logs/`, one file per service.

To explicitly reset the business dataset and rebuild the index, add
`--reset-data`. **This discards local
business changes.** It is never done automatically on an existing dataset.

### Separate dependencies for each Python project

Every application has its own `pyproject.toml`, `uv.lock`, `.python-version`
and `.venv`. There is no shared application environment or uv workspace lock:

| Application | Python project |
|---|---|
| Business API | `business/business_api/` |
| Document search | `business/docs_search/` |
| Model proxy | `gateway/model_gateway/` |
| Conversation API | `gateway/agent_gateway/` |
| MCP tools server | `my-agent/` |
| Chainlit UI | `clients/chat_ui/` |

All six select Python 3.13. The launcher synchronizes their lockfiles with
`uv sync --project <path> --locked`, then starts each with its own interpreter.
Shared source imports are resolved using the repository on `PYTHONPATH`, not by
installing the test project's combined dependencies into the services.
Database initialization also runs in the owning application's environment.

Tooling and tests are two additional, separate projects, not a root package:

- `tooling/cli/` owns the CLI and launcher under `src/workshop_tools/`, with
  its own `pyproject.toml`, `uv.lock` and `.venv`.
- `workshop_tests/` owns test dependencies and pytest configuration in its
  `pyproject.toml` (`package = false`), plus its own `uv.lock`, `.venv` and
  `.python-version`. It depends on the local `workshop-tools` project in editable
  mode. Its `testing/` and `evaluation/` folders provide shared fixtures and helpers.

Infrastructure tests live next to the component they test (`<component>/tests/`, `workshop_tests/tests/`, `workshop_tests/integration/`), while workshop acceptance
tests stay next to their guides. Chainlit's MCP 1 and the agent's MCP 2 remain
isolated; UI tests use the UI project's `dev` extra, not `workshop_tests/`.

Run the infrastructure suite from the repository root:

```powershell
uv run --project workshop_tests pytest -c workshop_tests/pyproject.toml agent_sdk business gateway tooling workshop_tests
```

The `-c` explicitly selects the test project's configuration and fixture plugin;
there is no root pytest configuration or fixture file. See the
[test environment guide](../workshop_tests/README.md) for evaluation commands.

To validate real startup and automatic shutdown of all six projects, run
`uv run --project tooling/cli workshop serve --check --port-offset 100`.
CI runs this on Windows/Linux.

The [UI guide](../clients/chat_ui/README.md) explains the welcome message,
configuration, and UI-specific tests. The UI does not implement the empty agent.

## Start individual services (advanced)

The automated tests start these services themselves: you do not need to start
them for `workshop check`.

```powershell
$env:PYTHONPATH = (Get-Location).Path
uv run --project business/business_api uvicorn business_api.app:app --port 8001
uv run --project business/docs_search uvicorn docs_search.app:app --port 8002
uv run --project gateway/model_gateway uvicorn model_gateway.app:app --port 8003
uv run --project gateway/agent_gateway uvicorn agent_gateway.chat_app:app --port 8000
uv run --project my-agent python my-agent/mcp_server.py
```

Run each command in a separate terminal from the repository root. In bash,
replace the first line with `export PYTHONPATH="$PWD"`. Prefer the complete-stack
launcher: it also initializes missing databases and sets service URLs.

Reset the dataset (PowerShell; in bash or zsh, replace the trailing backtick
with a backslash):

```powershell
curl -X POST http://127.0.0.1:8001/observation/reset `
  -H "Authorization: Bearer workshop-observation" `
  -H "Content-Type: application/json" `
  -d '{"dataset": "standard"}'
```

Then rebuild the document index:

```powershell
curl -X POST http://127.0.0.1:8002/indexing/rebuild `
  -H "Authorization: Bearer workshop-observation" `
  -H "Content-Type: application/json" `
  -d '{"include_retired": false}'
```
