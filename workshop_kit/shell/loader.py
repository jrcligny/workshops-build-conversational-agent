"""Loads the student's harness from my-agent/, without providing any loop."""

from __future__ import annotations

import importlib.util
import sys
from workshop_config import repo_path, settings
from workshop_kit.shell.harness_contract import HarnessNotImplemented


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
