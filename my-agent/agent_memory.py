"""Working memory: explicit conversation state, kept outside the history so it survives compaction."""

from __future__ import annotations

import copy
from typing import Any


class WorkingMemory:
    """Current customer, current order and pending namesake choice, per conversation.

    The state is updated from tool results only (never from what the model writes), so it holds only
    what the application confirmed.
    """

    def __init__(self) -> None:
        self._states: dict[str, dict[str, Any]] = {}

    def get(self, conversation_id: str) -> dict[str, Any]:
        return copy.deepcopy(self._states.get(conversation_id, {}))

    def render(self, conversation_id: str) -> str | None:
        state = self._states.get(conversation_id)
        if not state:
            return None
        lines = ["État de la conversation (confirmé par l'application, prioritaire sur le résumé) :"]
        customer = state.get("current_customer")
        if customer:
            city = f", {customer['city']}" if customer.get("city") else ""
            lines.append(f"- client en cours : {customer['name']}{city} (id {customer['id']})")
        order = state.get("current_order")
        if order:
            lines.append(f"- commande en cours : {order['reference']} (statut {order.get('status_label')})")
        candidates = state.get("candidates")
        if candidates:
            listed = " ; ".join(f"{c['name']} ({c.get('city')}, id {c['id']})" for c in candidates)
            lines.append(f"- homonymes en attente du choix de l'utilisateur : {listed}")
        return "\n".join(lines)

    def update(self, conversation_id: str, name: str, arguments: dict, result: dict, lookup) -> None:
        state = self._states.setdefault(conversation_id, {})
        status = result.get("status")
        if name == "search_customers" and status == "ok":
            customers = result.get("customers") or []
            if len(customers) == 1:
                self._set_customer(state, customers[0])
            elif customers:
                state["candidates"] = customers
        elif name == "list_customer_orders" and status == "ok":
            customer_id = result.get("customer_id")
            known = {c["id"]: c for c in state.get("candidates") or []}
            current = state.get("current_customer") or {}
            customer = known.get(customer_id) or (current if current.get("id") == customer_id else None)
            self._set_customer(state, customer or lookup(customer_id) or {"id": customer_id, "name": customer_id})
        elif name == "get_order" and status in {"found", "approximate"}:
            order = result.get("order") or {}
            customer_id = order.get("customer_id")
            current = state.get("current_customer") or {}
            if customer_id and current.get("id") != customer_id:
                customer = lookup(customer_id)
                if customer:
                    self._set_customer(state, customer)
            state["current_order"] = {
                "reference": order.get("reference"),
                "status_label": order.get("status_label"),
                "customer_id": customer_id,
            }

    @staticmethod
    def _set_customer(state: dict, customer: dict) -> None:
        previous = (state.get("current_customer") or {}).get("id")
        state["current_customer"] = {k: customer.get(k) for k in ("id", "name", "city")}
        state.pop("candidates", None)
        order = state.get("current_order")
        if previous != customer.get("id") and order and order.get("customer_id") != customer.get("id"):
            state.pop("current_order", None)
