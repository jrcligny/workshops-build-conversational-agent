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


TOOL_SPECS: dict[str, dict] = {
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

TOOL_FUNCTIONS = {"get_order": lambda client, args: get_order(client, args.get("reference", ""))}
