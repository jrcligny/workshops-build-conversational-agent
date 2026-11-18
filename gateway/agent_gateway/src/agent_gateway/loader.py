"""Loads the student's harness from my-agent/, without providing any loop."""

from __future__ import annotations

import importlib.util
import os
import sys
import time

from agent_sdk.contract import HarnessNotImplemented
from workshop_config import repo_path, settings

# Set by `workshop serve`: status of the MCP runner (`workshop_tools.mcp_runner`), which reloads
# my-agent/mcp_server.py on change. Absent in the tests, which serve the module themselves.
MCP_STATUS_ENV = "WORKSHOP_MCP_STATUS_URL"
NO_RESTART = "Fix the file and send your message again: no restart needed."


class MyAgentLoadError(Exception):
    """my-agent/ changed but cannot be loaded: the message names the file, the line and the error."""


def wait_for_mcp_server(signature: str, timeout: float = 30.0) -> None:
    """Waits until the MCP runner serves the version `signature` of my-agent/, or reports its error."""
    url = os.environ.get(MCP_STATUS_ENV)
    if not url:
        return
    import httpx

    deadline = time.monotonic() + timeout
    with httpx.Client(timeout=2, trust_env=False) as client:
        while True:
            try:
                status = client.get(url).json()
            except (httpx.HTTPError, ValueError):
                status = {}
            if status.get("signature") == signature:
                if status.get("state") == "error":
                    raise MyAgentLoadError(
                        f"The MCP server of my-agent could not be reloaded: {status.get('detail')}. {NO_RESTART}"
                    )
                return
            if time.monotonic() >= deadline:
                raise MyAgentLoadError(
                    f"The MCP server of my-agent did not reload the last changes within {timeout:.0f} s. "
                    "See .workshop/logs/mcp.log."
                )
            time.sleep(0.2)


def load_harness():
    folder = repo_path(settings.my_agent_dir)
    path = folder / "harness.py"
    if not path.exists():
        raise HarnessNotImplemented(
            "No my-agent/harness.py file. Implement the harness contract (workshop 03)."
        )
    spec = importlib.util.spec_from_file_location("my_agent_harness", path)
    if spec is None or spec.loader is None:
        raise HarnessNotImplemented("Cannot load my-agent/harness.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["my_agent_harness"] = module
    spec.loader.exec_module(module)
    if not hasattr(module, "Harness"):
        raise HarnessNotImplemented("my-agent/harness.py must expose a Harness class.")
    return module.Harness()


def load_my_agent_module(file_name: str, module_name: str):
    """Loads a module from the my-agent/ shell (harness, MCP server, ...)."""
    path = repo_path(settings.my_agent_dir) / file_name
    if not path.exists():
        raise FileNotFoundError(f"File missing from the shell: {path}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_mcp_server():
    return load_my_agent_module("mcp_server.py", "my_agent_mcp_server")
