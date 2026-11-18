"""Serves my-agent/mcp_server.py for `workshop serve`, and serves its new version as soon as a file changes.

The runner keeps the port and swaps the application behind it: `application()` of the module (the
contract of workshop 06) is loaded again after any change to the Python files of my-agent/. A version
that fails to load is reported in the log and through the status route, and the previous version keeps
answering until the file is fixed. Only the very first load must succeed: otherwise the runner exits,
and the stack does not start.

    GET /_workshop/status -> {"signature": ..., "state": "ready" | "error", "detail": ...}

The interface reads this status before each turn (`WORKSHOP_MCP_STATUS_URL`), and waits until the
version it loaded is served.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import time
import traceback
from pathlib import Path

STATUS_PATH = "/_workshop/status"
POLL_SECONDS = 0.5
# A change is loaded once the files stay still this long (an editor may write in several steps).
SETTLE_SECONDS = 0.3
DRAIN_SECONDS = 10.0


def log(message: str) -> None:
    print(f"[mcp-runner] {message}", file=sys.stderr, flush=True)


class Lifespan:
    """Runs the ASGI lifespan of one version of the application (the MCP session manager)."""

    def __init__(self, app) -> None:
        self.app = app
        self.state: dict = {}
        self._receive: asyncio.Queue = asyncio.Queue()
        self._sent: asyncio.Queue = asyncio.Queue()
        self._task: asyncio.Task | None = None
        self.supported = True

    async def _run(self) -> None:
        scope = {
            "type": "lifespan",
            "asgi": {"version": "3.0", "spec_version": "2.0"},
            "state": self.state,
        }
        try:
            await self.app(scope, self._receive.get, self._sent.put)
        except BaseException as exc:  # noqa: BLE001 - an application without lifespan support
            self.supported = False
            await self._sent.put({"type": "lifespan.unsupported", "message": repr(exc)})

    async def startup(self) -> None:
        self._task = asyncio.create_task(self._run())
        await self._receive.put({"type": "lifespan.startup"})
        message = await self._sent.get()
        if message["type"] == "lifespan.startup.failed":
            raise RuntimeError(message.get("message") or "lifespan startup failed")

    async def shutdown(self) -> None:
        if self._task is None:
            return
        if self.supported and not self._task.done():
            await self._receive.put({"type": "lifespan.shutdown"})
            try:
                await asyncio.wait_for(self._sent.get(), timeout=DRAIN_SECONDS)
            except TimeoutError:
                pass
        if not self._task.done():
            self._task.cancel()
        await asyncio.gather(self._task, return_exceptions=True)


class Version:
    def __init__(self, app, lifespan: Lifespan) -> None:
        self.app = app
        self.lifespan = lifespan
        self.active = 0


class Dispatcher:
    """The ASGI application uvicorn serves: hands each request to the current version."""

    def __init__(self) -> None:
        self.current: Version | None = None
        self.status = {"signature": None, "state": "starting", "detail": ""}

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "lifespan":
            return
        if scope["type"] == "http" and scope["path"] == STATUS_PATH:
            await _json(send, 200, self.status)
            return
        version = self.current
        if version is None:
            if scope["type"] == "http":
                await _json(send, 503, self.status)
            return
        version.active += 1
        try:
            await version.app({**scope, "state": dict(version.lifespan.state)}, receive, send)
        finally:
            version.active -= 1


async def _json(send, code: int, body: dict) -> None:
    payload = json.dumps(body).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(payload)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": payload})


def load_application(folder: Path):
    path = folder / "mcp_server.py"
    if not path.exists():
        raise FileNotFoundError(f"File missing from my-agent/: {path}")
    spec = importlib.util.spec_from_file_location("my_agent_mcp_server", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["my_agent_mcp_server"] = module
    spec.loader.exec_module(module)
    return module.application()


async def swap(dispatcher: Dispatcher, folder: Path, signature, changed: list[str]) -> bool:
    """Loads and starts the new version; on failure, keeps the previous one. True on success."""
    from workshop_config.reload import describe_error, digest, purge_modules

    if changed:
        purge_modules(folder, changed)
    try:
        app = load_application(folder)
        lifespan = Lifespan(app)
        await lifespan.startup()
    except Exception as exc:  # noqa: BLE001 - any error of the student's code is reported
        detail = describe_error(exc, folder)
        traceback.print_exc()
        log(f"my-agent/mcp_server.py could not be loaded: {detail}")
        dispatcher.status = {"signature": digest(signature), "state": "error", "detail": detail}
        return False
    previous, dispatcher.current = dispatcher.current, Version(app, lifespan)
    dispatcher.status = {"signature": digest(signature), "state": "ready", "detail": ""}
    if changed:
        log(f"MCP server reloaded (changed: {', '.join(changed)})")
    if previous is not None:
        deadline = time.monotonic() + DRAIN_SECONDS
        while previous.active and time.monotonic() < deadline:
            await asyncio.sleep(0.05)
        await previous.lifespan.shutdown()
    return True


async def watch(dispatcher: Dispatcher, folder: Path, signature) -> None:
    from workshop_config.reload import changed_files, source_signature

    while True:
        await asyncio.sleep(POLL_SECONDS)
        current = source_signature(folder)
        if current == signature:
            continue
        # Wait until the editor has finished writing.
        while True:
            await asyncio.sleep(SETTLE_SECONDS)
            settled = source_signature(folder)
            if settled == current:
                break
            current = settled
        changed = changed_files(signature, current)
        signature = current
        await swap(dispatcher, folder, current, changed)


async def main() -> int:
    import uvicorn
    from workshop_config import repo_path, settings
    from workshop_config.reload import source_signature

    folder = repo_path(settings.my_agent_dir).resolve()
    host = os.environ.get("MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("MCP_PORT", "8004"))
    dispatcher = Dispatcher()
    signature = source_signature(folder)
    if not await swap(dispatcher, folder, signature, []):
        log("Fix my-agent/mcp_server.py, then start the workshop again.")
        return 1
    server = uvicorn.Server(
        uvicorn.Config(dispatcher, host=host, port=port, lifespan="off", log_level="info")
    )
    watcher = asyncio.create_task(watch(dispatcher, folder, signature))
    log(f"Serving my-agent/mcp_server.py on http://{host}:{port}, reloaded when my-agent/ changes.")
    try:
        await server.serve()
    finally:
        watcher.cancel()
        await asyncio.gather(watcher, return_exceptions=True)
        if dispatcher.current is not None:
            await dispatcher.current.lifespan.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
