# Workshop chat UI

Standard **Chainlit** browser interface for the workshop kit. The UI speaks
French and contains no system prompt, agent loop, tools, or model calls.

## Why a separate environment?

All six applications use Python **3.13**, but Chainlit 2.12 requires
`mcp>=1.28.1,<2`, whereas the agent and shared tests require `mcp>=2.3`.
This directory therefore has its own project, environment, and lockfile inside
`workshop_kit/chat-ui/`. Do not install Chainlit into the agent or shared test
environment or downgrade their MCP SDK. There is no root Python project.

## Run (from the repository root)

Start the **complete environment**, including the UI:

```powershell
python start.py
```

Use `python3 start.py` on Linux if needed. This is the same cross-platform script;
it uses only the standard library, synchronizes `workshop_kit/bootstrap/`, then starts
the launcher without installing test dependencies. No activated environment is
needed. Alternatively, from the repository root on any supported OS:

```powershell
uv run --project workshop_kit/bootstrap workshop serve
```

The launcher synchronizes this UI project's dependencies with its own lockfile,
starts all six services, initializes missing databases, and checks readiness.
Open <http://127.0.0.1:8080>. Ctrl+C stops the processes it created. Existing data
is preserved unless you request `--reset-data`.

If the default ports are occupied, `uv run --project workshop_kit/bootstrap workshop serve --port-offset 10`
shifts all six ports (chat: 8090, conversation API: 8010). It never reuses or kills
unrelated services. See [installation](../../docs/installation.md) for all ports
and the per-service logs in `.workshop/logs/`.

### Welcome message and resources

All UI resources belong to this project, not the repository root:

- `workshop_chat_ui/welcome.md`: the welcome message sent at the start of each chat;
- `chainlit.md`: the UI's readme panel;
- `.chainlit/config.toml`: French language, theme, and enabled features.

The welcome message is read from the markdown resource, not embedded in Python.
Start a new conversation to see an updated welcome message. No agent code needs
to be changed. Uploads, audio, message editing and direct MCP connections are
disabled. The kit API is the only route to the agent.

### Run the UI by itself (advanced)

With a conversation API already running, from the repository root:

```powershell
uv run --directory workshop_kit/chat-ui chainlit run workshop_chat_ui/app.py --host 127.0.0.1 --port 8080 --headless
```

Backend URLs are used server-side, so no CORS
change is required on the kit.

The empty harness displays a French explanation pointing to workshop 03. This
is expected; starting the UI does not implement the agent. Start the model proxy,
business API, document search, and MCP server separately as your implementation
needs them (see [installation](../../docs/installation.md)). Live Azure mode remains
unimplemented.

### Backend URL

Default: `http://127.0.0.1:8000` (the conversation API, **not** the model proxy).
When running the UI alone, set `WORKSHOP_CHAT_BACKEND_URL` in its own `.env` file
(use this project's `.env.example` as a template) or in the UI terminal:

```powershell
$env:WORKSHOP_CHAT_BACKEND_URL = "http://127.0.0.1:9000"
```

Restart the UI after changing configuration. The complete-stack launcher sets
this URL to its own conversation API, including any port offset; it intentionally
overrides a standalone URL from the environment.

## Supported behavior

- Text chat, in French, with a processing message while waiting for the backend.
- Chainlit's **new conversation** control starts a fresh backend conversation;
  subsequent turns reuse its id. Sessions do not share history. There is no
  persistent conversation history or authentication.
- `text` events append to the answer; `error` and unsuccessful `end` events
  display a clear error without duplicating it.
- Connection failures, HTTP errors, timeouts, malformed SSE, and incomplete
  streams are reported explicitly. A submitted message is **never retried
  automatically**, since it may have triggered a write.
- `step` events appear as expandable operational steps. Input/output are rendered
  as data, not executed. These are reported actions, not hidden model reasoning.

The existing backend buffers the harness events until the end of the turn.
The adapter consumes SSE progressively, but cannot display those buffered events
before the backend sends them. No backend streaming semantics are changed here.

### Steps and tool calls

The stable contract reserves `step` with an open data payload. This UI recognizes:

```json
{"name": "Recherche des commandes", "input": {"customer": "Martin Durand"}, "output": {"count": 2}}
```

Adding `tool` or `tool_name` identifies a tool step:

```json
{"tool": "query_orders", "arguments": {"id": "CMD-1042"}, "result": {"status": "livrée"}}
```

`input` / `arguments` and `output` / `result` are aliases. Unknown step fields
remain visible as JSON. As optional extensions, separate `tool_call` and
`tool_result` events are also displayed as tool steps; no new event is required
from an existing harness. They appear as separate records, not a reconstructed
tool lifecycle. No tools are inferred from the assistant's text. The harness
must omit secrets and sensitive credentials from event payloads.

Confirmations, attachments, sources, persistent history and backend cancellation
are outside this version's scope. Closing/stopping the UI does not guarantee
that work already submitted to the backend is cancelled.

## Tests

From the repository root:

```powershell
uv sync --project workshop_kit/chat-ui --extra dev
uv run --project workshop_kit/chat-ui --extra dev pytest --confcutdir workshop_kit/chat-ui workshop_kit/chat-ui/tests
uv sync --project workshop_tests --locked --python 3.13
uv run --project workshop_tests pytest -c workshop_tests/pyproject.toml workshop_kit/tests
```

`--confcutdir` bounds UI test configuration discovery to the UI project. Shared
fixtures (which import MCP 2) are loaded explicitly by the separate
`workshop_tests/pyproject.toml` configuration, never by a root `conftest.py`.
Do not use that test configuration for UI tests. CI runs both suites on Windows
and Linux.

## Local development only

Both servers bind to loopback by default. The API accepts a default test identity;
this is not production authentication. Do not expose this setup to the network
or enable public sharing without adding authentication and access controls.