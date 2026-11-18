"""Start the complete local workshop stack, keeping Python projects isolated."""

from __future__ import annotations

import os
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import ExitStack, closing
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
TOOLS_SOURCE = REPO_ROOT / "tooling" / "cli" / "src"
UI_ROOT = REPO_ROOT / "clients" / "chat_ui"
PROJECTS = {
    "business_api": REPO_ROOT / "business" / "business_api",
    "docs_search": REPO_ROOT / "business" / "docs_search",
    "proxy": REPO_ROOT / "gateway" / "model_gateway",
    "mcp": REPO_ROOT / "my-agent",
    "interface": REPO_ROOT / "gateway" / "agent_gateway",
    "chat_ui": UI_ROOT,
}
HOST = "127.0.0.1"
LOGS = REPO_ROOT / ".workshop" / "logs"
# Read by agent_gateway.loader: the interface waits until the MCP runner serves the my-agent/ it loaded.
MCP_STATUS_ENV = "WORKSHOP_MCP_STATUS_URL"


@dataclass(frozen=True)
class Service:
    name: str
    port: int
    command: tuple[str, ...]
    cwd: Path
    env: dict[str, str]
    health_path: str | None = "/health"

    @property
    def project(self) -> Path:
        return PROJECTS[self.name]

    @property
    def url(self) -> str:
        return f"http://{HOST}:{self.port}"


def services(port_offset: int = 0) -> list[Service]:
    ports = {
        "business_api": 8001 + port_offset,
        "docs_search": 8002 + port_offset,
        "proxy": 8003 + port_offset,
        "mcp": 8004 + port_offset,
        "interface": 8000 + port_offset,
        "chat_ui": 8080 + port_offset,
    }
    if port_offset < 0 or any(not 1 <= port <= 65535 for port in ports.values()):
        raise ValueError("The port offset must be between 0 and 57455.")
    env = {
        **os.environ,
        "PYTHONUNBUFFERED": "1",
        "PYTHONPATH": os.pathsep.join(
            [str(TOOLS_SOURCE)]
            + ([os.environ["PYTHONPATH"]] if os.environ.get("PYTHONPATH") else [])
        ),
        "BUSINESS_API_URL": f"http://{HOST}:{ports['business_api']}",
        "DOCS_SEARCH_URL": f"http://{HOST}:{ports['docs_search']}",
        "PROXY_URL": f"http://{HOST}:{ports['proxy']}",
        "MCP_URL": f"http://{HOST}:{ports['mcp']}/mcp",
        "INTERFACE_URL": f"http://{HOST}:{ports['interface']}",
        "WORKSHOP_CHAT_BACKEND_URL": f"http://{HOST}:{ports['interface']}",
        "MCP_HOST": HOST,
        "MCP_PORT": str(ports["mcp"]),
    }
    modules = {
        "business_api": "business_api.app:app",
        "docs_search": "docs_search.app:app",
        "proxy": "model_gateway.app:app",
        "interface": "agent_gateway.chat_app:app",
    }
    result = []
    for name in ("business_api", "docs_search", "proxy", "mcp", "interface", "chat_ui"):
        port = ports[name]
        cwd = REPO_ROOT
        service_env = dict(env)
        project = PROJECTS[name]
        python = project / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        service_env["VIRTUAL_ENV"] = str(project / ".venv")
        health_path = "/health"
        if name == "mcp":
            # Serves my-agent/mcp_server.py and serves it again whenever my-agent/ changes.
            command = (str(python), "-m", "workshop_tools.mcp_runner")
            health_path = None  # The student's MCP server has no health endpoint.
        elif name == "interface":
            service_env[MCP_STATUS_ENV] = f"http://{HOST}:{ports['mcp']}/_workshop/status"
            command = (
                str(python), "-m", "uvicorn", modules[name],
                "--host", HOST, "--port", str(port),
            )
        elif name == "chat_ui":
            command = (
                str(python), "-m", "chainlit", "run", "src/chat_ui/app.py",
                "--host", HOST, "--port", str(port), "--headless",
            )
            cwd = UI_ROOT
            service_env["CHAINLIT_APP_ROOT"] = str(UI_ROOT)
            service_env["VIRTUAL_ENV"] = str(UI_ROOT / ".venv")
            health_path = "/"
        else:
            command = (
                str(python), "-m", "uvicorn", modules[name],
                "--host", HOST, "--port", str(port),
            )
        result.append(Service(name, port, command, cwd, service_env, health_path))
    return result


def check_ports(stack: list[Service]) -> None:
    """Never reuse or stop a pre-existing service, even if its health check succeeds."""
    for service in stack:
        try:
            with socket.socket() as sock:
                if os.name == "nt":
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                sock.bind((HOST, service.port))
        except OSError as exc:
            raise RuntimeError(
                f"Port {service.port} ({service.name}) is unavailable. "
                "No existing service was stopped. Use --port-offset 10 (or another free range)."
            ) from exc


def _has_table(path: Path, table: str) -> bool:
    if not path.exists():
        return False
    with closing(sqlite3.connect(path)) as conn:
        return conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone() is not None


def initialize_data(reset: bool = False, service_name: str | None = None) -> None:
    """Initialize missing databases only; resetting existing workshop work is opt-in."""
    from workshop_config import repo_path, settings

    if service_name in (None, "business_api") and (reset or not _has_table(repo_path(settings.business_api_db), "users")):
        from business_api.seed_data import load_dataset

        print("Initializing the standard business dataset.", flush=True)
        load_dataset("standard")
    if service_name in (None, "docs_search") and (reset or not _has_table(repo_path(settings.docs_search_db), "passages")):
        from docs_search.indexing import rebuild

        print("Building the document index.", flush=True)
        rebuild()


def wait_ready(service: Service, process: subprocess.Popen, timeout: float = 60) -> None:
    import httpx

    deadline = time.monotonic() + timeout
    tick = threading.Event()
    with httpx.Client(timeout=1, trust_env=False) as client:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"{service.name} exited during startup. See {LOGS / (service.name + '.log')}")
            try:
                if service.health_path is None:
                    with socket.create_connection((HOST, service.port), timeout=1):
                        return
                elif client.get(service.url + service.health_path).status_code == 200:
                    return
            except (OSError, httpx.HTTPError):
                pass
            tick.wait(0.1)
    raise RuntimeError(f"{service.name} did not become ready. See {LOGS / (service.name + '.log')}")


def stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
    except ProcessLookupError:
        pass


def supervise(stack: list[Service], check_only: bool = False) -> int:
    """Each service is a direct Python child, not an unsupervised uv wrapper."""
    processes: list[tuple[Service, subprocess.Popen]] = []
    LOGS.mkdir(parents=True, exist_ok=True)
    with ExitStack() as logs:
        try:
            for service in stack:
                log = logs.enter_context((LOGS / f"{service.name}.log").open("w", encoding="utf-8"))
                print(f"Starting {service.name}: {service.url}", flush=True)
                process = subprocess.Popen(
                    service.command, cwd=service.cwd, env=service.env,
                    stdout=log, stderr=subprocess.STDOUT,
                    # Ctrl+C is handled by the launcher, which stops its own children.
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
                    start_new_session=os.name != "nt",
                )
                processes.append((service, process))
                wait_ready(service, process)
            if check_only:
                print("All six isolated services are ready. Stopping validation stack.", flush=True)
                return 0
            print(f"\nChat ready: {stack[-1].url}\nLogs: {LOGS}\nPress Ctrl+C to stop all services.", flush=True)
            tick = threading.Event()
            while True:
                for service, process in processes:
                    if process.poll() is not None:
                        raise RuntimeError(f"{service.name} stopped. See {LOGS / (service.name + '.log')}")
                tick.wait(0.5)
        except KeyboardInterrupt:
            print("\nStopping the workshop services.", flush=True)
            return 0
        finally:
            for _, process in reversed(processes):
                stop_process(process)


def serve(port_offset: int = 0, reset_data: bool = False, check_only: bool = False) -> int:
    """Sync each project's own dependencies, then run the complete local stack."""
    previous_handler = signal.getsignal(signal.SIGTERM)

    def stop_on_signal(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop_on_signal)
    try:
        stack = services(port_offset)
        check_ports(stack)
        uv = shutil.which("uv")
        if uv is None:
            raise RuntimeError("uv is required to install each service project's own dependencies.")
        for service in stack:
            print(f"Synchronizing {service.name}: {service.project}", flush=True)
            subprocess.run(
                [uv, "sync", "--project", str(service.project), "--locked"],
                cwd=REPO_ROOT,
                env={key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"},
                check=True,
            )
        for service in stack[:2]:
            command = [service.command[0], "-m", "workshop_tools.devstack", "--initialize", service.name]
            if reset_data:
                command.append("--reset-data")
            subprocess.run(command, cwd=service.cwd, env=service.env, check=True)
        return supervise(stack, check_only=check_only)
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError, RuntimeError, sqlite3.Error, subprocess.CalledProcessError) as exc:
        print(f"Cannot start the workshop: {exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous_handler)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Initialize a service's own dataset.")
    parser.add_argument("--initialize", required=True, choices=("business_api", "docs_search"))
    parser.add_argument("--reset-data", action="store_true")
    args = parser.parse_args()
    initialize_data(args.reset_data, args.initialize)