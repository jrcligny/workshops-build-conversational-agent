"""Calling an MCP server from the harness (workshop 06 onwards), synchronously.

What it gives you:
- `list_tools(token=None)`: the tools the server exposes, as
  `[{"name", "description", "input_schema"}]`;
- `call_tool(name, arguments, token=None)`: runs one tool and returns
  `{"is_error", "structured", "text"}`;
- `as_openai_tool(tool)`: turns one listed tool into a declaration for `generate(tools=...)`.
The server URL is read from `MCP_URL` at each call (`http://127.0.0.1:8004/mcp` by default).
`token` is sent as `Authorization: Bearer <token>` (workshop 07).

What stays yours: the tools the server exposes and how they reach the business API
(`mcp_server.py`), recording `transport: "mcp"` on each call in the trace, the identity sent
to the server and what the server does with it (07).

Wiring checklist for workshop 06:
1. start the server: `uv run --project my-agent python my-agent/mcp_server.py`;
2. declare your tools in `mcp_server.py` (`@server.tool()`), wired to the business API;
3. from the harness, offer the model `[as_openai_tool(t) for t in list_tools(token)]` and run
   each requested call with `call_tool`;
4. trace each call with `transport: "mcp"`.
"""

from __future__ import annotations

import asyncio
import os
import threading
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

DEFAULT_MCP_URL = "http://127.0.0.1:8004/mcp"


def server_url() -> str:
    return os.environ.get("MCP_URL", DEFAULT_MCP_URL)


def list_tools(token: str | None = None, url: str | None = None) -> list[dict]:
    async def run(session: ClientSession):
        result = await session.list_tools()
        return [
            {
                "name": t.name,
                "description": t.description or "",
                "input_schema": getattr(t, "input_schema", None) or getattr(t, "inputSchema", None) or {},
            }
            for t in result.tools
        ]

    return _with_session(run, token, url)


def call_tool(name: str, arguments: dict, token: str | None = None, url: str | None = None) -> dict:
    async def run(session: ClientSession):
        result = await session.call_tool(name, arguments)
        structured = getattr(result, "structured_content", None)
        if structured is None:
            structured = getattr(result, "structuredContent", None)
        is_error = getattr(result, "is_error", None)
        if is_error is None:
            is_error = getattr(result, "isError", False)
        text = "\n".join(getattr(c, "text", "") for c in result.content or [] if getattr(c, "text", None))
        return {"is_error": bool(is_error), "structured": structured, "text": text}

    return _with_session(run, token, url)


def as_openai_tool(tool: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema") or {"type": "object", "properties": {}},
        },
    }


def _with_session(run, token: str | None, url: str | None) -> Any:
    async def main():
        headers = {"Authorization": f"Bearer {token}"} if token else None
        async with create_mcp_http_client(headers=headers) as http:
            async with streamable_http_client(url or server_url(), http_client=http) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    return await run(session)

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(main())
    # Called from inside an event loop: run in a separate thread with its own loop.
    box: dict[str, Any] = {}

    def worker():
        try:
            box["value"] = asyncio.run(main())
        except BaseException as exc:  # noqa: BLE001
            box["error"] = exc

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    if "error" in box:
        raise box["error"]
    return box["value"]
