# my-agent

This is where you build your agent. It is the **only** folder you edit: code, policy, catalog and attachments alike.

- `harness.py` is a runnable bootstrap: it answers every message with the same cautious sentence and writes the trace of the turn, but calls neither the model nor any tool. Replace it from workshop 03 on.
- `mcp_server.py` is an empty MCP server: it starts and answers the handshake, but exposes no business tool. You will wire it in workshop 09.
- `sandbox/policy.yaml` is the sandbox policy of workshop 10d (inactive, empty allowlist).
- `skills/` is the versioned skills catalog of workshop 14 (`manifest.yaml`, zero *skill*).
- `attachments/` is the read-only attachments area of workshop 15 (empty).
- `local-mode/` is the empty landing structure of workshop 19 (specification of a control; using a *coding agent* is optional).

The workshop tests stay red until the success criterion is met.

Deliverables added along the workshops:

- workshop 17: a route report (`route-report.md` or equivalent);
- workshop 19: specification and checks under `local-mode/`.
