"""Empty MCP server of the shell.

It starts, answers the MCP protocol handshake (official Python SDK `mcp`)
and exposes no business tool. You will wire it to the business API in workshop 09.
Planned transport: streamable HTTP, stateless mode.
"""

from __future__ import annotations

import os

from mcp.server import MCPServer

NAME = "workshop-tools"
VERSION = "0.1.0"
MCP_PATH = "/mcp"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8004


def create_server() -> MCPServer:
    return MCPServer(
        name=NAME,
        version=VERSION,
        instructions=(
            "Empty shell: no business tool is exposed yet. "
            "In workshop 09, you will move the tools to this stateless server "
            "and wire them to the business API."
        ),
    )


def application():
    """Starlette application served by uvicorn (tests and local run)."""
    return create_server().streamable_http_app(
        stateless_http=True,
        json_response=True,
        streamable_http_path=MCP_PATH,
        host=DEFAULT_HOST,
    )


if __name__ == "__main__":
    port = int(os.environ.get("MCP_PORT", str(DEFAULT_PORT)))
    host = os.environ.get("MCP_HOST", DEFAULT_HOST)
    create_server().run(
        transport="streamable-http",
        host=host,
        port=port,
        stateless_http=True,
        json_response=True,
        streamable_http_path=MCP_PATH,
    )
