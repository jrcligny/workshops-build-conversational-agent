"""What your agent imports without modifying it: the repetitive code, not the work of the workshops.

The package is installed in the `my-agent` project (editable dependency), so `harness.py` and
`mcp_server.py` import it directly, for example `from agent_sdk.trace import Tracer`.
The model client itself is wired in `harness.py` (`model_client()`).

| Module | What it gives you | What stays yours |
|---|---|---|
| `contract` | the types of the harness contract: `Message`, `Event`, `TestUser`, `HarnessNotImplemented` | what your `Harness.turn` yields |
| `context` | `context(conversation_id)`: every message the model has seen (user, assistant with `tool_calls`, `tool` results), kept between turns, and the rolling summary; `seed` for written conversations (tests) | what you record, clear and summarize (10) |
| `events` | one builder per event type of the contract | when to emit them and what they say |
| `trace` | `Tracer`: one method per thing that happens in a turn (model call, tool call, state, compaction, memory, mention...), writing the trace in the format the tests read (through `trace_store`) | what you record, and when: the decisions of each workshop |
| `model_client` | `ModelClient` and `ModelUnavailable`, the OpenAI-compatible client of the course proxy | the prompt, the tools offered, the fallback decision |
| `http_client` | the HTTP transport to the business API and the document search (URL, token, timeout, readable errors) | which route to call, input validation, interpreting answers |
| `mcp_client` | listing and calling the tools of an MCP server from the harness | which tools the server exposes, the identity it receives |
| `tool_schema` | an OpenAI tool declaration built from an annotated function | the tool names, parameters, descriptions and validation |
| `sandbox`, `skills`, `attachments` | readers of `my-agent/sandbox/policy.yaml`, `my-agent/skills/` and `my-agent/attachments/` | the policy, the catalog and what the agent does with an attachment |

Each `contrat.md` (section « Pistes techniques ») says which modules fit the workshop.
"""

from agent_sdk.contract import Event, HarnessNotImplemented, Message, TestUser
from agent_sdk.model_client import ModelClient, ModelUnavailable
from agent_sdk.trace import Tracer

__all__ = ["Event", "HarnessNotImplemented", "Message", "ModelClient", "ModelUnavailable", "TestUser", "Tracer"]
