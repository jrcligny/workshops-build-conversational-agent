"""Shared pytest fixtures: applications, proxy, traces, dataset.

Loaded as a pytest plugin by `tooling/cli/pyproject.toml`, so that the kit tests
(`<component>/tests/`, `tooling/cli/integration/`) and the workshop tests (`workshops/*/tests/`) share them.
"""

from __future__ import annotations

import os
import shutil

import httpx
import pytest

# Simulated mode by default; PROXY_MODE / MODEL_MODE from the environment or .env are honoured.
os.environ.setdefault("OBSERVATION_TOKEN", "workshop-observation")
os.environ.setdefault("TOKEN_SECRET", "workshop-test-secret-32-bytes-long!")

from business_api.app import app as business_app  # noqa: E402
from business_api.db import reassign  # noqa: E402
from business_api.seed_data import load_dataset  # noqa: E402
from docs_search.app import app as docs_app, clear_log as clear_docs_log  # noqa: E402
from docs_search.indexing import rebuild  # noqa: E402
from model_gateway.app import app as proxy_app, clear_log as clear_proxy_log  # noqa: E402
from model_gateway.tokens import reset_usage  # noqa: E402
from agent_sdk import trace_store as tracer  # noqa: E402
from agent_gateway.chat_app import app as interface_app, reset_conversations  # noqa: E402
from workshop_config import settings  # noqa: E402
from agent_testkit.chat_client import ChatClient  # noqa: E402
from agent_testkit.servers import start_uvicorn, free_port, wait_for, wait_for_port  # noqa: E402

OBSERVATION_TOKEN = "workshop-observation"


@pytest.fixture(scope="session")
def session_dir(tmp_path_factory):
    root = tmp_path_factory.mktemp("session")
    settings.business_api_db = str(root / "business_api.db")
    settings.docs_search_db = str(root / "docs_search.db")
    settings.traces_dir = str(root / "traces")
    settings.token_secret = "workshop-test-secret-32-bytes-long!"
    settings.observation_token = OBSERVATION_TOKEN
    reassign(settings.business_api_db)
    load_dataset("standard")
    rebuild(settings.docs_search_db)
    return root


@pytest.fixture(scope="session")
def services(session_dir):
    apps = {
        "business_api": business_app,
        "docs_search": docs_app,
        "proxy": proxy_app,
        "interface": interface_app,
    }
    ports = {name: free_port() for name in apps}
    servers = {name: start_uvicorn(app, ports[name]) for name, app in apps.items()}
    urls = {name: f"http://127.0.0.1:{port}" for name, port in ports.items()}
    for url in urls.values():
        wait_for(f"{url}/health")
    # Same variables as `workshop serve`, so the harness reaches the services the same way.
    exported = {
        "BUSINESS_API_URL": urls["business_api"],
        "DOCS_SEARCH_URL": urls["docs_search"],
        "PROXY_URL": urls["proxy"],
        "INTERFACE_URL": urls["interface"],
        # Persistent memory of the agent (bonus workshop): one store per test session, emptied by reset_state.
        "MEMORY_DIR": str(session_dir / "memory"),
    }
    previous = {name: os.environ.get(name) for name in exported}
    os.environ.update(exported)
    yield urls
    for name, value in previous.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
    for server in servers.values():
        server.should_exit = True


@pytest.fixture(scope="session")
def mcp_server(services):
    """Serves `my-agent/mcp_server.py` (`application()`, `MCP_PATH`) and exports `MCP_URL`.

    Same server as `workshop serve`: every workshop test reaches it through `MCP_URL`, from
    workshop 06 on (before 06 the bootstrap server exposes no tool and the harness ignores it).
    Yields None, without `MCP_URL`, when the file is missing or cannot start.
    """
    from agent_gateway.loader import load_mcp_server

    try:
        module = load_mcp_server()
        app = module.application()
        path = module.MCP_PATH
    except Exception as exc:  # noqa: BLE001 - a broken student file must not hide the other tests
        print(f"\nmy-agent/mcp_server.py not served: {type(exc).__name__}: {exc}")
        yield None
        return
    port = free_port()
    server = start_uvicorn(app, port)
    wait_for_port("127.0.0.1", port)
    url = f"http://127.0.0.1:{port}{path}"
    previous = os.environ.get("MCP_URL")
    os.environ["MCP_URL"] = url
    yield url
    if previous is None:
        os.environ.pop("MCP_URL", None)
    else:
        os.environ["MCP_URL"] = previous
    server.should_exit = True


@pytest.fixture(autouse=True)
def _workshop_mcp_server(request):
    """Every workshop test (`workshops/*/tests/`) runs with the MCP server of `my-agent/` started."""
    if "workshops" in request.node.path.parts:
        request.getfixturevalue("mcp_server")


@pytest.fixture
def reset_state(session_dir, services):
    load_dataset("standard")
    tracer.clear()
    clear_docs_log()
    clear_proxy_log()
    reset_usage()
    reset_conversations()
    memory_dir = session_dir / "memory"
    shutil.rmtree(memory_dir, ignore_errors=True)
    memory_dir.mkdir()
    yield


@pytest.fixture
def observation(services, reset_state):
    class Observation:
        def __init__(self):
            self.base = services["business_api"]
            self.headers = {"Authorization": f"Bearer {OBSERVATION_TOKEN}"}

        def state(self, case: str) -> dict:
            r = httpx.get(f"{self.base}/observation/state", params={"case": case}, headers=self.headers, timeout=10)
            r.raise_for_status()
            return r.json()

        def log(self) -> list:
            r = httpx.get(f"{self.base}/observation/log", headers=self.headers, timeout=10)
            r.raise_for_status()
            return r.json()

        def token(self, user_id: str = "camille-renard") -> dict:
            r = httpx.post(
                f"{self.base}/observation/test-token",
                headers=self.headers,
                json={"user_id": user_id},
                timeout=10,
            )
            r.raise_for_status()
            return r.json()

        def reset(self, dataset: str = "standard") -> dict:
            r = httpx.post(
                f"{self.base}/observation/reset",
                headers=self.headers,
                json={"dataset": dataset},
                timeout=30,
            )
            r.raise_for_status()
            return r.json()

        def arm_failure(self, typ: str, active: bool = True) -> dict:
            r = httpx.post(
                f"{self.base}/observation/failures",
                headers=self.headers,
                json={"type": typ, "active": active},
                timeout=10,
            )
            r.raise_for_status()
            return r.json()

    return Observation()


@pytest.fixture
def business_client(services, observation):
    token = observation.token()["app_token"]
    return httpx.Client(base_url=services["business_api"], headers={"Authorization": f"Bearer {token}"}, timeout=10)


@pytest.fixture
def chat_client(services, reset_state) -> ChatClient:
    return ChatClient(services["interface"])


@pytest.fixture
def traces(session_dir):
    class Traces:
        def all(self):
            return tracer.read_all()

        def last(self):
            everything = tracer.read_all()
            assert everything, "no trace written"
            return everything[-1]

    return Traces()
