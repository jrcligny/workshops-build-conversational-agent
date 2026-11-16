# Installation

Main target: **Windows**, with the latest stable Python release published on
[python.org](https://www.python.org/downloads/) (Python **3.15**, currently
3.15.2 as of 25 October 2026). Linux and macOS are supported too. The
repository requires Python 3.15 or newer (`requires-python`, `.python-version` file).

## Common requirements

- Python 3.15 or newer, **from python.org** (or from uv / Homebrew), not Apple's
  system Python nor, preferably, the Microsoft Store package
- [uv](https://docs.astral.sh/uv/)

Loading the **sqlite-vec** extension requires an interpreter whose SQLite
allows `enable_load_extension`. This is the case for the official python.org
builds and for the interpreters installed by `uv python install 3.15`. See below
if loading fails.

## Windows (PowerShell)

1. Install Python 3.15 from [python.org](https://www.python.org/downloads/windows/)
   (official **64-bit** installer). Tick **Add python.exe to PATH**.
2. Install uv, in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
```

3. Close and reopen the terminal, then:

```powershell
git clone https://github.com/jrcligny/workshops-build-conversational-agent.git
cd workshops-build-conversational-agent
uv python install 3.15
uv sync --extra dev --python 3.15
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
uv python install 3.15
uv sync --extra dev --python 3.15
cp .env.example .env
uv run pytest tests/kit
uv run workshop check-shell
```

On macOS, do not use `/usr/bin/python3` (often built without SQLite extension
loading). Prefer `uv python install 3.15`, Homebrew (`brew install python@3.15`)
or the python.org installer.

## sqlite-vec: diagnostics

If the document index refuses to start, the error message gives the
interpreter, the SQLite version and the cause. Check:

```powershell
uv run python -c "import sqlite3; print(hasattr(sqlite3.Connection, 'enable_load_extension'), sqlite3.sqlite_version)"
```

The expected values are `True` and a recent SQLite version (3.41 or newer
recommended). Then run `uv sync --python 3.15` again with an official interpreter.

## Check the framework

`uv run workshop check-shell` succeeds if, and only if, every workshop test
**fails** on the empty shell. This is the expected behaviour.

The `.env` file must never be committed. The `AZURE_OPENAI_API_KEY` key stays
empty during design: the `simulated` mode is enough.

## Start the services (optional, to explore by hand)

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
