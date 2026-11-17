# Agent ↔ tests interface contract

This contract is stable across all workshops. The capabilities not used yet (steps, interruption, confirmation, sources, mentions, attachments) exist in the protocol and stay inactive until the workshop that activates them.

## Chat entry point

The chat interface is `gateway/agent_gateway/src/agent_gateway/chat_app.py`.

| Element | Contract |
|---|---|
| Creation | `POST /conversations` with `user_id`, `role`, `organization`, optionally `app_token`, `sign_in` and `limits`. With `"sign_in": true` and no `app_token`, the interface issues an entry token (`typ=entry`) for the user, as a signed-in interface would; the tests and the Chainlit UI open their conversations that way, except the refusal cases of workshop 10a. Response: `{ "id": ... }`. |
| Test identities | `GET /users` lists the users of the seeded datasets (`user_id`, `name`, `role`, `organization`). The identity selector of the Chainlit UI reads it and opens its conversations with the chosen identity. |
| Turn | `POST /conversations/{id}/messages` with `{ "text": "..." }`. Server-sent events (SSE) response. |
| Events (workshop 03) | `text` (chunks, field `content`) then `end` (field `ok`). An `error` event reports a failure of the agent gateway. |
| Multi-turn | The same conversation id is reused. The *harness* replays the whole context of the conversation (`agent_sdk.context`: user and assistant messages, tool calls and their results) in the model input; the `history` parameter is only the transcript shown by the interface (texts). A conversation may also start from a written history (`POST /conversations/{id}/history`, tests; with `"append": true`, the written history follows the turns already played): the agent continues it as its own, and refuses without running any call the model makes to a tool it does not offer (`agent_sdk.context.unoffered_call_results`). |
| Service addresses | `BUSINESS_API_URL`, `DOCS_SEARCH_URL`, `PROXY_URL`, `INTERFACE_URL` are set in the environment by `workshop serve` and by the test fixtures (`workshop check`); `MCP_URL` too, by `workshop serve` and by the tests of workshops 06 and 10a, which start the MCP server of `my-agent/`. Read them at call time: the ports differ between the two. |

The tests use the internal client (`agent_testkit/src/agent_testkit/chat_client.py`), not a browser.
The standard Chainlit UI in `clients/chat_ui/` consumes the same HTTP/SSE
contract from its own Python environment. From the repository root, run
`uv run --project tooling/cli workshop serve` to start
the complete environment, including that UI.

## Attachments (reserved for workshop 14)

The contract already provides the entry point, with no file in the bootstrap:

| Element | Contract |
|---|---|
| List | `GET /attachments` returns `{ "attachments": [...] }` from the area `my-agent/attachments/` (setting `attachments_dir`). In the bootstrap, the list is empty. |
| Turn | The body of `POST /conversations/{id}/messages` accepts an optional `attachments` field (list of ids). It is passed to the *harness* (`turn(..., attachments=...)`). |
| Reserved event | `attachment` may report that an attached document was read. |

No sample quote is dropped in the bootstrap. You will fill the area in workshop 14.

## MCP server (empty bootstrap, wired in workshop 06)

The bootstrap includes `my-agent/mcp_server.py`: an MCP server that starts and answers the handshake, written with the official Python SDK `mcp`. It exposes **no business tool**. Planned transport: streamable HTTP (`streamable-http`), stateless mode, endpoint `/mcp` (port 8004 by default).

```powershell
uv run --project my-agent python my-agent/mcp_server.py
```

Run this command from the repository root; the MCP server uses its own project,
lockfile and environment. In workshop 06, you will move the tools there and wire
them to the business API. The workshop 06 tests stay red until this is done.

## Traces

One trace per turn, in a JSONL file (`turns.jsonl`) in the configured folder (`traces/` by default). Fields required from workshop 03:

- conversation and turn ids, `timestamp`;
- `input` sent to the model: `system_prompt`, `history` (the context messages of the previous turns), new `message`;
- `model`: id exposed by the proxy, tokens, duration, stop reason;
- `output`: assistant text;
- `tools`: empty list in workshop 03;
- no secret (Azure key, token).

Later workshops add fields; the table [Names read by the tests](#names-read-by-the-tests) lists them, and each workshop's `contrat.md` (section « Ce que lisent les tests ») and the docstring of its test file name the fields they read.

The bootstrap provides `agent_sdk/src/agent_sdk/trace.py`: a `Tracer` with one method per event to record (`call_model`, `tool_call`, `compaction`, `state`, `memory`, `mention`, `fallback`…) and `write()`, so the student never assembles the trace JSON by hand.

## Harness to implement

In `my-agent/harness.py`, a `Harness` class exposes `turn(conversation_id, message, user, history, attachments=None, interrupt_requested=False, confirmation=False, limits=None)` and yields `Event` objects (see `agent_sdk/src/agent_sdk/contract.py`). The shipped bootstrap calls the model through the proxy (`PROXY_URL`) with the system prompt of `my-agent/system_prompt.md`, the context of the conversation (`agent_sdk.context`) and the message, relays the answer, records the turn and writes the trace; it calls no tool. Every workshop test fails on it except those listed in `tooling/cli/bootstrap_passes.txt`.

## Other locations of the bootstrap

| Location | Role | State in the bootstrap |
|---|---|---|
| `my-agent/sandbox/policy.yaml` | Sandbox policy (workshop 10d), read by `agent_sdk/src/agent_sdk/sandbox.py` (setting `sandbox_policy_file`) | Present, policy inactive, empty allowlist |
| `my-agent/skills/` | Versioned skills catalog (workshop 13): `manifest.yaml` + `<id>/SKILL.md`, read by `agent_sdk/src/agent_sdk/skills.py` (setting `skills_dir`) | Valid manifest, zero *skill* |
| `my-agent/attachments/` | Read-only area for attached documents (workshop 14), read by `agent_sdk/src/agent_sdk/attachments.py` (setting `attachments_dir`) | Empty |
| `workshops/15-evaluation/routes/` | Evaluation routes and their checksum (workshops 15 and 17) | Empty set, checksum present |
| `my-agent/local-mode/` | Development mode landing (workshop 17, *coding agent* optional) | Empty structure (`specifications/`, `controls/`) |

## Reserved events and gestures (workshops 06, 07, 10b, 10d)

| Element | Contract |
|---|---|
| Step | SSE event `step` during a turn with several cycles (workshop 06). |
| Interruption | `POST /conversations/{id}/interruption`, or the `interrupt` field of the message. The next turn only receives `interrupt_requested=True` and stops without a new call (event `interruption`). |
| Compaction | SSE event `compaction` (or a `mention` announcing it) when the history has been compacted (workshop 10). The trace describes the threshold, the cleared tool results, the kept and summarized turns, the compaction prompt, the separate model call and the previous and new summaries. |
| Confirmation | `POST /conversations/{id}/confirmation` with `{ "confirmed": true }`. The next turn only receives `confirmation=True` (workshop 10b); a later draft needs a new gesture. The `confirmation_requested` event precedes the gesture. |
| Limits | Optional `limits` field of `POST /conversations` (`duration_s`, `token_budget`), passed to the *harness* (workshop 10d). |

## Names read by the tests

Everything not listed here is free. Tool result statuses are `ok` (`found` is accepted as a
synonym), `approximate`, `not_found`, `error` and `denied`.

| Workshop | Trace fields | Events | Tools, parameters, other names |
|---|---|---|---|
| 03 | `input.system_prompt`, `input.message`, `input.history[]` (`role`, `content`), `tools` (empty) | `text`, `end` | one model call through the proxy; tests marked `superseded_by("04")` |
| 04 | `tools[]` (`name`, `arguments`, `result.status`, `result.order`, `result.suggestions`) | | an invalid reference (`1042;DROP`) is rejected before any `/orders` call (status `error`) |
| 05 | `tools[].arguments.filter == "late"`, `result.total` or `result.count` | | customer search returns both namesakes |
| 06 | `cycles`, `tools[].cycle`, `cycle_limit_reached`, `interrupted` | `step` (`tool`), `mention`, `interruption` | |
| 07 | `model.calls[].context_size`, `tools[].result.orders` (summarized rows with `reference`), `returned`, `total`, `total_status`, `truncated`, `count`; business API log: `GET /orders/<reference>` | | `arguments.mode == "count"`; the position parameter name is free |
| 08 | `compaction` (`threshold`, `kept_turns`, `cleared_tool_results[]`, `summarized_turns`, `system_prompt`, `previous_summary`, `summary`, `model_call`), `input.history`, proxy log `system_sha256`; `state.current_customer` (`id`, `name`, `city`), `state.current_order.reference`, `state.candidates`; `input.state` | `compaction` or `mention` | `COMPACTION_MESSAGE_THRESHOLD`, `COMPACTION_KEEP_TURNS`, `my-agent/compaction_prompt.md` |
| 09 | `tools[].transport == "mcp"` | | `my-agent/mcp_server.py`: `application()`, `MCP_PATH`; generic tool with `source`, `filters`, `aggregate`; `result.error`, `result.value` |
| 10a | `identity` (`user`, `token_type: "application"`) | | entry token in `Authorization: Bearer` to the MCP server; `denied` / `error` without a valid one |
| 10b | | `confirmation_requested` (`draft_id`) | `POST /conversations/{id}/confirmation`; purchase requests by `paul-buyer` (buyer) |
| 10c | | | no tool whose name contains `python`, `exec`, `code`, `eval`, `shell`; median refused |
| 10d | `limit_reached` (`duration` or `token_budget`) | `mention` | `my-agent/sandbox/policy.yaml`; runtime probes on files opened and hosts contacted |
| 12 | `memory` (`loaded`, `written`, `deleted`; entries `topic`, `value`, `origin`, `recorded_at`, `user`, `organization`), `input` | `mention` (first turn), `memory` (`action`, `topic`, `value`) | `MEMORY_DIR` (files on disk, read at call time); topics `amount_display` (`excluding_tax`, `including_tax`), `answer_format` (`table`, `text`); `origin: "user"` |
| 13 | `tools[].result.passages[]`, `no_passage` | `sources` (`sources[]`: `title`, `version`, `address`) | |
| 14 | `skills_loaded[]` (`id`, `version`, `cycle`), `offered_tools` (one list per model call) | | `my-agent/skills/` manifest: `id`, `title`, `version`, `path`; approvals by `nina-accountant` |
| 15 | `offered_tools` | no `confirmation_requested` | attachment read by id (`sample-quote.txt`) |
| 17 | `model.usage`, `model.duration_ms`, `model.calls`, `tools[].duration_ms` | | routes YAML (`workshops/15-evaluation/tests/route_runner.py`), `my-agent/routes/`, `my-agent/route-report.json` |
| 18 | `fallback` (`from`, `to`, `reason`), `unknown_outcome.draft_id`, `versions` (`instructions`, `tools`, `skills`, `index`) | | single submission attempt; one fallback call |
| 19 | | | `my-agent/local-mode/specifications/*.md`, `controls/test_*.py`, `MY_AGENT_DISABLE_CONTROL=1` |