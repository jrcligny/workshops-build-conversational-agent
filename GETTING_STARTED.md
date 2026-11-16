# Getting started

This repository accompanies the workshops of the book. In the book, the workshops are decision studies; here, you carry them out in a provided environment, without any pre-written agent code.

Main target: Windows, with Python 3.13 (from python.org or uv). See [docs/installation.md](docs/installation.md).

## What is provided

The agent you build answers in French (code and docs stay English; see `docs/decisions.md`).

Two test applications (business API and document search), a model proxy in simulated mode, a chat interface, traces, an empty MCP server, and one set of end-to-end tests per workshop, stored next to its guide in `workshops/<id>-<topic>/tests/`. All of this lives in `workshop_kit/`, which you do not edit. The shell also provides, in `my-agent/`, the empty places you will fill in: the sandbox policy (`sandbox/policy.yaml`), the skills catalog (`skills/`), the attachments area (`attachments/`) and the local development mode (`local-mode/`).

## What you write

Your agent, in `my-agent/harness.py`: first the *system prompt* and the conversational loop (workshop 03), then the tools, the agent loop, compaction, and so on. In workshop 09, you wire `my-agent/mcp_server.py` to the business API.

## Models

No real model is provided while this repository is being designed, and none is needed to start. The default mode is **simulated** (scripted chat, deterministic embeddings, scripted judge). The live mode, through an Azure OpenAI proxy, will come later; the key will stay on the server. The names of the Azure deployments are configurable (see [docs/decisions.md](docs/decisions.md)).

## Useful commands

- `uv run workshop start 07` shows the guide, without copying any solution.
- `uv run workshop check 07` runs `workshops/07-context-compaction/tests/`.
- `uv run workshop check 07 --non-regression` runs the tests of workshops 03 to 07.
- `uv run workshop check-shell` checks that every workshop test fails on the empty shell.
