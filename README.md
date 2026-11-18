# Workshops — Build a Conversational Agent

Companion repository for the workshops of the book *De l'assistant à l'agent : anatomie d'un agent conversationnel* (written in French).

**Languages: code and docs in English, the agent converses in French.** Everything in this repository is in English except what the agent's user reads or types: the user turns and expected answers in the tests, the simulated model replies, the corpus texts and the display labels of business values. Details in [docs/decisions.md](docs/decisions.md#language).

It provides the environment and the end-to-end tests to carry out the workshops (chapters 3 to 17 of the book, one workshop per chapter and none for chapter 8; the workshop number is the chapter number: see the table in [workshops/README.md](workshops/README.md)). **It does not contain the agent's code**: you build your own in `my-agent/`, starting from a minimal bootstrap (agent gateway with chat interface, model client wired to the proxy, trace writer, interface contract, empty MCP server). The bootstrap includes neither the conversational loop nor the *system prompt*.

Main target: **Windows**, with Python **3.13** from [python.org](https://www.python.org/downloads/) or uv. Linux and macOS are supported too.

## Layout

```
README.md            this file
GETTING_STARTED.md   what is provided, what you write
my-agent/            the ONLY folder students edit
  harness.py         runnable bootstrap of your agent
  mcp_server.py      empty MCP server (wired in workshop 06)
  sandbox/           sandbox policy (policy.yaml, workshop 07)
  skills/            versioned skills catalog (manifest.yaml + <id>/, workshop 13)
  attachments/       read-only attachments area (workshop 14)
  local-mode/        landing structure of workshop 17 (specifications/, controls/)
workshops/           one folder per workshop: README.md (guide), contrat.md (test contract), state.yaml, tests/
clients/chat_ui/     standard Chainlit UI (client of the agent gateway), own project and dependencies
gateway/             running infrastructure, never edited by students
  agent_gateway/     chat API: conversations, identity, loading of my-agent/harness.py
  model_gateway/     OpenAI-compatible model proxy (simulated / replay / live Azure OpenAI)
agent_sdk/           what my-agent imports without editing it: contract types, Tracer, model client,
                     tool schemas, HTTP/MCP clients, readers of skills, sandbox and attachments
agent_testkit/       what tests the agent (never imported by my-agent): pytest plugins, ChatClient,
                     cases, conversations, assertions (expect), semantic judge (evaluation)
business/            what the agent queries
  business_api/      business API test app (FastAPI + SQLite)
  docs_search/       document search test app (SQLite FTS5 + sqlite-vec), corpus/ included
shared/              settings (workshop_config) and text vectors shared by the services
tooling/
  cli/               CLI and six-service launcher (workshop check, serve, check-bootstrap, check-inert);
                     test runner (`tests` group, pytest configuration), cross-component tests
                     (integration/), inert agent, declared bootstrap passes
ruff.toml            editor/static lint configuration only, not a Python project
docs/                interface contract, installation, decisions, test inventory, team validation
```

Three test suites live in this repository:

- `workshops/*/tests/`: the success criteria of each workshop. **They fail until the workshop is done** (red, then green).
- `<component>/tests/` (and `tooling/cli/integration/`): the tests of the provided infrastructure, next to the component they test; they must always pass.
- `clients/chat_ui/tests/`: the chat UI's tests, run with that project's own dependencies; they must always pass too.

Students only touch `my-agent/`. The files the kit reads on your behalf (sandbox policy, skills catalog, attachments) live there too. The supplied UI resources live in `clients/chat_ui/`; service dependency manifests and lockfiles live alongside their applications. The remaining kit files are Python code. A kit test checks this separation.

## Quick start

See [docs/installation.md](docs/installation.md) for details. In short, on Windows (PowerShell):

```powershell
uv python install 3.13
uv sync --project tooling/cli --locked --python 3.13
uv sync --project tooling/cli --group tests --locked --python 3.13
Copy-Item .env.example .env
uv run --project tooling/cli --group tests pytest -c tooling/cli/pyproject.toml agent_sdk agent_testkit business gateway tooling
uv run --project tooling/cli workshop check-bootstrap   # succeeds when every workshop test fails on the bootstrap, except tooling/cli/bootstrap_passes.txt
uv run --project tooling/cli workshop check 03      # stays red until workshop 03 is done
```

On Linux or macOS (bash):

```bash
uv python install 3.13
uv sync --project tooling/cli --locked --python 3.13
uv sync --project tooling/cli --group tests --locked --python 3.13
cp .env.example .env
uv run --project tooling/cli --group tests pytest -c tooling/cli/pyproject.toml agent_sdk agent_testkit business gateway tooling
uv run --project tooling/cli workshop check-bootstrap
uv run --project tooling/cli workshop check 03
```

## Start the complete environment

The Chainlit chat is a standard part of the kit. The same Python startup script
works on Windows and Linux (Python and uv must be installed):

```powershell
python start.py
```

On Linux, use `python3 start.py` if Python is named `python3`.
The script works from any directory when given its absolute path.
It uses only the standard library, synchronizes the tooling project, then runs
the service launcher; it never installs test dependencies.
Or, from the repository root on any supported OS:

```bash
uv run --project tooling/cli workshop serve
```

This starts the business API, document search, model proxy, MCP server,
conversation API and browser UI. Open <http://127.0.0.1:8080>.
Each Python project keeps its own dependencies, lockfile and virtual environment;
the launcher synchronizes each of the six application projects independently.
There is no root Python project, lockfile or virtual environment. Commands use
`tooling/cli/`; tests use its `tests` dependency group, separately from the six applications.
Ctrl+C stops all six services.
Existing datasets are preserved unless `--reset-data` is requested.

If the default ports are occupied, use `uv run --project tooling/cli workshop serve --port-offset 10`
(chat on port 8090), or `python start.py --port-offset 10`. The launcher
does not reuse or stop pre-existing services. See the [UI guide](clients/chat_ui/README.md).

### Hot reload of `my-agent/`

Edit `my-agent/` while the stack runs: no restart is needed.

- **Python files** (`harness.py`, the `agent_*.py` modules it imports, `mcp_server.py`): at the next
  message, the interface sees the change, imports the modules of `my-agent/` again and builds a new
  `Harness`. The MCP server (`workshop_tools.mcp_runner`, port 8004) checks `my-agent/` twice a
  second, loads `application()` of `mcp_server.py` again and serves the new version on the same
  port. The interface waits until the MCP server serves the same version before running the turn.
  The logs say so: `my-agent reloaded (changed: …)` in `interface.log`,
  `MCP server reloaded (changed: …)` in `mcp.log`.
- **Files read at each turn** (`system_prompt.md`, `compaction_prompt.md`, `skills/`,
  `sandbox/policy.yaml`): read again at the next turn, as before. A `SKILL.md` already loaded
  in a conversation, or an attachment already read, keeps its content in that conversation.
- **An error** (syntax error, failing import, `application()` that raises): the message gets an
  error that names the file, the line and the error, for example
  `my-agent could not be loaded: my-agent/harness.py, line 12: SyntaxError: invalid syntax`,
  and the traceback is in `.workshop/logs/interface.log` or `mcp.log`. Fix the file and send the
  message again. Meanwhile, the MCP server keeps serving its last working version. Only at startup
  does a broken `mcp_server.py` stop the stack, as before.
- **What a reload keeps**: the conversations, their context and their working state
  (`agent_sdk.context`). It starts a new `Harness`: what the old instance kept in its attributes is
  lost (pending drafts of workshop 07, skills loaded in a conversation, attachments read).
- **What needs a restart**: `.env` and the code outside `my-agent/` (`agent_sdk/`, `gateway/`,
  `business/`, ...).

Changes are detected by polling the files (date and size), which works the same on Windows,
macOS, Linux and WSL, including on a Windows drive opened from WSL. The tests (`workshop check`)
load `my-agent/` themselves, without this mechanism.

## Licence

The licence is not decided yet. No `LICENSE` file is published for now.

## Documentation

- [Chainlit chat UI](clients/chat_ui/README.md) (French browser chat, steps and tool calls)
- [Getting started](GETTING_STARTED.md)
- [Installation](docs/installation.md)
- [Workshop tooling](tooling/cli/README.md)
- [Test environment](agent_testkit/README.md)
- [Interface contract](docs/interface-contract.md)
- [Workshop test inventory](docs/test-inventory.md)
- [Team validation procedure](docs/team-validation.md) (phase B, once Azure is available)
- [Provisional decisions](docs/decisions.md)
