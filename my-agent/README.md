# my-agent

This is where you build your agent. It is the **only** folder you edit: code, policy, catalog and attachments alike.

- `harness.py` is a runnable bootstrap that already converses: at each turn it sends the model (through the course proxy) the system prompt, the context of the conversation (`agent_sdk.context`: every message of the previous turns, tool calls and results included) and the message, relays the answer (`text`, then `end`), records the turn in the context and writes the trace of the turn. The `history` parameter of `turn(...)` is only the transcript shown by the interface. It calls no tool. You extend it from workshop 03 on.
- `system_prompt.md` is the system prompt of your agent (workshop 03), loaded by `harness.py` at each turn; its HTML comments are guidance and are not sent to the model.
- `compaction_prompt.md` is the system prompt of the separate model call that writes the compaction summary (workshop 10), loaded like `system_prompt.md`; it starts empty, with guidance in HTML comments.
- `mcp_server.py` is an empty MCP server: it starts and answers the handshake, but exposes no business tool. You will wire it in workshop 06.
- `pyproject.toml` installs `agent_sdk` (editable, at the repository root), the repetitive code you import without modifying it, so you can focus on each workshop's goal. None of it does the work of a workshop:
  - `agent_sdk.contract`: the contract types `Message`, `Event`, `TestUser`;
  - `agent_sdk.trace`: `Tracer`, one method per thing that happens in a turn (`input`, `call_model`/`model_call`, `cycle`, `tool_call`, `state`, `compaction`/`compaction_call`, `memory`, `mention`, `skill_loaded`, `identity`, `limit_reached`, `fallback`, `unknown_outcome`, `versions`, `output`, `write`), plus `memory_entry(...)`; you never assemble the trace JSON yourself, what you record and when stays yours;
  - `agent_sdk.model_client`: `ModelClient` and `ModelUnavailable`, the client of the course model proxy;
  - `agent_sdk.http_client` (from workshop 04): HTTP transport to the business API and the document search (URL read at call time, bearer token, timeout, `ServiceError`); which route to call stays yours;
  - `agent_sdk.mcp_client` (from workshop 06): `list_tools()`, `call_tool()` and `as_openai_tool()` against your MCP server (`MCP_URL`), plus the wiring checklist;
  - `agent_sdk.events`: one builder per event type (`text`, `end`, `step`, `mention`, `interruption`, `compaction`, `confirmation_requested`, `memory`, `sources`...); when to emit them stays yours;
  - `agent_sdk.tool_schema` (from workshop 04): `declare(function)` builds an OpenAI tool declaration from an annotated function and its docstring; no registry, nothing runs by itself;
  - `agent_sdk.sandbox`, `agent_sdk.skills`, `agent_sdk.attachments`: readers of the three data folders below.
- `sandbox/policy.yaml` is the sandbox policy of workshop 07 (step `confinement`).
- `skills/` is the versioned skills catalog of workshop 13 (`manifest.yaml`).
- `attachments/` is the read-only attachments area of workshop 14 (manifest `attachments.yaml`).
- `local-mode/` is the empty landing structure of workshop 17 (specification of a control; using a *coding agent* is optional).

The workshop tests stay red until the success criterion is met.

Deliverables added along the workshops:

- workshop 11: no memory between conversations; a stated preference is only reported in the trace (`preference_reports`);
- workshop 15: own evaluation routes under `routes/`, report `route-report.json`;
- workshop 17: specification and checks under `local-mode/`.
