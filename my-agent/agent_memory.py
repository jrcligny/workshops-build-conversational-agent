"""Working memory: explicit conversation state, kept outside the history so it survives compaction."""

from __future__ import annotations

import copy
import json
from typing import Any


class WorkingMemory:
    """Current customer, current order and pending namesake choice, per conversation.

    The state is updated from tool results only (never from what the model writes), so it holds only
    what the application confirmed.
    """

    def __init__(self) -> None:
        self._states: dict[str, dict[str, Any]] = {}
        # Conversations whose namesake candidates appeared in the current turn: the user has not chosen yet.
        self._choice_pending: set[str] = set()

    def bind(self, conversation_id: str, state: dict[str, Any]) -> None:
        """The state lives in the conversation context (agent_sdk.context ctx.state): updated in place."""
        self._states[conversation_id] = state

    def rebuild(self, conversation_id: str, messages: list[dict[str, Any]], lookup) -> None:
        """A loaded conversation comes without state: replay its tool results, turn by turn, to rebuild it.

        Written histories may name neutral tools (resolve_name, query, search_customers, list_orders): their
        results are read the same way as those of find_by_name and query."""
        calls: dict[str, tuple[str, dict]] = {}
        for message in messages:
            role = message.get("role")
            if role == "user":
                self.begin_turn(conversation_id)
            elif role == "assistant":
                for call in message.get("tool_calls") or []:
                    function = call.get("function") or {}
                    try:
                        arguments = json.loads(function.get("arguments") or "{}")
                    except (TypeError, ValueError):
                        arguments = {}
                    calls[call.get("id", "")] = (function.get("name", ""), arguments if isinstance(arguments, dict) else {})
            elif role == "tool":
                name, arguments = calls.get(message.get("tool_call_id", ""), (message.get("name", ""), {}))
                try:
                    result = json.loads(message.get("content") or "")
                except (TypeError, ValueError):
                    continue  # a cleared result (marker): nothing to read
                if isinstance(result, dict):
                    self.update(conversation_id, *_normalized(name or message.get("name", ""), arguments, result), lookup)

    def begin_turn(self, conversation_id: str) -> None:
        self._choice_pending.discard(conversation_id)

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
        listing = state.get("last_listing")
        if listing:
            following = (
                f"suite avec query(source orders, filters {listing['filters']}, offset {listing['next_offset']})"
                if listing.get("next_offset") is not None
                else "aucune ligne suivante"
            )
            lines.append(
                f"- dernière liste de commandes : lignes 1 à {listing['returned_until']} reçues sur {listing['total']} "
                f"({listing['total_status']}) ; {following}"
            )
        return "\n".join(lines)

    def update(self, conversation_id: str, name: str, arguments: dict, result: dict, lookup) -> None:
        state = self._states.setdefault(conversation_id, {})
        status = result.get("status")
        if name == "find_by_name" and status == "ok" and result.get("entity_type") == "customer":
            customers = result.get("matches") or []
            if len(customers) == 1:
                self._set_customer(state, customers[0])
            elif customers:
                state["candidates"] = customers
                self._choice_pending.add(conversation_id)
        elif name == "query" and status == "ok" and result.get("source") == "customers":
            rows = result.get("rows") or []
            if len(rows) == 1 and rows[0].get("id"):
                # One customer read (for instance the namesake the user just chose): the conversation is about him.
                self._set_customer(state, rows[0])
        elif name == "query" and status == "ok" and result.get("source") == "orders":
            customer_id = (result.get("filters") or {}).get("customer_id")
            known = {c["id"]: c for c in state.get("candidates") or []}
            if customer_id and customer_id in known and conversation_id in self._choice_pending:
                # Control: a namesake is recorded as current customer only after the user's choice.
                return
            orders = result.get("rows") if not result.get("group_by") else None
            if isinstance(orders, list) and "total" in result:
                state["last_listing"] = {
                    "filters": result.get("filters"),
                    "returned_until": (result.get("offset") or 0) + (result.get("returned") or 0),
                    "next_offset": result.get("next_offset"),
                    "total": result.get("total"),
                    "total_status": result.get("total_status"),
                }
            if customer_id:
                current = state.get("current_customer") or {}
                customer = (
                    result.get("customer")
                    or known.get(customer_id)
                    or (current if current.get("id") == customer_id else None)
                    or lookup(customer_id)
                )
                self._set_customer(state, customer or {"id": customer_id, "name": customer_id})
                orders = orders or []
                if len(orders) == 1 and result.get("total") == 1 and orders[0].get("reference"):
                    # The customer's only order is the one the conversation is about.
                    state["current_order"] = {
                        "reference": orders[0]["reference"],
                        "status_label": orders[0].get("status_label") or orders[0].get("status"),
                        "customer_id": customer_id,
                    }
        elif name == "get_order" and status in {"found", "approximate"}:
            order = result.get("order") or {}
            customer_id = order.get("customer_id")
            current = state.get("current_customer") or {}
            if customer_id and current.get("id") != customer_id:
                customer = order.get("customer") or lookup(customer_id)
                if customer:
                    self._set_customer(state, customer)
            state["current_order"] = {
                "reference": order.get("reference"),
                "status_label": order.get("status_label") or order.get("status"),
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


def _normalized(name: str, arguments: dict, result: dict) -> tuple[str, dict, dict]:
    """Maps the results of neutral tool names (written histories) onto this agent's own tools."""
    if name in ("resolve_name", "search_customers"):
        entity_type = arguments.get("entity_type") or "customer"
        matches = result.get("matches") or result.get("customers") or []
        status = result.get("status") or ("ok" if matches else "not_found")
        return "find_by_name", arguments, {"status": status, "entity_type": entity_type, "matches": matches}
    if name in ("query", "list_orders") and "rows" in result or name == "list_orders":
        filters = dict(arguments.get("filters") or {})
        if arguments.get("customer_id"):
            filters["customer_id"] = arguments["customer_id"]
        rows = result.get("rows") if "rows" in result else result.get("orders") or []
        source = arguments.get("source") or "orders"
        offset = result.get("offset") or arguments.get("offset") or 0
        return "query", arguments, {
            **result, "status": result.get("status") or "ok", "source": source, "filters": filters, "rows": rows,
            "offset": offset, "returned": result.get("returned", len(rows)), "next_offset": result.get("next_offset"),
            "total": result.get("total", len(rows)), "total_status": result.get("total_status", "exact"),
        }
    if name == "get_order" and result.get("status") == "ok":
        return name, arguments, {**result, "status": "found"}
    return name, arguments, result
