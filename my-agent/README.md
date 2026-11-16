# my-agent

This is where you build your agent. It is the **only** folder you edit: code, policy, catalog and attachments alike.

- `harness.py` is a runnable bootstrap that already converses: at each turn it sends the model (through the course proxy) the system prompt, the history and the message, relays the answer (`text`, then `end`) and writes the trace of the turn. It calls no tool. You extend it from workshop 03 on.
- `system_prompt.md` is the system prompt of your agent (workshop 03), loaded by `harness.py` at each turn; its HTML comments are guidance and are not sent to the model.
- `mcp_server.py` is an empty MCP server: it starts and answers the handshake, but exposes no business tool. You will wire it in workshop 09.
- `agent_helpers/` holds the repetitive code, so you can focus on each workshop's goal. None of it does the work of a workshop:
  - `trace.py`: `Tracer`, one method per thing that happens in a turn (`input`, `call_model`/`model_call`, `cycle`, `tool_call`, `state`, `compaction`, `memory`, `mention`, `skill_loaded`, `identity`, `limit_reached`, `fallback`, `unknown_outcome`, `versions`, `output`, `write`), plus `memory_entry(...)`; you never assemble the trace JSON yourself, what you record and when stays yours;
  - `http_client.py` (from workshop 04): HTTP transport to the business API and the document search (URL read at call time, bearer token, timeout, `ServiceError`); which route to call stays yours;
  - `mcp_client.py` (from workshop 09): `list_tools()`, `call_tool()` and `as_openai_tool()` against your MCP server (`MCP_URL`), plus the wiring checklist;
  - `events.py`: one builder per event type (`text`, `end`, `step`, `mention`, `interruption`, `compaction`, `confirmation_requested`, `memory`, `sources`...); when to emit them stays yours;
  - `tool_schema.py` (from workshop 04): `declare(function)` builds an OpenAI tool declaration from an annotated function and its docstring; no registry, nothing runs by itself.
- `sandbox/policy.yaml` is the sandbox policy of workshop 10d (inactive, empty allowlist).
- `skills/` is the versioned skills catalog of workshop 14 (`manifest.yaml`, zero *skill*).
- `attachments/` is the read-only attachments area of workshop 15 (empty).
- `local-mode/` is the empty landing structure of workshop 19 (specification of a control; using a *coding agent* is optional).

The workshop tests stay red until the success criterion is met.

Deliverables added along the workshops:

- workshop 17: a route report (`route-report.md` or equivalent);
- workshop 19: specification and checks under `local-mode/`.
