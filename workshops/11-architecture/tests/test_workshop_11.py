"""End-to-end tests of workshop 11. They must fail on the empty shell.

Deliverable: `my-agent/trace_queries.py` with two functions.
- `intermediate_reads_share(traces) -> list[{"turn_id", "share"}]`: share of the context
  taken by intermediate reads, turn by turn (one entry per trace, share in [0, 1]).
- `incompatible_domains(traces, permissions) -> list[{"turn_id", "domains"}]`: turns whose
  tool calls touch, within one turn, domains whose read permissions differ. `permissions`
  maps a domain to the set of roles allowed to read it.
The example traces (`tests/fixtures/example-traces.jsonl`) carry `context.total_size`,
`context.intermediate_reads` and `tools[].domain`; the queries must also run on the traces
written by your own agent (folder `traces/`).
"""

import importlib.util
import json
import random
from pathlib import Path

import pytest

from workshop_kit.shell.config import repo_path, settings
from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.turns import successful_turn

pytestmark = pytest.mark.workshop

EXAMPLE_TRACES = Path(__file__).parent / "fixtures" / "example-traces.jsonl"
PERMISSIONS = {
    "customers": {"customer_service", "accountant", "buyer"},
    "orders": {"customer_service", "accountant", "buyer"},
    "invoices": {"accountant"},
}


def _load_queries():
    path = repo_path(settings.my_agent_dir) / "trace_queries.py"
    assert path.is_file(), "missing deliverable: my-agent/trace_queries.py (intermediate_reads_share, incompatible_domains)"
    spec = importlib.util.spec_from_file_location("student_trace_queries", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _example_traces() -> list[dict]:
    return [json.loads(line) for line in EXAMPLE_TRACES.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_intermediate_reads_share_turn_by_turn():
    shares = {s["turn_id"]: s["share"] for s in _load_queries().intermediate_reads_share(_example_traces())}
    assert set(shares) == {"t1", "t2", "t3", "t4"}, "one entry per turn"
    assert shares["t1"] == pytest.approx(0.625)
    assert shares["t2"] == pytest.approx(800 / 3500)
    assert shares["t3"] == pytest.approx(0.1)
    assert shares["t4"] == pytest.approx(0.0)


def test_incompatible_domains_reported():
    reported = _load_queries().incompatible_domains(_example_traces(), PERMISSIONS)
    by_turn = {r["turn_id"]: set(r["domains"]) for r in reported}
    assert set(by_turn) == {"t2"}, "only t2 mixes domains with different read permissions (t3 does not)"
    assert by_turn["t2"] == {"orders", "invoices"}


def test_queries_computed_on_unseen_traces():
    """Traces generated at test time (new turn ids, sizes and permissions): the values are computed, not recalled."""
    rng = random.Random(11)
    combos = [[], ["orders"], ["customers", "orders"], ["orders", "invoices"], ["invoices", "customers", "invoices"]]
    traces, expected_share, expected_mixed = [], {}, {}
    permissions = dict(PERMISSIONS, customers={"customer_service", "buyer"})  # customers no longer readable by the accountant
    for i in range(12):
        total = rng.randint(500, 9000)
        reads = rng.randint(0, total)
        domains = combos[i % len(combos)]
        turn_id = f"gen-{rng.randint(1000, 9999)}-{i}"
        traces.append({"turn_id": turn_id, "context": {"total_size": total, "intermediate_reads": reads},
                       "tools": [{"name": "query", "domain": d} for d in domains]})
        expected_share[turn_id] = reads / total
        if len({frozenset(permissions[d]) for d in domains}) > 1:
            expected_mixed[turn_id] = set(domains)
    module = _load_queries()
    shares = {s["turn_id"]: s["share"] for s in module.intermediate_reads_share(traces)}
    assert shares.keys() == expected_share.keys()
    for turn_id, share in expected_share.items():
        assert shares[turn_id] == pytest.approx(share)
    reported = {r["turn_id"]: set(r["domains"]) for r in module.incompatible_domains(traces, permissions)}
    assert reported == expected_mixed, "the permissions passed as argument decide, e.g. customers + orders now differ"


def test_queries_run_on_your_own_traces(chat_client, services):
    module = _load_queries()
    _, trace = successful_turn(chat_client, "Quel est le statut de la commande CMD-1042 ?")
    shares = module.intermediate_reads_share([trace])
    assert len(shares) == 1 and 0.0 <= shares[0]["share"] <= 1.0, "the share is computed on a trace written by your agent"
    assert shares[0]["share"] > 0, "a turn that called a tool has intermediate reads in its context"
    assert module.incompatible_domains([trace], PERMISSIONS) == [], "a turn on orders only is not reported"

    _, greeting = successful_turn(chat_client, "Merci, bonne journée !")
    if not greeting.get("tools"):
        assert module.intermediate_reads_share([greeting])[0]["share"] == 0, "a turn without tool has no intermediate read"

    accountant = ChatClient(services["interface"])
    accountant.open(user_id="nina-accountant", role="accountant", organization="organization-a")
    _, mixed = successful_turn(accountant, "Quel est le statut de la commande CMD-1042, et celui de sa facture FAC-3301 ?")
    reported = module.incompatible_domains([mixed], PERMISSIONS)
    assert len(reported) == 1 and {"orders", "invoices"} <= set(reported[0]["domains"]), (
        "a turn of your agent reading orders and invoices together is reported"
    )
