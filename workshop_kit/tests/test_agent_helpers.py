"""Helpers of the my-agent bootstrap (my-agent/agent_helpers/): repetitive code, never a workshop's goal."""

import importlib
import sys

import pytest

from workshop_kit.shell.config import repo_path, settings


@pytest.fixture(scope="module")
def helpers():
    folder = str(repo_path(settings.my_agent_dir))
    added = folder not in sys.path
    if added:
        sys.path.append(folder)
    yield lambda name: importlib.import_module(f"agent_helpers.{name}")
    if added:
        sys.path.remove(folder)


def test_kit_model_client_reads_the_proxy_url_at_call_time(helpers, monkeypatch):
    kit = helpers("kit")
    monkeypatch.setenv("PROXY_URL", "http://127.0.0.1:9/")
    assert kit.model_client().base_url == "http://127.0.0.1:9"
    assert kit.is_egress_allowed("http://example.com/") is None, "the shipped policy is inactive"
