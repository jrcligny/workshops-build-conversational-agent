# Workshops — Build a Conversational Agent

Companion repository for the workshops of the book *De l'assistant à l'agent : anatomie d'un agent conversationnel* (written in French; this repository is in English).

It provides the environment and the end-to-end tests to carry out the workshops (chapters 3 to 19, chapter 10 being split into 10a to 10d). **It does not contain the agent's code**: you build your own in `my-agent/`, starting from a minimal shell (chat interface, model client wired to the proxy, trace writer, interface contract, empty MCP server). The shell includes neither the conversational loop nor the *system prompt*.

Main target: **Windows**, with Python **3.15** (latest stable release on [python.org](https://www.python.org/downloads/) at design time: 3.15.2). Linux and macOS are supported too.

## Layout

```
README.md            this file
GETTING_STARTED.md   what is provided, what you write
my-agent/            the ONLY place where you write code
  harness.py         empty shell of your agent
  mcp_server.py      empty MCP server (wired in workshop 09)
  local-mode/        landing structure of workshop 19 (specifications/, controls/)
workshops/           one folder per workshop: README.md (guide), state.yaml, tests/
workshop_kit/        provided infrastructure (Python package), never edited by students
  shell/             settings, harness contract, chat interface, model client, tracer
  llm_proxy/         OpenAI-compatible proxy (simulated / replay; live Azure OpenAI later)
  apps/business_api/ business API test app (FastAPI + SQLite)
  apps/docs_search/  document search test app (SQLite FTS5 + sqlite-vec)
  services/          empty bases: sandbox, skills_catalog, attachments
  evaluation/        LLM judge and evaluation-route checksum
  testing/           shared test helpers and pytest fixtures
  cli.py             the `workshop` command
corpus/              documentation sources (.txt) and metadata.yaml
docs/                interface contract, installation, decisions, test inventory, team validation
tests/kit/           tests of the infrastructure itself (must pass)
```

Two kinds of tests live in this repository:

- `workshops/*/tests/`: the success criteria of each workshop. **They fail until the workshop is done** (red, then green).
- `tests/kit/`: the tests of the provided infrastructure, which must always pass.

Students do not edit the Python code of `workshop_kit/`. A few workshops ask you to fill in data files that the kit reads: the sandbox policy (`workshop_kit/services/sandbox/policy.yaml`, workshop 10d), the skills catalog (`workshop_kit/services/skills_catalog/`, workshop 14) and the attachments area (`workshop_kit/services/attachments/`, workshop 15).

## Quick start

See [docs/installation.md](docs/installation.md) for details. In short, on Windows (PowerShell):

```powershell
uv python install 3.15
uv sync --extra dev --python 3.15
Copy-Item .env.example .env
uv run pytest tests/kit
uv run workshop check-shell   # succeeds when every workshop test fails on the empty shell
uv run workshop check 03      # stays red until workshop 03 is done
```

On Linux or macOS (bash):

```bash
uv python install 3.15
uv sync --extra dev --python 3.15
cp .env.example .env
uv run pytest tests/kit
uv run workshop check-shell
uv run workshop check 03
```

## Licence

The licence is not decided yet. No `LICENSE` file is published for now.

## Documentation

- [Getting started](GETTING_STARTED.md)
- [Installation](docs/installation.md)
- [Interface contract](docs/interface-contract.md)
- [Workshop test inventory](docs/test-inventory.md)
- [Team validation procedure](docs/team-validation.md) (phase B, once Azure is available)
- [Provisional decisions](docs/decisions.md)
