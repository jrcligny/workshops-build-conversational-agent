"""Shared pytest fixtures: applications, proxy, traces, dataset.

Loaded as a pytest plugin by the root `conftest.py`, so that the kit tests
(`tests/kit/`) and the workshop tests (`workshops/*/tests/`) share them.
"""

from __future__ import annotations

import os

import httpx
import pytest

# Simulated mode from import time, before the applications read their settings.
os.environ.setdefault("PROXY_MODE", "simulated")
os.environ.setdefault("MODEL_MODE", "simulated")
os.environ.setdefault("OBSERVATION_TOKEN", "workshop-observation")
os.environ.setdefault("TOKEN_SECRET", "workshop-test-secret-32-bytes-long!")

from workshop_kit.apps.business_api.app import app as business_app  # noqa: E402
from workshop_kit.apps.business_api.db import reassign  # noqa: E402
from workshop_kit.apps.business_api.seed_data import load_dataset  # noqa: E402
from workshop_kit.apps.docs_search.app import app as docs_app, clear_log as clear_docs_log  # noqa: E402
from workshop_kit.apps.docs_search.indexing import rebuild  # noqa: E402
from workshop_kit.llm_proxy.app import app as proxy_app, clear_log as clear_proxy_log  # noqa: E402
from workshop_kit.llm_proxy.tokens import reset_usage  # noqa: E402
from workshop_kit.shell import tracer  # noqa: E402
from workshop_kit.shell.chat_app import app as interface_app, reset_conversations  # noqa: E402
from workshop_kit.shell.config import settings  # noqa: E402
from workshop_kit.testing.chat_client import ChatClient  # noqa: E402
from workshop_kit.testing.servers import start_uvicorn, free_port, wait_for  # noqa: E402

OBSERVATION_TOKEN = "workshop-observation"


@pytest.fixture(scope="session")
def session_dir(tmp_path_factory):
    root = tmp_path_factory.mktemp("session")
    settings.business_api_db = str(root / "business_api.db")
    settings.docs_search_db = str(root / "docs_search.db")
    settings.traces_dir = str(root / "traces")
    settings.proxy_mode = "simulated"
    settings.model_mode = "simulated"
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
    yield urls
    for server in servers.values():
        server.should_exit = True


@pytest.fixture
def reset_state(session_dir, services):
    load_dataset("standard")
    tracer.clear()
    clear_docs_log()
    clear_proxy_log()
    reset_usage()
    reset_conversations()
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
