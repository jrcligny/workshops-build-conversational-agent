# my-agent

This is where you build your agent. It is the **only** folder where you write code.

- `harness.py` is an empty shell: it implements neither the loop nor the *system prompt*.
- `mcp_server.py` is an empty MCP server: it starts and answers the handshake, but exposes no business tool. You will wire it in workshop 09.
- `local-mode/` is the empty landing structure of workshop 19 (specification of a control; using a *coding agent* is optional).

The workshop tests stay red until the success criterion is met.

Deliverables added along the workshops:

- workshop 11: `trace_queries.py`, with the functions `intermediate_reads_share` and `incompatible_domains`;
- workshop 17: a route report (`route-report.md` or equivalent);
- workshop 19: specification and checks under `local-mode/`.
