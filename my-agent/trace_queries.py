"""Review criteria of the agent expressed as queries on the trace (workshop 11).

The agent stays single: one loop, one tool catalog, no sub-agent and no routing. These two queries
watch the signals that would justify splitting it one day:

- `intermediate_reads_share`: turn by turn, the share of the model context taken by intermediate
  tool reads. A share that stays high means the context is crowded by reads that a sub-agent could
  have digested before answering.
- `incompatible_domains`: the turns that touch, within a single turn, business domains whose
  permissions belong to different roles (orders handled by customer service, invoices by accounting,
  purchasing by buyers). Such a mix is a reason to review permissions, or to separate agents.

Both accept the traces written by the harness (`traces/*.jsonl`, read with `load()`) and the
simplified form of the example traces (`context.total_size`, `context.intermediate_reads`,
`tools[].domain`).

Usage: uv run --project workshop_tests python my-agent/trace_queries.py [traces.jsonl]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Roles that own each business domain (who reads or writes it as their own job).
DOMAIN_OWNERS: dict[str, set[str]] = {
    "orders": {"customer_service"},
    "customers": {"customer_service"},
    "invoices": {"accountant", "financial_controller"},
    "invoice_approval": {"accountant"},
    "suppliers": {"buyer"},
    "purchase_requests": {"buyer"},
    "purchase_request": {"buyer"},
}

# Domain of a harness tool call when the trace does not record it explicitly.
_TOOL_DOMAINS = {
    "get_order": "orders",
    "prepare_purchase_request": "purchase_requests",
    "prepare_invoice_approval": "invoices",
}
_ENTITY_DOMAINS = {"customer": "customers", "supplier": "suppliers"}


def load(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Traces written by the harness (default: the kit's trace file)."""
    if path is None:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from workshop_kit.shell import tracer

        return tracer.read_all()
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _turn_key(trace: dict) -> dict:
    user = trace.get("user")
    return {
        "turn_id": trace.get("turn_id"),
        "conversation_id": trace.get("conversation_id"),
        "user": user.get("id") if isinstance(user, dict) else user,
        "role": user.get("role") if isinstance(user, dict) else trace.get("role"),
    }


def _context_sizes(trace: dict) -> tuple[int, int]:
    """(total size of the context, size taken by intermediate reads), in characters."""
    context = trace.get("context") or {}
    if "total_size" in context:
        return int(context.get("total_size") or 0), int(context.get("intermediate_reads") or 0)
    reads = sum(
        len(json.dumps(t.get("result"), ensure_ascii=False)) for t in trace.get("tools") or [] if "result" in t
    )
    calls = (trace.get("model") or {}).get("calls") or []
    sizes = [(c.get("context_size") or {}).get("chars", 0) for c in calls]
    return (max(sizes) if sizes else 0), reads


def intermediate_reads_share(traces: list[dict]) -> list[dict]:
    """Turn by turn, the share of the context taken by intermediate reads (0 to 1)."""
    rows = []
    for trace in traces:
        total, reads = _context_sizes(trace)
        share = round(min(reads / total, 1.0), 3) if total else 0.0
        rows.append({**_turn_key(trace), "context_size": total, "intermediate_reads": reads, "share": share})
    return rows


def _domain(tool: dict) -> str | None:
    if tool.get("domain"):
        return tool["domain"]
    arguments = tool.get("arguments") or {}
    name = tool.get("name")
    if name == "query" or name == "describe_source":
        return arguments.get("source")
    if name == "find_by_name":
        return _ENTITY_DOMAINS.get(arguments.get("entity_type") or "customer")
    return _TOOL_DOMAINS.get(name)


def incompatible_domains(traces: list[dict]) -> list[dict]:
    """Turns that touch, within one turn, domains owned by disjoint sets of roles."""
    findings = []
    for trace in traces:
        domains = sorted({d for d in (_domain(t) for t in trace.get("tools") or []) if d})
        conflicts = [
            [a, b]
            for i, a in enumerate(domains)
            for b in domains[i + 1 :]
            if a in DOMAIN_OWNERS and b in DOMAIN_OWNERS and not DOMAIN_OWNERS[a] & DOMAIN_OWNERS[b]
        ]
        if conflicts:
            findings.append({**_turn_key(trace), "domains": domains, "conflicts": conflicts})
    return findings


if __name__ == "__main__":
    data = load(sys.argv[1] if len(sys.argv) > 1 else None)
    print(json.dumps({"intermediate_reads_share": intermediate_reads_share(data),
                      "incompatible_domains": incompatible_domains(data)}, ensure_ascii=False, indent=2))
