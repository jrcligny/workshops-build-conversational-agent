"""Hot reload: a change to my-agent/ applies from the next turn; an error names its file and line."""

import sys

import pytest
from agent_gateway import chat_app
from agent_gateway.loader import MyAgentLoadError
from workshop_config import settings

HARNESS = """
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hot_helper

class Harness:
    def answer(self):
        return hot_helper.ANSWER
"""


@pytest.fixture
def agent(tmp_path, monkeypatch):
    folder = tmp_path / "my-agent"
    folder.mkdir()
    (folder / "harness.py").write_text(HARNESS, encoding="utf-8")
    (folder / "hot_helper.py").write_text('ANSWER = "one"\n', encoding="utf-8")
    monkeypatch.setattr(settings, "my_agent_dir", str(folder))
    monkeypatch.delenv("WORKSHOP_MCP_STATUS_URL", raising=False)
    for name in ("_harness", "_loaded", "_mcp_ready"):
        monkeypatch.setattr(chat_app, name, None)
    monkeypatch.setattr(sys, "path", list(sys.path))
    yield folder
    sys.modules.pop("hot_helper", None)
    sys.modules.pop("my_agent_harness", None)


def test_a_changed_module_applies_at_the_next_turn(agent):
    first = chat_app.harness()
    assert first.answer() == "one"
    assert chat_app.harness() is first
    (agent / "hot_helper.py").write_text('ANSWER = "second"\n', encoding="utf-8")
    second = chat_app.harness()
    assert second is not first
    assert second.answer() == "second"


def test_a_syntax_error_is_reported_then_fixed_without_restart(agent):
    assert chat_app.harness().answer() == "one"
    (agent / "hot_helper.py").write_text('ANSWER = = "two"\n', encoding="utf-8")
    with pytest.raises(MyAgentLoadError, match=r"my-agent/hot_helper\.py, line 1: SyntaxError"):
        chat_app.harness()
    (agent / "hot_helper.py").write_text('ANSWER = "fixed"\n', encoding="utf-8")
    assert chat_app.harness().answer() == "fixed"


def test_reset_without_change_keeps_the_loaded_modules(agent):
    chat_app.harness()
    helper = sys.modules["hot_helper"]
    chat_app.reset_conversations()
    chat_app.harness()
    # Tests may patch these modules: nothing changed on disk, so nothing is imported again.
    assert sys.modules["hot_helper"] is helper
