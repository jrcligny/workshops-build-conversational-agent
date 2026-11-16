# Getting started

This repository accompanies the workshops of the book. In the book, the workshops are decision studies; here, you carry them out in a provided environment, without any pre-written agent code.

Main target: Windows, with Python 3.13 (from python.org or uv). See [docs/installation.md](docs/installation.md).

## What is provided

The agent you build answers in French, and the workshop guides are in French (code and technical docs stay English; see `docs/decisions.md`).

Two test applications (business API and document search), a model proxy (simulated or live), a chat interface and traces live in `workshop_kit/`, which you do not edit. The CLI and launcher live in `workshop_kit/bootstrap/`; shared fixtures, evaluation helpers and test dependencies live in `workshop_tests/`. End-to-end tests stay next to each guide in `workshops/<id>-<topic>/tests/`. The shell also provides, in `my-agent/`, an empty MCP server and the empty places you will fill in: the sandbox policy (`sandbox/policy.yaml`), the skills catalog (`skills/`), the attachments area (`attachments/`) and the local development mode (`local-mode/`).

## What you write

Your agent, in `my-agent/harness.py`: first the *system prompt* and the conversational loop (workshop 03), then the tools, the agent loop, compaction, and so on. In workshop 09, you wire `my-agent/mcp_server.py` to the business API.

## Models

The `.env.example` default is **simulated** (scripted chat, deterministic embeddings, scripted judge): enough to start, and the mode of the CI. The **live** mode (`PROXY_MODE=live` in `.env`) forwards chat completions to Azure OpenAI through the proxy, which keeps the key on the server; it needs `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_CHAT_DEPLOYMENT` (plus `AZURE_OPENAI_FALLBACK_DEPLOYMENT` for workshop 18). Embeddings stay deterministic in every mode. The tests honour `PROXY_MODE` from `.env`. The names of the Azure deployments are configurable (see [docs/decisions.md](docs/decisions.md)).

**Which mode for which workshop.** The **live mode is the reference** for every workshop (set `PROXY_MODE=live` and `MODEL_MODE=live`). Workshop 03 can be started in simulated mode while you wait for Azure access, but validate it in live mode. From workshop 04 on, live mode is required: the agent must decide on its own which tool to call, which the simulated model does not do, so a test passed in simulated mode would only reward a hard-coded workflow. The simulated mode is the one of the CI, `check-shell` and `check-inert`.

**Judge.** Facts checked by code come first; a rubric then judges the meaning, with a judge model when `JUDGE_BASE_URL` (and `JUDGE_API_KEY`) are set. A rubric replayed on fresh conversations passes when `JUDGE_K` runs out of `JUDGE_N` pass (3 out of 5 by default): count a few model calls per judged test.

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
- `uv run --project workshop_kit/bootstrap workshop check 07` runs `workshops/07-progressive-disclosure/tests/` in the test project's environment.
- `uv run --project workshop_kit/bootstrap workshop check 07 --non-regression` runs the tests of workshops 03 to 07.
- `uv run --project workshop_kit/bootstrap workshop check-shell` checks that every workshop test fails on the empty shell.
- `uv run --project workshop_kit/bootstrap workshop check-inert` checks that every workshop test fails against an inert agent (one that answers without calling the model nor any tool).
- In `--non-regression`, a test marked `superseded_by("<id>")` is skipped once the checked workshop reaches `<id>` (for example the "no tool yet" test of workshop 03 from workshop 04 on).
- `uv run --project workshop_tests pytest -c workshop_tests/pyproject.toml workshop_kit/tests` runs the infrastructure tests, which must pass.
