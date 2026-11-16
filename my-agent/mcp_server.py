"""MCP server of my agent: read tools wired to the business API.

Stateless streamable HTTP. The caller's bearer token is relayed to the business API on each call,
so the application applies the user's own permissions.
"""

from __future__ import annotations

import os
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context

# The SDK is installed in this environment: `agent_sdk.http_client` and `agent_sdk.tool_schema` help here.

NAME = "workshop-tools"
VERSION = "0.2.0"
MCP_PATH = "/mcp"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8004

MAX_ROWS = 20
LATE = "late"


class BusinessAPI:
    """HTTP client to the business API, with the caller's token."""

    _local = None

    def __init__(self, authorization: str | None):
        self.authorization = authorization or ""
        url = os.environ.get("BUSINESS_API_URL")
        if url:
            import httpx

            self._http = httpx.Client(base_url=url.rstrip("/"), timeout=15)
        else:
            # Test runs host the business API in the same process and export no URL.
            if BusinessAPI._local is None:
                from fastapi.testclient import TestClient

                from workshop_kit.apps.business_api.app import app

                BusinessAPI._local = TestClient(app)
            self._http = BusinessAPI._local

    def request(self, method: str, path: str, **kwargs) -> tuple[int, Any]:
        response = self._http.request(method, path, headers={"Authorization": self.authorization}, **kwargs)
        try:
            body = response.json()
        except ValueError:
            body = response.text
        return response.status_code, body


def _api(ctx: Context) -> BusinessAPI:
    headers = ctx.headers or {}
    return BusinessAPI(headers.get("authorization"))


# ----------------------------------------------------------------------------------------------- helpers


def _close(a: str, b: str) -> bool:
    """Same length and at most one substitution or one transposition of adjacent characters."""
    if len(a) != len(b) or a == b:
        return False
    diffs = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    if len(diffs) == 1:
        return True
    return len(diffs) == 2 and diffs[1] == diffs[0] + 1 and a[diffs[0]] == b[diffs[1]] and a[diffs[1]] == b[diffs[0]]


def _labelled(row: dict, meta: dict) -> dict:
    """Adds the business label next to every coded value."""
    out = dict(row)
    for field, codes in (meta.get("coded_values") or {}).items():
        if field in out and out[field] in codes:
            out[f"{field}_label"] = codes[out[field]]
    out.pop("organization_id", None)
    return out


def _source(api: BusinessAPI, name: str) -> tuple[dict | None, dict | None]:
    code, body = api.request("GET", f"/sources/{name}")
    if code == 200:
        return body, None
    code, listing = api.request("GET", "/sources")
    names = [s["name"] for s in listing] if code == 200 else []
    return None, {
        "status": "error",
        "error": f"unknown source {name!r}",
        "fix": "use one of the available sources",
        "available_sources": names,
    }


def _customer(api: BusinessAPI, customer_id: str | None) -> dict | None:
    if not customer_id:
        return None
    code, body = api.request("GET", f"/customers/{customer_id}")
    if code != 200:
        return None
    return {k: body.get(k) for k in ("id", "name", "city")}


def _normalize_filters(filters: Any, meta: dict, source: str) -> tuple[dict | None, bool, dict | None]:
    """Validates the filters; returns (api_filters, late_only, error)."""
    fields = dict(meta.get("fields") or {})
    allowed = set(fields) | {"id", "customer_id", "status"}
    coded = meta.get("coded_values") or {}
    if filters in (None, "", {}):
        return {}, False, None
    if not isinstance(filters, dict):
        return None, False, {
            "status": "error",
            "error": f"malformed filters {filters!r}: filters must be an object {{field: value}}",
            "fix": "pass for example {\"status\": \"delivered\"}; operators such as == are not accepted",
            "fields": sorted(allowed) + ([LATE] if source == "orders" else []),
            "values": {f: [{"code": c, "label": l} for c, l in codes.items()] for f, codes in coded.items()},
        }
    api_filters: dict[str, Any] = {}
    late_only = False
    for key, value in filters.items():
        if key == LATE and source == "orders":
            late_only = bool(value) and str(value).lower() not in {"false", "0", "non", "no"}
            continue
        if key not in allowed:
            return None, False, {
                "status": "error",
                "error": f"unknown filter field {key!r} for source {source!r}",
                "fix": "use one of the listed fields",
                "fields": sorted(allowed) + ([LATE] if source == "orders" else []),
            }
        if key in coded:
            codes = coded[key]
            by_label = {label.lower(): code for code, label in codes.items()}
            text = str(value).strip()
            if text in codes:
                value = text
            elif text.lower() in by_label:
                value = by_label[text.lower()]
            else:
                return None, False, {
                    "status": "error",
                    "error": f"invalid value {value!r} for {key!r}",
                    "fix": f"use one of the codes listed for {key!r} (a business label is accepted too)",
                    "values": [{"code": c, "label": l} for c, l in codes.items()],
                }
        api_filters[key] = value
    return api_filters, late_only, None


# ------------------------------------------------------------------------------------------------- tools


def get_order(reference: str, ctx: Context) -> dict:
    """Looks up one order by its reference (e.g. CMD-1234).

    Returns status 'found' with the order (and its customer), 'approximate' with the closest existing order
    when the reference does not exist, 'not_found' when nothing matches, or 'error'.
    """
    api = _api(ctx)
    reference = (reference or "").strip().upper()
    if not reference:
        return {"status": "error", "error": "missing reference", "fix": "pass a reference such as CMD-1042"}
    meta, _ = _source(api, "orders")
    meta = meta or {}
    code, body = api.request("GET", f"/orders/{reference}")
    if code == 200:
        order = _labelled(body, meta)
        order["customer"] = _customer(api, body.get("customer_id"))
        return {"status": "found", "order": order}
    if code != 404:
        return {"status": "error", "error": f"business API answered {code}", "reference": reference}
    # Not found: closest visible reference (excluded orders are never returned by the API).
    code, body = api.request("POST", "/sources/orders/query", json={"filters": {}})
    rows = body.get("rows", []) if code == 200 else []
    candidates = [r for r in rows if _close(reference, str(r.get("reference", "")).upper())]
    if len(candidates) == 1:
        order = _labelled(candidates[0], meta)
        order["customer"] = _customer(api, candidates[0].get("customer_id"))
        return {
            "status": "approximate",
            "requested_reference": reference,
            "detail": "the requested reference does not exist; closest existing order returned",
            "order": order,
        }
    return {
        "status": "not_found",
        "reference": reference,
        "detail": "order not found (absent or not accessible); no close reference",
    }


def find_by_name(name: str, ctx: Context, entity_type: str = "customer") -> dict:
    """Resolves a name to identifiers: entity_type is 'customer' (default), 'supplier' or 'user'.

    Returns every match, namesakes included, with their id (and city for customers). When nothing matches
    the requested type, the other types are searched too and the type actually found is reported.
    Never pick one of several matches on behalf of the user.
    """
    api = _api(ctx)
    types = ["customer", "supplier", "user"]
    if entity_type not in types:
        return {"status": "error", "error": f"unknown entity_type {entity_type!r}", "fix": "customer, supplier or user"}
    if not (name or "").strip():
        return {"status": "error", "error": "missing name"}
    matches: list[dict] = []
    found_type = entity_type
    for candidate_type in [entity_type] + [t for t in types if t != entity_type]:
        code, body = api.request("GET", "/resolution", params={"type": candidate_type, "name": name.strip()})
        if code != 200:
            return {"status": "error", "error": f"business API answered {code}"}
        matches = [{k: r.get(k) for k in ("id", "name", "city", "role") if r.get(k) is not None} for r in body]
        if matches:
            found_type = candidate_type
            break
    if not matches:
        return {"status": "not_found", "entity_type": entity_type, "name": name, "matches": [], "searched": types}
    result: dict[str, Any] = {"status": "ok", "entity_type": found_type, "count": len(matches), "matches": matches}
    if found_type != entity_type:
        result["note_type"] = f"no {entity_type} with this name; found as {found_type}"
    if len(matches) > 1:
        result["note"] = "several matches (namesakes): list them all and ask the user which one; never pick one"
    return result


def describe_source(source: str, ctx: Context) -> dict:
    """Describes a data source: fields, coded values with their business labels, relations and aggregates."""
    api = _api(ctx)
    meta, error = _source(api, source)
    if error:
        return error
    fields = dict(meta.get("fields") or {})
    if source == "orders":
        fields[LATE] = "true to keep only the orders whose delivery is late (applied by the tool)"
    return {"status": "ok", "source": source, **{k: v for k, v in meta.items() if k != "fields"}, "fields": fields}


def query(
    source: str,
    ctx: Context,
    filters: dict[str, Any] | str | None = None,
    aggregate: str | None = None,
    group_by: str | None = None,
    limit: int | None = None,
) -> dict:
    """Generic read query on a data source (orders, customers, invoices, suppliers, purchase_requests).

    filters: object {field: value} with equality semantics; coded values accept the code or the business label.
    On orders, {"late": true} keeps only late deliveries (applied here, never filter a list yourself).
    aggregate: 'count', 'total' or 'average' (amount); group_by: a field. Without aggregate, at most 20 rows
    are returned together with the total; use aggregate='count' when only the number is wanted.
    Every coded value comes back with its business label (field_label).
    """
    api = _api(ctx)
    meta, error = _source(api, source)
    if error:
        return error
    api_filters, late_only, error = _normalize_filters(filters, meta, source)
    if error:
        return error
    aggregates = meta.get("aggregates") or []
    if aggregate and aggregate not in aggregates:
        return {
            "status": "error",
            "error": f"aggregate {aggregate!r} is not offered for {source!r}",
            "fix": "use one of the available aggregates",
            "available_aggregates": aggregates,
        }
    cap = min(int(limit or MAX_ROWS), MAX_ROWS)
    body: dict[str, Any] = {"filters": api_filters}
    if late_only:
        # The late flag is computed: fetch the rows, filter them here, then aggregate or cap.
        code, data = api.request("POST", f"/sources/{source}/query", json=body)
        if code != 200:
            return {"status": "error", "error": f"business API answered {code}", "detail": data}
        rows = [r for r in data.get("rows", []) if r.get("late")]
        data = _local_aggregate(rows, aggregate, group_by) if (aggregate or group_by) else {"rows": rows, "total": len(rows)}
    else:
        if aggregate:
            body["aggregate"] = aggregate
        if group_by:
            body["group_by"] = group_by
        if not (aggregate or group_by):
            body["limit"] = cap
        code, data = api.request("POST", f"/sources/{source}/query", json=body)
        if code != 200:
            detail = data.get("detail") if isinstance(data, dict) else data
            return {"status": "error", "error": f"query refused ({code}): {detail}", "fields": sorted(meta.get("fields") or {})}
    if isinstance(data, dict) and data.get("refused"):
        return {"status": "error", "error": data.get("reason"), "available_aggregates": data.get("available_aggregates")}
    result: dict[str, Any] = {"status": "ok", "source": source, "filters": {**api_filters, **({LATE: True} if late_only else {})}}
    customer_id = api_filters.get("customer_id")
    if source == "orders" and customer_id:
        result["customer"] = _customer(api, customer_id)
    if "value" in data:
        result.update({"aggregate": data.get("aggregate"), "value": data.get("value"), "count": data.get("total")})
        return result
    if group_by:
        result.update({"group_by": group_by, "aggregate": aggregate, "groups": data.get("rows", [])})
        return result
    rows = data.get("rows", [])
    total = data.get("total")
    shown = rows[:cap]
    cap_reached = len(rows) > cap or bool(data.get("truncated")) or len(shown) >= cap
    total_is_minimum = total is None and cap_reached
    result.update(
        {
            "total": total if total is not None else len(shown),
            "total_is_minimum": total_is_minimum,
            "returned": len(shown),
            "cap": cap,
            "cap_reached": cap_reached,
            "rows": [_labelled(r, meta) for r in shown],
        }
    )
    if cap_reached and (total is None or total > len(shown)):
        result["truncated"] = True
        result["note"] = (
            f"partial list: only {len(shown)} rows shown (cap {cap}); "
            + (f"at least {len(shown)} rows exist (minimum)" if total_is_minimum else f"exact total {total}")
            + ". Say the answer is partial and give the total; use aggregate='count' for the number only."
        )
    return result


def _local_aggregate(rows: list[dict], aggregate: str | None, group_by: str | None) -> dict:
    def value(items: list[dict]) -> float | int:
        amounts = [float(r.get("amount") or 0) for r in items]
        if aggregate == "total":
            return round(sum(amounts), 2)
        if aggregate == "average":
            return round(sum(amounts) / len(amounts), 2) if amounts else 0
        return len(items)

    if group_by:
        groups: dict[str, list[dict]] = {}
        for r in rows:
            groups.setdefault(str(r.get(group_by, "")), []).append(r)
        return {"rows": [{"group": k, "count": len(v), aggregate or "count": value(v)} for k, v in groups.items()]}
    return {"value": value(rows), "aggregate": aggregate, "total": len(rows)}


def create_server() -> MCPServer:
    server = MCPServer(
        name=NAME,
        version=VERSION,
        instructions=(
            "Read tools of the customer service agent, wired to the business API with the caller's identity. "
            "Use find_by_name to resolve names, query for any read on a data source, get_order for one order."
        ),
    )
    server.tool()(get_order)
    server.tool()(find_by_name)
    server.tool()(describe_source)
    server.tool()(query)
    return server


def application():
    """Starlette application served by uvicorn (tests and local run)."""
    return create_server().streamable_http_app(
        stateless_http=True,
        json_response=True,
        streamable_http_path=MCP_PATH,
        host=DEFAULT_HOST,
    )


if __name__ == "__main__":
    port = int(os.environ.get("MCP_PORT", str(DEFAULT_PORT)))
    host = os.environ.get("MCP_HOST", DEFAULT_HOST)
    create_server().run(
        transport="streamable-http",
        host=host,
        port=port,
        stateless_http=True,
        json_response=True,
        streamable_http_path=MCP_PATH,
    )
