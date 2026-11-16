# Getting started

This repository accompanies the workshops of the book. In the book, the workshops are decision studies; here, you carry them out in a provided environment, without any pre-written agent code.

Main target: Windows, with Python 3.13 (from python.org or uv). See [docs/installation.md](docs/installation.md).

## What is provided

The agent you build answers in French (code and docs stay English; see `docs/decisions.md`).

Two test applications (business API and document search), a model proxy in simulated mode, a chat interface and traces live in `workshop_kit/`, which you do not edit. The CLI and launcher live in `workshop_kit/bootstrap/`; shared fixtures, evaluation helpers and test dependencies live in `workshop_tests/`. End-to-end tests stay next to each guide in `workshops/<id>-<topic>/tests/`. The shell also provides, in `my-agent/`, an empty MCP server and the empty places you will fill in: the sandbox policy (`sandbox/policy.yaml`), the skills catalog (`skills/`), the attachments area (`attachments/`) and the local development mode (`local-mode/`).

## What you write

Your agent, in `my-agent/harness.py`: first the *system prompt* and the conversational loop (workshop 03), then the tools, the agent loop, compaction, and so on. In workshop 09, you wire `my-agent/mcp_server.py` to the business API.

## Models

No real model is provided while this repository is being designed, and none is needed to start. The default mode is **simulated** (scripted chat, deterministic embeddings, scripted judge). The live mode, through an Azure OpenAI proxy, will come later; the key will stay on the server. The names of the Azure deployments are configurable (see [docs/decisions.md](docs/decisions.md)).

## Useful commands

Run `python start.py` on Windows or `python3 start.py` on Linux to prepare the
tooling environment and start all services. This standard-library bootstrap
never installs test dependencies. From the repository root,
`uv run --project workshop_kit/bootstrap workshop serve` also starts all services,
including the [Chainlit UI](workshop_kit/chat-ui/README.md), a standard part of the kit.
Open <http://127.0.0.1:8080>. It displays the existing agent's responses, steps,
and tool calls without implementing any workshop for you. Each Python project
keeps its own dependencies and environment.

For checks, first run `uv sync --project workshop_kit/bootstrap --locked --python 3.13`
and `uv sync --project workshop_tests --locked --python 3.13` from the repository
root. There is no root Python project or shared environment.

- `uv run --project workshop_kit/bootstrap workshop start 07` shows the guide, without copying any solution.
- `uv run --project workshop_kit/bootstrap workshop check 07` runs `workshops/07-context-compaction/tests/` in the test project's environment.
- `uv run --project workshop_kit/bootstrap workshop check 07 --non-regression` runs the tests of workshops 03 to 07.
- `uv run --project workshop_kit/bootstrap workshop check-shell` checks that every workshop test fails on the empty shell.
- `uv run --project workshop_tests pytest -c workshop_tests/pyproject.toml workshop_kit/tests` runs the infrastructure tests, which must pass.
