# Workshops — Build a Conversational Agent

Companion repository for the workshops of the book *De l'assistant à l'agent : anatomie d'un agent conversationnel* (written in French).

**Languages: code and docs in English, the agent converses in French.** Everything in this repository is in English except what the agent's user reads or types: the user turns and expected answers in the tests, the simulated model replies, the corpus texts and the display labels of business values. Details in [docs/decisions.md](docs/decisions.md#language).

It provides the environment and the end-to-end tests to carry out the workshops (chapters 3 to 19, chapter 10 being split into 10a to 10d). **It does not contain the agent's code**: you build your own in `my-agent/`, starting from a minimal shell (chat interface, model client wired to the proxy, trace writer, interface contract, empty MCP server). The shell includes neither the conversational loop nor the *system prompt*.

Main target: **Windows**, with Python **3.13** from [python.org](https://www.python.org/downloads/) or uv. Linux and macOS are supported too.

## Layout

```
README.md            this file
GETTING_STARTED.md   what is provided, what you write
my-agent/            the ONLY folder students edit
  harness.py         empty shell of your agent
  mcp_server.py      empty MCP server (wired in workshop 09)
  sandbox/           sandbox policy (policy.yaml, workshop 10d)
  skills/            versioned skills catalog (manifest.yaml + <id>/, workshop 14)
  attachments/       read-only attachments area (workshop 15)
  local-mode/        landing structure of workshop 19 (specifications/, controls/)
workshops/           one folder per workshop: README.md (guide), state.yaml, tests/
workshop_kit/        provided infrastructure (Python package), never edited by students
  chat-ui/           standard Chainlit UI, with its own Python project and dependencies
  shell/             settings, harness contract, chat interface, model client, tracer
  llm_proxy/         OpenAI-compatible proxy (simulated / replay; live Azure OpenAI later)
  apps/business_api/ business API test app (FastAPI + SQLite)
  apps/docs_search/  document search test app (SQLite FTS5 + sqlite-vec)
  services/          readers for my-agent/sandbox, my-agent/skills, my-agent/attachments
  evaluation/        LLM judge and evaluation-route checksum
  testing/           shared test helpers and pytest fixtures
  cli.py             the `workshop` command
corpus/              documentation sources (.txt) and metadata.yaml
docs/                interface contract, installation, decisions, test inventory, team validation
tests/kit/           tests of the infrastructure itself (must pass)
```

Three test suites live in this repository:

- `workshops/*/tests/`: the success criteria of each workshop. **They fail until the workshop is done** (red, then green).
- `tests/kit/`: the tests of the provided infrastructure, which must always pass.
- `workshop_kit/chat-ui/tests/`: the chat UI's tests, run with that project's own dependencies; they must always pass too.

Students only touch `my-agent/`. There is no exception: the files the kit reads on your behalf (sandbox policy, skills catalog, attachments) live in `my-agent/` too, and `workshop_kit/` loads them through configurable paths (`sandbox_policy_file`, `skills_dir`, `attachments_dir` in `workshop_kit/shell/config.py`, overridable from `.env`). The supplied UI resources live in `workshop_kit/chat-ui/`; outside this UI project, `workshop_kit/` contains only Python code. A kit test checks this separation.

## Quick start

See [docs/installation.md](docs/installation.md) for details. In short, on Windows (PowerShell):

```powershell
uv python install 3.13
uv sync --extra dev --python 3.13
Copy-Item .env.example .env
uv run pytest tests/kit
uv run workshop check-shell   # succeeds when every workshop test fails on the empty shell
uv run workshop check 03      # stays red until workshop 03 is done
```

On Linux or macOS (bash):

```bash
uv python install 3.13
uv sync --extra dev --python 3.13
cp .env.example .env
uv run pytest tests/kit
uv run workshop check-shell
uv run workshop check 03
```

## Start the complete environment

The Chainlit chat is a standard part of the kit. The same Python startup script
works on Windows and Linux (Python and uv must be installed):

```powershell
python start.py
```

On Linux, use `python3 start.py` if Python is named `python3`.
The script works from any directory when given its absolute path.
Or, on any supported OS after installing the kit dependencies:

```bash
uv run workshop serve
```

This starts the business API, document search, model proxy, MCP server,
conversation API and browser UI. Open <http://127.0.0.1:8080>.
Each Python project keeps its own dependencies, lockfile and virtual environment;
the launcher installs the UI project separately. Ctrl+C stops all six services.
Existing datasets are preserved unless `--reset-data` is requested.

If the default ports are occupied, use `uv run workshop serve --port-offset 10`
(chat on port 8090), or `python start.py --port-offset 10`. The launcher
does not reuse or stop pre-existing services. See the [UI guide](workshop_kit/chat-ui/README.md).

## Licence

The licence is not decided yet. No `LICENSE` file is published for now.

## Documentation

- [Chainlit chat UI](workshop_kit/chat-ui/README.md) (French browser chat, steps and tool calls)
- [Getting started](GETTING_STARTED.md)
- [Installation](docs/installation.md)
- [Interface contract](docs/interface-contract.md)
- [Workshop test inventory](docs/test-inventory.md)
- [Team validation procedure](docs/team-validation.md) (phase B, once Azure is available)
- [Provisional decisions](docs/decisions.md)
