# Agent ↔ tests interface contract

This contract is stable across all workshops. The capabilities not used yet (steps, interruption, confirmation, sources, mentions, attachments) exist in the protocol and stay inactive until the workshop that activates them.

## Chat entry point

The chat interface is `workshop_kit/shell/chat_app.py`.

| Element | Contract |
|---|---|
| Creation | `POST /conversations` with `user_id`, `role`, `organization`, optionally `app_token` and `limits`. Response: `{ "id": ... }`. |
| Turn | `POST /conversations/{id}/messages` with `{ "text": "..." }`. Server-sent events (SSE) response. |
| Events (workshop 03) | `text` (chunks, field `content`) then `end` (field `ok`). An `error` event reports a failure of the shell. |
| Multi-turn | The same conversation id is reused. The *harness* must replay the history in the model input. |

The tests use the internal client (`workshop_tests/testing/chat_client.py`), not a browser.
The standard Chainlit UI in `workshop_kit/chat-ui/` consumes the same HTTP/SSE
contract from its own Python environment. From the repository root, run
`uv run --project workshop_kit/bootstrap workshop serve` to start
the complete environment, including that UI.

## Attachments (reserved for workshop 15)

The contract already provides the entry point, with no file in the shell:

| Element | Contract |
|---|---|
| List | `GET /attachments` returns `{ "attachments": [...] }` from the area `my-agent/attachments/` (setting `attachments_dir`). In the shell, the list is empty. |
| Turn | The body of `POST /conversations/{id}/messages` accepts an optional `attachments` field (list of ids). It is passed to the *harness* (`turn(..., attachments=...)`). |
| Reserved event | `attachment` may report that an attached document was read. |

No sample quote is dropped in the shell. You will fill the area in workshop 15.

## MCP server (empty shell, wired in workshop 09)

The shell includes `my-agent/mcp_server.py`: an MCP server that starts and answers the handshake, written with the official Python SDK `mcp`. It exposes **no business tool**. Planned transport: streamable HTTP (`streamable-http`), stateless mode, endpoint `/mcp` (port 8004 by default).

```powershell
uv run --project my-agent python my-agent/mcp_server.py
```

Run this command from the repository root; the MCP server uses its own project,
lockfile and environment. In workshop 09, you will move the tools there and wire
them to the business API. The workshop 09 tests stay red until this is done.

## Traces

One trace per turn, in a JSONL file (`turns.jsonl`) in the configured folder (`traces/` by default). Fields required from workshop 03:

- conversation and turn ids, `timestamp`;
- `input` sent to the model: `system_prompt`, `history`, new `message`;
- `model`: id exposed by the proxy, tokens, duration, stop reason;
- `output`: assistant text;
- `tools`: empty list in workshop 03;
- no secret (Azure key, token).

Later workshops add fields such as `cycles`, `compaction`, `state` (working memory), `identity` and component versions; each workshop guide and its tests name the fields they read.

If you go through the client `workshop_kit.shell.model_client.ModelClient`, the model calls can be complemented by your own trace writes (`workshop_kit.shell.tracer.write`).

## Harness to implement

In `my-agent/harness.py`, a `Harness` class exposes `turn(conversation_id, message, user, history, attachments=None, interrupt_requested=False, confirmation=False, limits=None)` and yields `Event` objects (see `workshop_kit/shell/harness_contract.py`). The shipped shell raises `NotImplementedError`: this is intended.

## Other locations of the shell

| Location | Role | State in the shell |
|---|---|---|
| `my-agent/sandbox/policy.yaml` | Sandbox policy (workshop 10d), read by `workshop_kit/services/sandbox/interface.py` (setting `sandbox_policy_file`) | Present, policy inactive, empty allowlist |
| `my-agent/skills/` | Versioned skills catalog (workshop 14): `manifest.yaml` + `<id>/SKILL.md`, read by `workshop_kit/services/skills_catalog/catalog.py` (setting `skills_dir`) | Valid manifest, zero *skill* |
| `my-agent/attachments/` | Read-only area for attached documents (workshop 15), read by `workshop_kit/services/attachments/registry.py` (setting `attachments_dir`) | Empty |
| `workshops/17-evaluation/routes/` | Evaluation routes and their checksum (workshops 17 and 19) | Empty set, checksum present |
| `my-agent/local-mode/` | Development mode landing (workshop 19, *coding agent* optional) | Empty structure (`specifications/`, `controls/`) |

## Reserved events and gestures (workshops 06, 07, 10b, 10d)

| Element | Contract |
|---|---|
| Step | SSE event `step` during a turn with several cycles (workshop 06). |
| Interruption | `POST /conversations/{id}/interruption`, or the `interrupt` field of the message. The *harness* receives `interrupt_requested=True` and stops the turn without a new call (event `interruption`). |
| Compaction | SSE event `compaction` (or a `mention` announcing it) when the history has been compacted (workshop 07). The trace describes the moment, the replaced exchanges, the summary and the items kept verbatim. |
| Confirmation | `POST /conversations/{id}/confirmation` with `{ "confirmed": true }`. The next turn receives `confirmation=True` (workshop 10b). The `confirmation_requested` event precedes the gesture. |
| Limits | Optional `limits` field of `POST /conversations` (`duration_s`, `token_budget`), passed to the *harness* (workshop 10d). |
