"""MCP server of my agent: read tools wired to the business API.

Stateless streamable HTTP. The caller's bearer token is relayed to the business API on each call,
so the application applies the user's own permissions.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context

# The SDK is installed in this environment: `agent_sdk.http_client` and `agent_sdk.tool_schema` help here.
# Loaded by path by the gateway and the tests: its sibling module agent_sandbox must stay importable.
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent_sandbox  # noqa: E402

NAME = "workshop-tools"
VERSION = "0.2.0"
MCP_PATH = "/mcp"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8004

MAX_ROWS = 20
LATE = "late"


class IdentityRefused(Exception):
    """The request carries no valid user identity: the tool server refuses it."""


ACCEPTED_TYPES = {"entry", "application"}
EXCHANGED_TOKEN_MINUTES = 5


def exchange(authorization: str | None) -> tuple[str, dict]:
    """Checks the caller's token and exchanges it for a distinct token for the business API.

    The new token is issued for the application, on behalf of the same user (sub, role, organization),
    with this server as actor. The received token is never relayed, and no service account exists.
    """
    import uuid
    from datetime import datetime, timedelta, timezone

    import jwt

    from business_api.auth import ALGORITHM, ROLES
    from workshop_config import settings

    if not authorization or not authorization.lower().startswith("bearer "):
        raise IdentityRefused("missing identity: the request carries no user token")
    try:
        claims = jwt.decode(authorization.split(" ", 1)[1].strip(), settings.token_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise IdentityRefused(f"invalid user token ({type(exc).__name__})") from exc
    if claims.get("typ") not in ACCEPTED_TYPES:
        raise IdentityRefused(f"token type {claims.get('typ')!r} is not accepted")
    if not claims.get("sub") or not claims.get("organization") or claims.get("role") not in ROLES:
        raise IdentityRefused("incomplete identity: user, role or organization missing")
    now = datetime.now(timezone.utc)
    exchanged = {
        "sub": claims["sub"],
        "role": claims["role"],
        "organization": claims["organization"],
        "typ": "application",
        "act": {"sub": NAME},
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=EXCHANGED_TOKEN_MINUTES)).timestamp()),
    }
    return jwt.encode(exchanged, settings.token_secret, algorithm=ALGORITHM), exchanged


class BusinessAPI:
    """HTTP client to the business API, with a token exchanged for the caller."""

    _local = None
    URL_VARIABLE = "BUSINESS_API_URL"
    LABEL = "business API"

    @staticmethod
    def _local_app():
        from business_api.app import app

        return app

    def __init__(self, authorization: str | None):
        token, self.claims = exchange(authorization)
        self.authorization = f"Bearer {token}"
        url = os.environ.get(self.URL_VARIABLE)
        if url:
            import httpx

            allowed, reason = agent_sandbox.egress_decision(url)
            if not allowed:
                raise IdentityRefused(f"{self.LABEL} unreachable from the sandbox: {reason}")
            self._http = httpx.Client(base_url=url.rstrip("/"), timeout=15, follow_redirects=False)
        else:
            # Test runs host the application in the same process and export no URL.
            cls = type(self)
            if cls._local is None:
                from fastapi.testclient import TestClient

                cls._local = TestClient(self._local_app())
            self._http = cls._local

    def request(self, method: str, path: str, **kwargs) -> tuple[int, Any]:
        response = self._http.request(method, path, headers={"Authorization": self.authorization}, **kwargs)
        try:
            body = response.json()
        except ValueError:
            body = response.text
        return response.status_code, body


class DocsSearch(BusinessAPI):
    """HTTP client to the repository's document search application, with the same exchanged identity."""

    _local = None
    URL_VARIABLE = "DOCS_SEARCH_URL"
    LABEL = "document search"

    @staticmethod
    def _local_app():
        from docs_search.app import app

        return app


def _guarded(tool):
    """Turns an identity refusal into an explicit tool result instead of a protocol failure."""
    import functools

    @functools.wraps(tool)
    def wrapper(*args, **kwargs):
        try:
            return tool(*args, **kwargs)
        except IdentityRefused as exc:
            return {
                "status": "error",
                "error": f"request refused by the tool server: {exc}",
                "refused": True,
                "fix": "the user's identity could not be verified; no data can be read on their behalf",
            }

    return wrapper


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
                    "error": f"invalid value {value!r} for {key!r}; allowed values: "
                    + ", ".join(f"{c} ({l})" for c, l in codes.items()),
                    "fix": f"use one of the codes listed for {key!r} (a business label is accepted too)",
                    "values": [{"code": c, "label": l} for c, l in codes.items()],
                }
        api_filters[key] = value
    return api_filters, late_only, None


# ------------------------------------------------------------------------------------------------- tools


ORDER_REFERENCE = re.compile(r"CMD-[A-Z0-9]+(?:-[A-Z0-9]+)*")


def get_order(reference: str, ctx: Context) -> dict:
    """Looks up one order by its reference (e.g. CMD-1234).

    Returns status 'found' with the order (and its customer), 'approximate' with the closest existing order
    when the reference does not exist, 'not_found' when nothing matches, or 'error'.
    """
    api = _api(ctx)
    reference = (reference or "").strip().upper()
    if not reference:
        return {"status": "error", "error": "missing reference", "fix": "pass a reference such as CMD-1042"}
    if not ORDER_REFERENCE.fullmatch(reference):
        return {
            "status": "error",
            "error": f"invalid reference {reference!r}: an order reference is CMD- followed by letters or digits, optionally in hyphenated groups (CMD-1042, CMD-B-100)",
            "fix": "ask the user for a reference such as CMD-1042",
        }
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
        # Only the reference is suggested: the close order's details wait for the user's confirmation.
        return {
            "status": "approximate",
            "requested_reference": reference,
            "detail": "the requested reference does not exist; ask the user whether they meant the suggested reference",
            "suggestions": [candidates[0].get("reference")],
        }
    return {
        "status": "not_found",
        "reference": reference,
        "detail": "order not found (absent or not accessible); no close reference",
    }


def find_by_name(name: str, ctx: Context, entity_type: str = "customer", city: str | None = None) -> dict:
    """Resolves a name to identifiers: entity_type is 'customer' (default), 'supplier' or 'user'.

    Returns every match, namesakes included, with their id (and city for customers). When nothing matches
    the requested type, the other types are searched too and the type actually found is reported.
    city: pass it only when the user named the city; matches from other cities are then left out.
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
    if city and city.strip():
        wanted = city.strip().casefold()
        same_city = [m for m in matches if str(m.get("city") or "").casefold() == wanted]
        if not same_city:
            return {"status": "not_found", "entity_type": found_type, "name": name, "city": city,
                    "matches": [], "other_cities": sorted({str(m.get("city")) for m in matches if m.get("city")})}
        matches = same_city
    result: dict[str, Any] = {"status": "ok", "entity_type": found_type, "count": len(matches), "matches": matches}
    if found_type != entity_type:
        result["note_type"] = f"no {entity_type} with this name; found as {found_type}"
    if len(matches) > 1:
        result["note"] = "several matches (namesakes): never pick one yourself. If the user already designated one (e.g. by city) or asked about all of them, use those ids (in parallel when several); otherwise list them all and ask which one"
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
    group_by: list[str] | str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    filter: str | None = None,
) -> dict:
    """Generic read query on a data source (orders, customers, invoices, suppliers, purchase_requests).

    filters: object {field: value} with equality semantics; coded values accept the code or the business label.
    filter: 'late' (orders only) keeps only late deliveries, selected by the application, never by you.
    aggregate: 'count', 'total' or 'average' (amount), computed by the application. A number of rows is always
    aggregate='count', never a list counted afterwards.
    group_by: list of fields (e.g. ["supplier_id", "month"]); 'month' groups by the month of the source's date.
    Without aggregate, a bounded portion of at most 20 summarized rows comes back with `returned`, `total`,
    `total_status` ('exact', or 'minimum' when the application's retrieval cap is reached), `truncated`,
    `offset` and `next_offset`; pass offset=next_offset for the following portion, only when asked.
    The detail of one order (amount, delivery) comes from get_order.
    Every coded value comes back with its business label (field_label).
    """
    api = _api(ctx)
    meta, error = _source(api, source)
    if error:
        return error
    api_filters, late_only, error = _normalize_filters(filters, meta, source)
    if error:
        return error
    if filter not in (None, ""):
        if filter != LATE or source != "orders":
            return {"status": "error", "error": f"unknown filter {filter!r}; allowed values: late (orders only)",
                    "fix": "filter is 'late' on orders, or omitted"}
        late_only = True
    if late_only:
        api_filters[LATE] = True
    keys = [group_by] if isinstance(group_by, str) else [str(k) for k in group_by or [] if k]
    aggregates = meta.get("aggregates") or []
    if aggregate and aggregate not in aggregates:
        # The application states the refusal itself (with the aggregates it offers) when it knows the request.
        code, data = api.request("POST", f"/sources/{source}/query", json={"filters": {}, "aggregate": aggregate})
        if code == 200 and isinstance(data, dict) and data.get("refused"):
            return {
                "status": "error",
                "refused": True,
                "error": f"refused by the application: {data.get('reason')}",
                "available_aggregates": data.get("available_aggregates") or aggregates,
            }
        return {
            "status": "error",
            "error": f"aggregate {aggregate!r} is not offered for {source!r}",
            "fix": "use one of the available aggregates",
            "available_aggregates": aggregates,
        }
    cap = max(1, min(int(limit or MAX_ROWS), MAX_ROWS))
    body: dict[str, Any] = {"filters": api_filters}
    if aggregate:
        body["aggregate"] = aggregate
    if keys:
        body["group_by"] = keys
    if keys or not aggregate:
        body["limit"] = cap
        body["offset"] = max(int(offset or 0), 0)
    code, data = api.request("POST", f"/sources/{source}/query", json=body)
    if code != 200:
        detail = data.get("detail") if isinstance(data, dict) else data
        return {"status": "error", "error": f"query refused ({code}): {detail}",
                "fields": sorted(meta.get("fields") or {}) + ([LATE] if source == "orders" else [])}
    if isinstance(data, dict) and data.get("refused"):
        return {"status": "error", "refused": True, "error": data.get("reason"),
                "available_aggregates": data.get("available_aggregates")}
    result: dict[str, Any] = {"status": "ok", "source": source, "filters": api_filters}
    customer_id = api_filters.get("customer_id")
    if source == "orders" and customer_id:
        result["customer"] = _customer(api, customer_id)
    if "value" in data:
        result.update(
            {
                "aggregate": data.get("aggregate"),
                "value": data.get("value"),
                "count": data.get("total"),
                "computed_by": "business application (query tool), not by the model",
            }
        )
        return result
    if keys:
        rows = _named_groups(api, data.get("rows", []), keys, meta)
        result.update({"group_by": keys, "aggregate": aggregate,
                       "computed_by": "business application (query tool), not by the model"})
    else:
        rows = [_summary(_labelled(r, meta), source) for r in data.get("rows", [])]
    result.update(
        {
            "rows": rows,
            "returned": len(rows),
            "total": data.get("total"),
            "total_status": data.get("total_status") or "exact",
            "truncated": bool(data.get("truncated")),
            "offset": data.get("offset", 0),
            "next_offset": data.get("next_offset"),
        }
    )
    if result["truncated"]:
        minimum = result["total_status"] == "minimum"
        what = "groups" if keys else "rows"
        result["note"] = (
            f"partial result: only an extract of {len(rows)} {what} is shown; total "
            + (f"is a MINIMUM: at least {result['total']} {what} (application retrieval cap): write "
               f"'au moins {result['total']}'" if minimum else f"{result['total']} (exact)")
            + ". Say the answer is partial and give the total"
            + (f"; next portion with offset={result['next_offset']}, only when the user asks for it"
               if result["next_offset"] is not None else "")
            + "."
        )
    return result


def _named_groups(api: BusinessAPI, rows: list[dict], keys: list[str], meta: dict) -> list[dict]:
    """Adds `<key>_name` to the groups whose key is a relation (supplier_id -> suppliers.id), so that the answer
    names suppliers or customers instead of quoting their identifiers."""
    relations = {k: str(v).split(".")[0] for k, v in (meta.get("relations") or {}).items() if k in keys}
    if not relations:
        return rows
    values = {k: set() for k in relations}
    for row in rows:
        group = row.get("group")
        for key in relations:
            value = group.get(key) if isinstance(group, dict) else (group if len(keys) == 1 else None)
            if value:
                values[key].add(str(value))
    names = {key: _names_of(api, relations[key], ids) for key, ids in values.items() if ids}
    named = []
    for row in rows:
        row = dict(row)
        group = row.get("group")
        for key, found in names.items():
            if isinstance(group, dict) and group.get(key) in found:
                row["group"] = {**row["group"], f"{key}_name": found[group[key]]}
            elif not isinstance(group, dict) and str(group) in found:
                row[f"{key}_name"] = found[str(group)]
        named.append(row)
    return named


def _names_of(api: BusinessAPI, source: str, ids: set[str], pages: int = 10) -> dict[str, str]:
    """Names of the records of `source` whose id is in `ids`, read page by page from the application."""
    found: dict[str, str] = {}
    offset = 0
    for _ in range(pages):
        code, data = api.request("POST", f"/sources/{source}/query",
                                 json={"filters": {}, "limit": MAX_ROWS, "offset": offset})
        if code != 200 or not isinstance(data, dict):
            break
        for row in data.get("rows", []):
            if str(row.get("id")) in ids and row.get("name"):
                found[str(row["id"])] = row["name"]
        offset = data.get("next_offset")
        if ids <= set(found) or offset is None:
            break
    return found


# Detail fields left out of a listed order: they come from get_order, one order at a time.
ORDER_DETAIL_FIELDS = {"amount", "delivery_city", "delivery_date", "customer_id", "organization_id", "deleted"}
HIDDEN_FIELDS = {"organization_id", "deleted"}


def _summary(row: dict, source: str) -> dict:
    hidden = ORDER_DETAIL_FIELDS if source == "orders" else HIDDEN_FIELDS
    return {k: v for k, v in row.items() if k not in hidden}


# ------------------------------------------------------------------------------------------------ writes

# Who may prepare what. The business API enforces the same rule; the server refuses before calling it.
WRITE_PERMISSIONS = {
    "prepare_purchase_request": {"buyer"},
    "prepare_invoice_approval": {"accountant"},
}
DRAFT_TYPES = {"purchase_request": "prepare_purchase_request", "invoice_approval": "prepare_invoice_approval"}
# Submission is the harness's job after the user's gesture: never offered to the model.
HARNESS_ONLY_TOOLS = {"submit_draft", "check_record"}


def allowed_tools(role: str | None) -> set[str]:
    return {tool for tool, roles in WRITE_PERMISSIONS.items() if role in roles}


def _permission_refusal(tool: str, api: BusinessAPI) -> dict | None:
    role = api.claims.get("role")
    if role in WRITE_PERMISSIONS[tool]:
        return None
    return {
        "status": "error",
        "refused": True,
        "error": f"permission refused: the role {role!r} is not allowed to use {tool}",
        "fix": "no draft was prepared; the user does not have the right to request this action",
    }


def _draft_result(code: int, body: Any, what: str) -> dict:
    if code == 403:
        return {"status": "error", "refused": True, "error": "permission refused by the application"}
    if code != 200:
        detail = body.get("detail") if isinstance(body, dict) else body
        return {"status": "error", "error": f"{what} refused ({code}): {detail}"}
    return {
        "status": "draft",
        "draft": body,
        "submitted": False,
        "note": (
            "draft only: NOTHING has been submitted. The user must confirm with the confirmation button of the "
            "interface; never say it is submitted or sent."
        ),
    }


def prepare_purchase_request(subject: str, ctx: Context, amount: float | None = None, supplier_id: str | None = None) -> dict:
    """Prepares a purchase request DRAFT (subject, amount in euros, optional supplier id).

    Nothing is submitted: the draft waits for the user's confirmation gesture in the interface.
    """
    api = _api(ctx)
    refusal = _permission_refusal("prepare_purchase_request", api)
    if refusal:
        return refusal
    if not (subject or "").strip():
        return {"status": "error", "error": "missing subject"}
    payload = {"subject": subject.strip(), "amount": amount, "supplier_id": supplier_id}
    code, body = api.request("POST", "/purchase-requests/drafts", json=payload)
    return _draft_result(code, body, "purchase request draft")


def prepare_invoice_approval(invoice: str, ctx: Context) -> dict:
    """Prepares the approval DRAFT of a supplier invoice (its id or its reference).

    Nothing is approved: the draft waits for the user's confirmation gesture in the interface.
    """
    api = _api(ctx)
    refusal = _permission_refusal("prepare_invoice_approval", api)
    if refusal:
        return refusal
    invoice = (invoice or "").strip()
    code, data = api.request("POST", "/sources/invoices/query", json={"filters": {"reference": invoice}})
    rows = data.get("rows", []) if code == 200 else []
    invoice_id = rows[0]["id"] if rows else invoice
    original = rows[0].get("duplicate_of") if rows else None
    code, body = api.request("POST", f"/invoices/{invoice_id}/approval/drafts")
    if code == 404:
        return {"status": "not_found", "error": f"invoice {invoice!r} not found"}
    result = _draft_result(code, body, "invoice approval draft")
    if original:
        # A probable duplicate is flagged on the draft: the user decides when confirming, warned.
        result["duplicate_suspected"] = True
        result["duplicate_of"] = original
        result["warning"] = (f"invoice {invoice!r} looks like a duplicate of {original}: tell the user before they "
                             "confirm; nothing is approved without their gesture")
    return result


def submit_draft(draft_id: str, ctx: Context) -> dict:
    """Submits a draft confirmed by the user. Called by the harness only, after the confirmation gesture."""
    api = _api(ctx)
    code, draft = api.request("GET", f"/drafts/{draft_id}")
    if code != 200:
        return {"status": "error", "error": f"draft {draft_id!r} not found"}
    refusal = _permission_refusal(DRAFT_TYPES.get(draft.get("type"), ""), api) if draft.get("type") in DRAFT_TYPES else None
    if refusal:
        return refusal
    if draft.get("submitted"):
        return {"status": "error", "error": "draft already submitted", "draft_id": draft_id}
    code, body = api.request("POST", f"/drafts/{draft_id}/submit")
    if code == 504:
        return {"status": "unknown_outcome", "error": "the application did not report the outcome", "draft_id": draft_id}
    if code != 200:
        detail = body.get("detail") if isinstance(body, dict) else body
        return {"status": "error", "error": f"submission refused ({code}): {detail}", "draft_id": draft_id}
    return {"status": "submitted", "draft_id": draft_id, "result": body}


RECORD_ROUTE = re.compile(r"(orders|invoices|customers|suppliers|purchase-requests)/[A-Za-z0-9][A-Za-z0-9_-]*")


def check_record(record: str, ctx: Context) -> dict:
    """Can the user consult this business record (e.g. orders/CMD-2010)? Called by the harness only.

    Read with the user's own (exchanged) token: the application applies their organization and role.
    """
    record = (record or "").strip().strip("/")
    if not RECORD_ROUTE.fullmatch(record):
        return {"status": "denied", "record": record, "error": "not a business record route"}
    code, _ = _api(ctx).request("GET", f"/{record}")
    if code == 200:
        return {"status": "ok", "record": record}
    return {"status": "not_found" if code == 404 else "denied", "record": record, "code": code}


def search_documents(ctx: Context, query: str) -> dict:
    """Searches the internal documentation (procedures, definitions) for passages answering a question.

    Returns only the passages the user may read (their organization and role). Use it for "what does the
    procedure / documentation say"; use the data tools for the state of an order, invoice, etc.
    An empty result is declared explicitly (status no_passage): then answer that the documentation does not mention it ("ne mentionne pas").
    """
    code, body = DocsSearch((ctx.headers or {}).get("authorization")).request(
        "POST", "/search", json={"query": query, "k": 5, "threshold": 0.3}
    )
    if code != 200:
        return {"status": "error", "error": f"document search answered {code}", "query": query}
    passages = [
        {
            "id": p["id"],
            "document_id": p["document_id"],
            "title": p["title"],
            "section": p["section"],
            "version": p["version"],
            "address": p["address"],
            "audience": p.get("audience"),
            "score": p.get("score"),
            "text": p["text"][:1500],
        }
        for p in body.get("passages") or []
    ]
    if not passages:
        return {
            "status": "no_passage",
            "query": query,
            "no_passage": True,
            "passages": [],
            "note": "no passage of the documentation available to this user answers the question",
        }
    return {
        "status": "found",
        "query": query,
        "no_passage": False,
        "passages": passages,
        "note": (
            "documentation passages, filtered by the user's organization and role, ranked by a search that "
            "may return off-topic passages: use only those that answer the question, cite them as "
            "documentation and mark each one used with [source: <id>]"
        ),
    }


def fetch_url(url: str) -> dict:
    """Fetches a web page by URL, within the sandbox: only destinations on the allowlist are reached.

    Any other destination (or any scheme other than http/https, such as file://) is refused.
    """
    allowed, reason = agent_sandbox.egress_decision(url)
    if not allowed:
        return {"status": "refused", "url": url, "error": reason, "policy": "sandbox allowlist"}
    import httpx

    try:
        response = httpx.get(url, timeout=10, follow_redirects=False)
    except httpx.HTTPError as exc:
        return {"status": "error", "url": url, "error": f"{type(exc).__name__}"}
    text = response.text
    return {"status": "fetched", "url": url, "code": response.status_code, "content": text[:4000], "truncated": len(text) > 4000}


def create_server() -> MCPServer:
    server = MCPServer(
        name=NAME,
        version=VERSION,
        instructions=(
            "Read tools of the customer service agent, wired to the business API with the caller's identity. "
            "Use find_by_name to resolve names, query for any read on a data source (orders of one customer: "
            "source 'orders', filters {customer_id}, filter 'late' for late deliveries), get_order for one order."
        ),
    )
    for tool in (
        get_order, find_by_name, describe_source, query, search_documents, fetch_url,
        prepare_purchase_request, prepare_invoice_approval, submit_draft, check_record,
    ):
        server.tool()(_guarded(tool))
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
