"""End-to-end tests of workshop 11. They must fail on the empty shell."""

import importlib.util
import json
from pathlib import Path

import pytest

from workshop_tests.testing.turns import flat

pytestmark = pytest.mark.workshop

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_TRACES = Path(__file__).parent / "fixtures" / "example-traces.jsonl"


def _load_queries():
    path = REPO_ROOT / "my-agent" / "trace_queries.py"
    assert path.is_file(), (
        "missing deliverable: my-agent/trace_queries.py "
        "(functions intermediate_reads_share and incompatible_domains)"
    )
    spec = importlib.util.spec_from_file_location("student_trace_queries", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _example_traces() -> list[dict]:
    return [json.loads(line) for line in EXAMPLE_TRACES.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_trace_queries_present_and_runnable():
    module = _load_queries()
    traces = _example_traces()
    assert hasattr(module, "intermediate_reads_share"), "function intermediate_reads_share missing"
    assert hasattr(module, "incompatible_domains"), "function incompatible_domains missing"
    shares = module.intermediate_reads_share(traces)
    incompatible = module.incompatible_domains(traces)
    assert isinstance(shares, list) and shares, "the share of intermediate reads must be computed turn by turn"
    assert any(
        "t1" in flat(s) or (isinstance(s, dict) and (s.get("turn_id") == "t1" or s.get("share", 0) >= 0.5)) or "0.6" in flat(s)
        for s in shares
    )
    assert isinstance(incompatible, list)
    # the second example turn mixes orders and invoices
    assert incompatible, "turn t2 mixes domains with incompatible permissions and must be reported"
