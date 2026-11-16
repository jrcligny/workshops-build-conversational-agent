"""Business rules and queries, including isolation by organization and by role."""

from __future__ import annotations

import json
import uuid
from typing import Any

from workshop_kit.apps.business_api.db import connection
from workshop_kit.shell.timestamps import CLOCK, now

STATUSES_HIDDEN_FROM_CUSTOMER_SERVICE = {"deleted", "rejected"}


def _org(identity: dict) -> str:
    return identity["organization"]


def log_call(method: str, route: str, identity: dict | None, code: int) -> None:
    connection().execute(
        """INSERT INTO call_log(timestamp, method, route, user_id, organization_id, role, code)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            now().isoformat(),
            method,
            route,
            (identity or {}).get("sub"),
            (identity or {}).get("organization"),
            (identity or {}).get("role"),
            code,
        ),
    )
    connection().commit()


def read_call_log() -> list[dict]:
    rows = connection().execute("SELECT * FROM call_log ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def active_failure() -> str | None:
    row = connection().execute("SELECT type, active FROM failures WHERE id = 1").fetchone()
    if row and row["active"]:
        return row["type"]
    return None


def arm_failure(failure_type: str | None, active: bool = True) -> None:
    connection().execute("UPDATE failures SET type = ?, active = ? WHERE id = 1", (failure_type, int(active)))
    connection().commit()


def _row(d) -> dict | None:
    return dict(d) if d is not None else None


def is_excluded(row: dict, identity: dict) -> bool:
    if identity.get("role") == "customer_service":
        return bool(row.get("deleted")) or row.get("status") in STATUSES_HIDDEN_FROM_CUSTOMER_SERVICE
    return False


def is_late(row: dict) -> bool:
    if row.get("deleted") or row.get("status") in {"delivered", "rejected", "deleted"}:
        return False
    promised = row.get("promised_date")
    if not promised:
        return False
    return promised < CLOCK.date().isoformat()


def get_order(reference: str, identity: dict) -> dict | None:
    row = connection().execute(
        "SELECT * FROM orders WHERE reference = ? AND organization_id = ?",
        (reference, _org(identity)),
    ).fetchone()
    if not row:
        return None
    data = dict(row)
    if is_excluded(data, identity):
        return None
    data["late"] = is_late(data)
    return data


def search_customers(name: str, identity: dict) -> list[dict]:
    rows = connection().execute(
        "SELECT * FROM customers WHERE organization_id = ? AND name LIKE ? COLLATE NOCASE",
        (_org(identity), f"%{name}%"),
    ).fetchall()
    return [dict(r) for r in rows]


def get_customer(customer_id: str, identity: dict) -> dict | None:
    row = connection().execute(
        "SELECT * FROM customers WHERE id = ? AND organization_id = ?",
        (customer_id, _org(identity)),
    ).fetchone()
    return _row(row)


def list_orders(customer_id: str, identity: dict, filter: str | None = None, limit: int | None = None) -> dict:
    rows = connection().execute(
        "SELECT * FROM orders WHERE customer_id = ? AND organization_id = ? ORDER BY order_date",
        (customer_id, _org(identity)),
    ).fetchall()
    orders = [dict(r) for r in rows]
    orders = [o for o in orders if not is_excluded(o, identity)]
    for o in orders:
        o["late"] = is_late(o)
    if filter == "late":
        orders = [o for o in orders if o["late"]]
    total = len(orders)
    truncated = False
    if limit is not None and len(orders) > limit:
        orders = orders[:limit]
        truncated = True
    return {"orders": orders, "total": total, "truncated": truncated, "limit": limit}


def resolve_name(entity_type: str, name: str, identity: dict) -> list[dict]:
    tables = {"customer": "customers", "supplier": "suppliers", "user": "users"}
    table = tables.get(entity_type)
    if not table:
        return []
    rows = connection().execute(
        f"SELECT * FROM {table} WHERE organization_id = ? AND name LIKE ? COLLATE NOCASE",
        (_org(identity), f"%{name}%"),
    ).fetchall()
    return [dict(r) for r in rows]


# Codes and field names are English (API contract). The labels of coded values are
# French: they are what the agent shows to its French-speaking users.
SOURCES = {
    "orders": {
        "description": "Orders and deliveries",
        "fields": {
            "reference": "order reference",
            "status": "status code (French display labels in coded_values: livrée, expédiée, en préparation, rejetée, supprimée)",
            "amount": "amount including tax",
            "promised_date": "promised delivery date",
            "customer_id": "customer identifier",
        },
        "relations": {"customer_id": "customers.id"},
        "coded_values": {
            "status": {
                "delivered": "livrée",
                "shipped": "expédiée",
                "in_preparation": "en préparation",
                "rejected": "rejetée",
                "deleted": "supprimée",
                "confirmed": "confirmée",
            }
        },
        "aggregates": ["count", "total", "average"],
    },
    "customers": {
        "description": "Customers of the organization",
        "fields": {"name": "name", "city": "city"},
        "relations": {},
        "coded_values": {},
        "aggregates": ["count"],
    },
    "invoices": {
        "description": "Supplier invoices",
        "fields": {"reference": "reference", "status": "status", "amount": "amount", "duplicate_of": "original invoice when duplicated"},
        "relations": {"order_id": "orders.id"},
        "coded_values": {
            "status": {"paid": "réglée", "pending": "en attente d'approbation", "approved": "approuvée"}
        },
        "aggregates": ["count", "total", "average"],
    },
    "suppliers": {
        "description": "Suppliers",
        "fields": {"name": "name"},
        "relations": {},
        "coded_values": {},
        "aggregates": ["count"],
    },
    "purchase_requests": {
        "description": "Purchase requests",
        "fields": {"subject": "subject", "status": "status", "amount": "amount"},
        "relations": {},
        "coded_values": {},
        "aggregates": ["count", "total"],
    },
}


def query_source(name: str, identity: dict, filters: dict, limit: int | None, aggregate: str | None, group_by: str | None) -> dict:
    if name not in SOURCES:
        raise ValueError("unknown source")
    if aggregate == "median":
        return {
            "refused": True,
            "reason": "the median is not offered",
            "available_aggregates": SOURCES[name]["aggregates"],
        }
    sql = f"SELECT * FROM {name} WHERE organization_id = ?"
    params: list[Any] = [_org(identity)]
    for key, value in (filters or {}).items():
        if key not in SOURCES[name]["fields"] and key not in {"organization_id", "id", "customer_id", "status"}:
            raise ValueError(f"unrecognized filter: {key}")
        sql += f" AND {key} = ?"
        params.append(value)
    rows = [dict(r) for r in connection().execute(sql, params).fetchall()]
    if name == "orders":
        rows = [r for r in rows if not is_excluded(r, identity)]
        for r in rows:
            r["late"] = is_late(r)
    total = len(rows)
    if aggregate or group_by:
        if group_by:
            groups: dict[str, list[float]] = {}
            for r in rows:
                key = str(r.get(group_by, ""))
                groups.setdefault(key, []).append(float(r.get("amount") or 0))
            result = []
            for key, values in groups.items():
                item = {"group": key, "count": len(values)}
                if aggregate == "total":
                    item["total"] = round(sum(values), 2)
                if aggregate == "average":
                    item["average"] = round(sum(values) / len(values), 2) if values else 0
                result.append(item)
            return {"rows": result, "total": len(result), "aggregate": aggregate, "group_by": group_by}
        amounts = [float(r.get("amount") or 0) for r in rows]
        if aggregate == "count":
            value = total
        elif aggregate == "total":
            value = round(sum(amounts), 2)
        elif aggregate == "average":
            value = round(sum(amounts) / len(amounts), 2) if amounts else 0
        else:
            raise ValueError("unknown aggregate")
        return {"value": value, "aggregate": aggregate, "total": total}
    truncated = False
    if limit is not None and len(rows) > limit:
        rows = rows[:limit]
        truncated = True
    return {"rows": rows, "total": total, "truncated": truncated, "limit": limit}


def prepare_draft(typ: str, payload: dict, identity: dict) -> dict:
    draft_id = f"DRAFT-{uuid.uuid4().hex[:10]}"
    connection().execute(
        """INSERT INTO drafts(id, type, organization_id, user_id, payload, submitted, created_at)
           VALUES (?, ?, ?, ?, ?, 0, ?)""",
        (draft_id, typ, _org(identity), identity["sub"], json.dumps(payload, ensure_ascii=False), now().isoformat()),
    )
    connection().commit()
    return {"id": draft_id, "type": typ, "payload": payload, "submitted": False}


def get_draft(draft_id: str, identity: dict) -> dict | None:
    row = connection().execute(
        "SELECT * FROM drafts WHERE id = ? AND organization_id = ?",
        (draft_id, _org(identity)),
    ).fetchone()
    if not row:
        return None
    data = dict(row)
    data["payload"] = json.loads(data["payload"])
    return data


def submit_draft(draft_id: str, identity: dict) -> dict:
    failure = active_failure()
    if failure == "unavailable":
        raise RuntimeError("application unavailable")
    draft = get_draft(draft_id, identity)
    if not draft:
        raise KeyError("draft not found")
    if draft["submitted"]:
        # No idempotency: a resubmission is a new attempt, without a key.
        pass
    if failure == "unknown_outcome":
        # Accept, then silence: nothing is written and the outcome is not reported.
        raise RuntimeError("unknown_outcome")
    typ = draft["type"]
    payload = draft["payload"]
    if typ == "purchase_request":
        request_id = f"PR-{uuid.uuid4().hex[:8]}"
        connection().execute(
            """INSERT INTO purchase_requests(
                id, organization_id, supplier_id, status, subject, amount, draft,
                assigned_to, on_behalf_of, created_at, submitted_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)""",
            (
                request_id,
                _org(identity),
                payload.get("supplier_id"),
                "submitted",
                payload.get("subject", ""),
                payload.get("amount"),
                "agent",
                identity["sub"],
                now().isoformat(),
                now().isoformat(),
            ),
        )
        result = {"request_id": request_id, "status": "submitted", "assigned_to": "agent", "on_behalf_of": identity["sub"]}
    elif typ == "invoice_approval":
        invoice_id = payload.get("invoice_id")
        connection().execute(
            "UPDATE invoices SET status = ? WHERE id = ? AND organization_id = ?",
            ("approved", invoice_id, _org(identity)),
        )
        result = {"invoice_id": invoice_id, "status": "approved", "assigned_to": "agent", "on_behalf_of": identity["sub"]}
    else:
        raise ValueError("unknown draft type")
    connection().execute("UPDATE drafts SET submitted = 1 WHERE id = ?", (draft_id,))
    connection().commit()
    return result


def get_invoice(invoice_id: str, identity: dict) -> dict | None:
    row = connection().execute(
        "SELECT * FROM invoices WHERE id = ? AND organization_id = ?",
        (invoice_id, _org(identity)),
    ).fetchone()
    return _row(row)


def get_user_settings(identity: dict) -> dict:
    row = connection().execute(
        "SELECT * FROM user_settings WHERE user_id = ?", (identity["sub"],)
    ).fetchone()
    if not row:
        return {"user_id": identity["sub"], "prefer_excl_tax": False}
    return dict(row)


def set_user_settings(identity: dict, prefer_excl_tax: bool) -> dict:
    connection().execute(
        "INSERT INTO user_settings(user_id, prefer_excl_tax) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET prefer_excl_tax = excluded.prefer_excl_tax",
        (identity["sub"], int(prefer_excl_tax)),
    )
    connection().commit()
    return get_user_settings(identity)


def case_state(case: str) -> dict:
    conn = connection()
    if case.startswith(("CMD-", "FAC-", "PR-", "DRAFT-")):
        order = conn.execute("SELECT * FROM orders WHERE reference = ?", (case,)).fetchone()
        invoice = conn.execute("SELECT * FROM invoices WHERE id = ? OR reference = ?", (case, case)).fetchone()
        request = conn.execute("SELECT * FROM purchase_requests WHERE id = ?", (case,)).fetchone()
        draft = conn.execute("SELECT * FROM drafts WHERE id = ?", (case,)).fetchone()
        return {
            "case": case,
            "order": dict(order) if order else None,
            "invoice": dict(invoice) if invoice else None,
            "purchase_request": dict(request) if request else None,
            "draft": dict(draft) if draft else None,
        }
    if case == "submissions":
        requests = [dict(r) for r in conn.execute("SELECT * FROM purchase_requests WHERE draft = 0").fetchall()]
        drafts = [dict(r) for r in conn.execute("SELECT * FROM drafts").fetchall()]
        return {"submitted_requests": requests, "drafts": drafts}
    return {"case": case, "unknown": True}
