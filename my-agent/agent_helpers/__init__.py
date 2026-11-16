"""Ready-made helpers for your agent: the repetitive code, not the work of the workshops.

Import them from `harness.py` or `mcp_server.py`, for example
`from agent_helpers.trace import Tracer`. Both files put `my-agent/` on the import path.
The model client itself is wired in `harness.py` (`model_client()`).

| Module | What it gives you | What stays yours |
|---|---|---|
| `trace` | `Tracer`: one method per thing that happens in a turn (model call, tool call, state, compaction, memory, mention...), writing the trace in the format the tests read | what you record, and when: the decisions of each workshop |
| `http_client` | the HTTP transport to the business API and the document search (URL, token, timeout, readable errors) | which route to call, input validation, interpreting answers |
| `mcp_client` | listing and calling the tools of an MCP server from the harness | which tools the server exposes, the identity it receives |
| `events` | one builder per event type of the contract | when to emit them and what they say |
| `tool_schema` | an OpenAI tool declaration built from an annotated function | the tool names, parameters, descriptions and validation |

Each `contrat.md` (section « Pistes techniques ») says which helpers fit the workshop.
`mcp_client`, `events` and `trace` rely on `workshop_kit`, available to the harness;
`http_client` and `tool_schema` only need `httpx` and the standard library, so the MCP server
can use them from its own environment.
"""
