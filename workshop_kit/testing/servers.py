"""Starts the test processes on local ports.

Works on Windows and on Unix: no fork, no POSIX signals. The uvicorn
servers run in threads and stop through `should_exit`, not through SIGTERM.
"""

from __future__ import annotations

import socket
import threading
import time

import httpx
import uvicorn


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_port(host: str, port: int, timeout: float = 8.0) -> None:
    """Waits until the TCP port accepts a connection (no HTTP GET)."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        with socket.socket() as s:
            s.settimeout(0.2)
            try:
                if s.connect_ex((host, port)) == 0:
                    return
            except Exception as exc:  # noqa: BLE001
                last = exc
        time.sleep(0.05)
    raise RuntimeError(f"port unreachable: {host}:{port} ({last})")


def wait_for(url: str, timeout: float = 8.0) -> None:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=0.5)
            if r.status_code < 500:
                return
        except Exception as exc:  # noqa: BLE001
            last = exc
        time.sleep(0.05)
    raise RuntimeError(f"service unreachable: {url} ({last})")


def start_uvicorn(app, port: int) -> uvicorn.Server:
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server
