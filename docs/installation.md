# Installation

Main target: **Windows**, with Python **3.13** from
[python.org](https://www.python.org/downloads/) or uv. Linux and macOS are
supported too. The repository requires Python 3.13 or newer (`requires-python`)
and selects Python 3.13 for development and CI (`.python-version`).

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
uv sync --extra dev --python 3.13
Copy-Item .env.example .env
uv run pytest tests/kit
uv run workshop check-shell
```

The `workshop` command is provided by the project (`uv run workshop ...`). It
uses neither `fork` nor POSIX signals; it works on Windows.

## Linux and macOS

```bash
git clone https://github.com/jrcligny/workshops-build-conversational-agent.git
cd workshops-build-conversational-agent
uv python install 3.13
uv sync --extra dev --python 3.13
cp .env.example .env
uv run pytest tests/kit
uv run workshop check-shell
```

On macOS, do not use `/usr/bin/python3` (often built without SQLite extension
loading). Prefer `uv python install 3.13`, Homebrew (`brew install python@3.13`)
or the python.org installer.

## sqlite-vec: diagnostics

If the document index refuses to start, the error message gives the
interpreter, the SQLite version and the cause. Check:

```powershell
uv run python -c "import sqlite3; print(hasattr(sqlite3.Connection, 'enable_load_extension'), sqlite3.sqlite_version)"
```

The expected values are `True` and a recent SQLite version (3.41 or newer
recommended). Then run `uv sync --python 3.13` again with an official interpreter.

## Check the framework

`uv run workshop check-shell` succeeds if, and only if, every workshop test
**fails** on the empty shell. This is the expected behaviour.

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

The script synchronizes the kit dependencies and runs `uv run workshop serve`.
On Linux/macOS, or when the kit is already installed, use:

```bash
uv run workshop serve
```

The launcher synchronizes the UI's own dependencies, initializes missing
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

Use `uv run workshop serve --port-offset 10` (or `python start.py --port-offset 10`)
to shift **all six** ports by 10 when defaults are occupied. The UI then opens
on port 8090, connected to the conversation API on 8010. Logs are written to
`.workshop/logs/`, one file per service.

To explicitly reset the business dataset and rebuild the index, add
`--reset-data`. **This discards local
business changes.** It is never done automatically on an existing dataset.

### Separate dependencies for each Python project

The root `pyproject.toml`, `uv.lock`, and `.venv` belong to the Python kit.
`workshop_kit/chat-ui/` has its own `pyproject.toml`, `uv.lock`, and `.venv`.
Both use Python 3.13. Their dependencies are not merged: Chainlit requires MCP 1,
while the kit uses MCP 2. They communicate only through HTTP/SSE.

The [UI guide](../workshop_kit/chat-ui/README.md) explains the welcome message,
configuration, and UI-specific tests. The UI does not implement the empty agent.

## Start individual services (advanced)

The automated tests start these services themselves: you do not need to start
them for `workshop check`.

```powershell
uv run uvicorn workshop_kit.apps.business_api.app:app --port 8001
uv run uvicorn workshop_kit.apps.docs_search.app:app --port 8002
uv run uvicorn workshop_kit.llm_proxy.app:app --port 8003
uv run uvicorn workshop_kit.shell.chat_app:app --port 8000
uv run python my-agent/mcp_server.py
```

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
