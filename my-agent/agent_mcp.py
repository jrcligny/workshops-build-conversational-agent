"""MCP client of my agent: the tools now live behind the MCP server (my-agent/mcp_server.py).

MCP_URL points to a running server (devstack). Without it (test runs), the agent starts its own
server once per process, on a free local port, in a background thread.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import threading
import time
from typing import Any

import mcp_server

_lock = threading.Lock()
_loop: asyncio.AbstractEventLoop | None = None
_local_url: str | None = None
_catalog: list[dict] | None = None


def _runner() -> asyncio.AbstractEventLoop:
    """Private event loop in a daemon thread: the harness is synchronous and may run inside another loop."""
    global _loop
    with _lock:
        if _loop is None:
            _loop = asyncio.new_event_loop()
            threading.Thread(target=_loop.run_forever, name="mcp-client-loop", daemon=True).start()
    return _loop


def _run(coro, timeout: float = 60) -> Any:
    return asyncio.run_coroutine_threadsafe(coro, _runner()).result(timeout)


def server_url() -> str:
    url = os.environ.get("MCP_URL")
    if url:
        return url.rstrip("/") + ("" if url.rstrip("/").endswith(mcp_server.MCP_PATH) else mcp_server.MCP_PATH)
    global _local_url
    with _lock:
        if _local_url is None:
            import uvicorn

            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            config = uvicorn.Config(mcp_server.application(), host="127.0.0.1", port=port, log_level="warning")
            server = uvicorn.Server(config)
            threading.Thread(target=server.run, name="mcp-server", daemon=True).start()
            deadline = time.time() + 15
            while not server.started and time.time() < deadline:
                time.sleep(0.05)
            _local_url = f"http://127.0.0.1:{port}{mcp_server.MCP_PATH}"
    return _local_url


def _client(token: str):
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client
    from mcp.shared._httpx_utils import create_mcp_http_client

    http = create_mcp_http_client(headers={"Authorization": f"Bearer {token}"})
    return Client(streamable_http_client(server_url(), http_client=http))


def user_token(user) -> str:
    """The user's own token, as received from the interface.

    Without one (local test runs), an entry token for the conversation's user stands in for the interface's
    session token: the agent never mints an application token itself.
    """
    if user.app_token:
        return user.app_token
    from workshop_kit.apps.business_api.auth import issue_token

    return issue_token(user.id, user.role, user.organization, typ="entry")


def identity_record(user, token: str) -> dict:
    """What the trace keeps about the identity: who, which token type was received, how it was used."""
    import jwt

    try:
        received = jwt.decode(token, options={"verify_signature": False}).get("typ")
    except jwt.PyJWTError:
        received = "unreadable"
    return {
        "user": user.id,
        "role": user.role,
        "organization": user.organization,
        "received_token_type": received,
        "relayed_to_tool_server": "user token, in the request header (value never traced)",
        "business_api_token": "exchanged by the tool server for an application token on behalf of the user",
        "service_account": False,
    }


def tool_specs(token: str) -> list[dict]:
    """Tool catalog published by the server, in the model's function format (cached per process)."""
    global _catalog
    if _catalog is None:

        async def fetch():
            async with _client(token) as client:
                return (await client.list_tools()).tools

        tools = _run(fetch())
        _catalog = [
            {
                "type": "function",
                "function": {"name": t.name, "description": t.description or "", "parameters": t.input_schema},
            }
            for t in tools
        ]
    return _catalog


def call(token: str, name: str, arguments: dict) -> dict:
    async def invoke():
        async with _client(token) as client:
            return await client.call_tool(name, arguments)

    result = _run(invoke())
    data = result.structured_content
    if isinstance(data, dict) and set(data) == {"result"}:
        data = data["result"]
    if not isinstance(data, dict):
        text = "".join(getattr(c, "text", "") for c in result.content or [])
        try:
            data = json.loads(text)
        except (TypeError, ValueError):
            data = {"status": "error" if result.is_error else "ok", "detail": text}
    if result.is_error and data.get("status") != "error":
        data = {"status": "error", **data}
    return data
