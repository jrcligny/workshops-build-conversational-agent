"""Business tools of the agent and their client to the business API."""

from __future__ import annotations

import os
from typing import Any

from workshop_kit.shell.harness_contract import TestUser

STATUS_LABELS = {
    "delivered": "livrée",
    "shipped": "expédiée",
    "in_preparation": "en préparation",
    "confirmed": "confirmée",
    "rejected": "rejetée",
    "deleted": "supprimée",
}


class BusinessClient:
    """HTTP client to the business API, on behalf of the conversation's user."""

    def __init__(self, user: TestUser):
        self.user = user
        self.token = user.app_token or _user_scoped_token(user)
        url = os.environ.get("BUSINESS_API_URL")
        if url:
            import httpx

            self._http = httpx.Client(base_url=url.rstrip("/"), timeout=15)
        else:
            # Test runs host the business API in the same process and export no URL.
            from fastapi.testclient import TestClient

            from workshop_kit.apps.business_api.app import app

            self._http = TestClient(app)

    def request(self, method: str, path: str, **kwargs) -> tuple[int, Any]:
        response = self._http.request(method, path, headers={"Authorization": f"Bearer {self.token}"}, **kwargs)
        try:
            body = response.json()
        except ValueError:
            body = response.text
        return response.status_code, body


def _user_scoped_token(user: TestUser) -> str:
    """Application token for the conversation's user, when the interface passed none."""
    from workshop_kit.apps.business_api.auth import issue_token

    return issue_token(user.id, user.role, user.organization, typ="application")


def _close(a: str, b: str) -> bool:
    """Same length and at most one substitution or one transposition of adjacent characters."""
    if len(a) != len(b) or a == b:
        return False
    diffs = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    if len(diffs) == 1:
        return True
    return len(diffs) == 2 and diffs[1] == diffs[0] + 1 and a[diffs[0]] == b[diffs[1]] and a[diffs[1]] == b[diffs[0]]


def _order_view(order: dict) -> dict:
    return {
        "reference": order.get("reference"),
        "status": order.get("status"),
        "status_label": STATUS_LABELS.get(order.get("status"), order.get("status")),
        "amount": order.get("amount"),
        "order_date": order.get("order_date"),
        "promised_date": order.get("promised_date"),
        "delivery_date": order.get("delivery_date"),
        "delivery_city": order.get("delivery_city"),
        "customer_id": order.get("customer_id"),
        "late": order.get("late"),
    }


def get_order(client: BusinessClient, reference: str) -> dict:
    reference = (reference or "").strip().upper()
    if not reference:
        return {"status": "error", "error": "missing reference"}
    code, body = client.request("GET", f"/orders/{reference}")
    if code == 200:
        return {"status": "found", "order": _order_view(body)}
    if code != 404:
        return {"status": "error", "error": f"business API answered {code}", "reference": reference}
    # Not found: look for the closest visible reference (excluded orders are never returned by the API).
    code, body = client.request("POST", "/sources/orders/query", json={"filters": {}})
    if code != 200:
        return {"status": "not_found", "reference": reference, "detail": "order not found; no suggestion available"}
    candidates = [row for row in body.get("rows", []) if _close(reference, str(row.get("reference", "")).upper())]
    if len(candidates) == 1:
        return {
            "status": "approximate",
            "requested_reference": reference,
            "detail": "the requested reference does not exist; closest existing order returned",
            "order": _order_view(candidates[0]),
        }
    return {
        "status": "not_found",
        "reference": reference,
        "detail": "order not found (absent or not accessible); no close reference",
    }


def search_customers(client: BusinessClient, name: str) -> dict:
    name = (name or "").strip()
    if not name:
        return {"status": "error", "error": "missing name"}
    code, body = client.request("GET", "/customers", params={"name": name})
    if code != 200:
        return {"status": "error", "error": f"business API answered {code}"}
    customers = [
        {key: row.get(key) for key in ("id", "name", "city", "email", "segment") if row.get(key) is not None}
        for row in body
    ]
    if not customers:
        return {"status": "not_found", "name": name, "customers": []}
    result: dict[str, Any] = {"status": "ok", "count": len(customers), "customers": customers}
    if len(customers) > 1:
        result["note"] = (
            "several customers match: list them all (with their city) and ask the user which one; never pick one"
        )
    return result


ORDER_FILTERS = {"all": None, "late": "late"}
MAX_ORDERS = 20


def list_customer_orders(client: BusinessClient, customer_id: str, filter: str = "all", limit: int | None = None) -> dict:
    customer_id = (customer_id or "").strip()
    if not customer_id:
        return {"status": "error", "error": "missing customer_id (use search_customers first)"}
    if filter not in ORDER_FILTERS:
        return {"status": "error", "error": f"unknown filter {filter!r}; allowed: {sorted(ORDER_FILTERS)}"}
    limit = min(int(limit or MAX_ORDERS), MAX_ORDERS)
    params: dict[str, Any] = {"limit": limit}
    if ORDER_FILTERS[filter]:
        params["filter"] = ORDER_FILTERS[filter]
    code, body = client.request("GET", f"/customers/{customer_id}/orders", params=params)
    if code == 404:
        return {"status": "not_found", "customer_id": customer_id}
    if code != 200:
        return {"status": "error", "error": f"business API answered {code}"}
    result = {
        "status": "ok",
        "customer_id": customer_id,
        "filter": filter,
        "total": body.get("total"),
        "returned": len(body.get("orders", [])),
        "orders": [_order_view(o) for o in body.get("orders", [])],
    }
    if body.get("truncated"):
        result["note"] = f"only the first {limit} of {body.get('total')} orders are listed: say so to the user"
    return result


TOOL_SPECS: dict[str, dict] = {
    "search_customers": {
        "type": "function",
        "function": {
            "name": "search_customers",
            "description": (
                "Searches customers by (part of) their name. Returns every match, namesakes included, "
                "with id and city. Never pick one of several matches on behalf of the user."
            ),
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Customer name or part of it"}},
                "required": ["name"],
                "additionalProperties": False,
            },
        },
    },
    "list_customer_orders": {
        "type": "function",
        "function": {
            "name": "list_customer_orders",
            "description": (
                "Lists the orders of one customer (by customer id from search_customers). "
                "Use filter='late' to keep only orders whose delivery is late: the filtering is done here, "
                "do not filter the list yourself."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Customer id, e.g. C-DURAND-1"},
                    "filter": {"type": "string", "enum": list(ORDER_FILTERS), "description": "'late' or 'all'"},
                    "limit": {"type": "integer", "description": f"Maximum number of orders (≤ {MAX_ORDERS})"},
                },
                "required": ["customer_id", "filter"],
                "additionalProperties": False,
            },
        },
    },
    "get_order": {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": (
                "Looks up one order by its reference (e.g. CMD-1234). Returns status 'found' with the order, "
                "'approximate' with the closest existing order when the reference does not exist, "
                "'not_found' when nothing matches, or 'error'."
            ),
            "parameters": {
                "type": "object",
                "properties": {"reference": {"type": "string", "description": "Order reference, e.g. CMD-1234"}},
                "required": ["reference"],
                "additionalProperties": False,
            },
        },
    },
}

TOOL_FUNCTIONS = {
    "get_order": lambda client, args: get_order(client, args.get("reference", "")),
    "search_customers": lambda client, args: search_customers(client, args.get("name", "")),
    "list_customer_orders": lambda client, args: list_customer_orders(
        client, args.get("customer_id", ""), args.get("filter") or "all", args.get("limit")
    ),
}
