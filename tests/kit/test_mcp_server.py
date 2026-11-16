"""The shell's MCP server starts and exposes no tool."""

from __future__ import annotations

import asyncio

import pytest
from mcp import Client

from workshop_kit.shell.loader import load_mcp_server
from workshop_kit.testing.servers import free_port, start_uvicorn, wait_for_port

pytestmark = pytest.mark.shell


@pytest.fixture(scope="module")
def mcp_server_url():
    module = load_mcp_server()
    port = free_port()
    server = start_uvicorn(module.application(), port)
    wait_for_port("127.0.0.1", port)
    yield f"http://127.0.0.1:{port}{module.MCP_PATH}"
    server.should_exit = True


def test_mcp_server_starts_and_lists_zero_tools(mcp_server_url):
    async def _check():
        async with Client(mcp_server_url) as client:
            assert client.server_info is not None
            assert client.server_info.name == "workshop-tools"
            result = await client.list_tools()
            assert result.tools == []

    asyncio.run(_check())
