"""The MCP runner serves the new my-agent/mcp_server.py after a change, and keeps the last good one on error."""

import asyncio
import sys

import httpx
from workshop_config.reload import source_signature
from workshop_tools import mcp_runner

SERVER = """
VERSION = {version!r}
MCP_PATH = "/mcp"


def application():
    async def app(scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({{"type": "lifespan.startup.complete"}})
                else:
                    await send({{"type": "lifespan.shutdown.complete"}})
                    return
        await send({{"type": "http.response.start", "status": 200, "headers": []}})
        await send({{"type": "http.response.body", "body": VERSION.encode()}})
    return app
"""


def test_reload_and_error_keep_serving(tmp_path):
    folder = tmp_path / "my-agent"
    folder.mkdir()
    server = folder / "mcp_server.py"

    async def scenario():
        dispatcher = mcp_runner.Dispatcher()
        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=dispatcher), base_url="http://mcp"
        )

        async def reload(text):
            before = source_signature(folder)
            server.write_text(text, encoding="utf-8")
            after = source_signature(folder)
            return await mcp_runner.swap(
                dispatcher, folder, after, ["mcp_server.py"] if before else []
            )

        assert await reload(SERVER.format(version="one-v1"))
        assert (await client.get("/mcp")).text == "one-v1"
        assert await reload(SERVER.format(version="second-v2"))
        assert (await client.get("/mcp")).text == "second-v2"
        assert not await reload("VERSION = = 1\n")
        status = (await client.get(mcp_runner.STATUS_PATH)).json()
        assert status["state"] == "error"
        assert "my-agent/mcp_server.py, line 1: SyntaxError" in status["detail"]
        assert (await client.get("/mcp")).text == "second-v2"
        await dispatcher.current.lifespan.shutdown()

    asyncio.run(scenario())
    sys.modules.pop("my_agent_mcp_server", None)
