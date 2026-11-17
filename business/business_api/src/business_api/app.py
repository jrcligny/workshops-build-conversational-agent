"""HTTP API of the business application (FastAPI + OpenAPI)."""

from __future__ import annotations

import time
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from business_api.auth import decode_token, issue_token, user_from_header
from business_api.seed_data import DATASETS, case_catalog, load_dataset, user as user_record
from business_api.services import (
    SOURCES,
    active_failure,
    arm_failure,
    case_state,
    get_customer,
    get_draft,
    get_invoice,
    get_order,
    get_user_settings,
    list_orders,
    log_call,
    prepare_draft,
    query_source,
    read_call_log,
    resolve_name,
    search_customers,
    set_user_settings,
    submit_draft,
)
from workshop_config import settings

app = FastAPI(title="Business application of the running example", version="0.1.0")

WRITE_ROLES = {
    "purchase_request": {"buyer"},
    "invoice_approval": {"accountant"},
}


class ResetIn(BaseModel):
    dataset: str = "standard"


class TokenIn(BaseModel):
    user_id: str


class FailureIn(BaseModel):
    type: str | None = None
    active: bool = True


class QueryIn(BaseModel):
    filters: dict[str, Any] = Field(default_factory=dict)
    limit: int | None = None
    aggregate: str | None = None
    group_by: str | list[str] | None = None


class PurchaseRequestDraftIn(BaseModel):
    subject: str
    amount: float | None = None
    supplier_id: str | None = None


class UserSettingsIn(BaseModel):
    prefer_excl_tax: bool


def _require_observation(authorization: str | None) -> None:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing observation token")
    token = authorization.split(" ", 1)[1].strip()
    if token != settings.observation_token:
        raise HTTPException(status_code=401, detail="invalid observation token")


@app.middleware("http")
async def call_log_and_failures(request: Request, call_next):
    identity = None
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        # The observation token is not a JWT; decoding errors are ignored here.
        try:
            identity = decode_token(auth.split(" ", 1)[1].strip())
        except Exception:  # noqa: BLE001
            identity = None
    if request.url.path.startswith("/observation"):
        return await call_next(request)
    failure = active_failure()
    if failure == "unavailable" and request.method in {"GET", "POST"}:
        log_call(request.method, request.url.path, identity, 503)
        return JSONResponse({"detail": "application unavailable"}, status_code=503)
    if failure == "latency":
        time.sleep(0.05)
    response = await call_next(request)
    log_call(request.method, request.url.path, identity, response.status_code)
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/customers")
def api_customers(name: str, identity: dict = Depends(user_from_header)):
    return search_customers(name, identity)


@app.get("/customers/{customer_id}")
def api_customer(customer_id: str, identity: dict = Depends(user_from_header)):
    customer = get_customer(customer_id, identity)
    if not customer:
        raise HTTPException(status_code=404, detail="customer not found")
    return customer


@app.get("/customers/{customer_id}/orders")
def api_customer_orders(
    customer_id: str,
    filter: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    identity: dict = Depends(user_from_header),
):
    if not get_customer(customer_id, identity):
        raise HTTPException(status_code=404, detail="customer not found")
    return list_orders(customer_id, identity, filter=filter, limit=limit, offset=offset)


@app.get("/orders/{reference}")
def api_order(reference: str, identity: dict = Depends(user_from_header)):
    order = get_order(reference, identity)
    if not order:
        raise HTTPException(status_code=404, detail="order not found")
    return order


@app.get("/resolution")
def api_resolution(type: str, name: str, identity: dict = Depends(user_from_header)):
    return resolve_name(type, name, identity)


@app.get("/sources")
def api_sources(identity: dict = Depends(user_from_header)):
    return [{"name": name, "description": meta["description"]} for name, meta in SOURCES.items()]


@app.get("/sources/{name}")
def api_source(name: str, identity: dict = Depends(user_from_header)):
    if name not in SOURCES:
        raise HTTPException(status_code=404, detail="unknown source")
    return {"name": name, **SOURCES[name]}


@app.post("/sources/{name}/query")
def api_query(name: str, body: QueryIn, identity: dict = Depends(user_from_header)):
    try:
        return query_source(name, identity, body.filters, body.limit, body.aggregate, body.group_by)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _require_role(identity: dict, typ: str) -> None:
    if identity.get("role") not in WRITE_ROLES[typ]:
        raise HTTPException(status_code=403, detail="insufficient write permission")


@app.post("/purchase-requests/drafts")
def api_prepare_purchase_request(body: PurchaseRequestDraftIn, identity: dict = Depends(user_from_header)):
    _require_role(identity, "purchase_request")
    return prepare_draft("purchase_request", body.model_dump(), identity)


@app.post("/invoices/{invoice_id}/approval/drafts")
def api_prepare_invoice_approval(invoice_id: str, identity: dict = Depends(user_from_header)):
    _require_role(identity, "invoice_approval")
    if not get_invoice(invoice_id, identity):
        raise HTTPException(status_code=404, detail="invoice not found")
    return prepare_draft("invoice_approval", {"invoice_id": invoice_id}, identity)


@app.get("/drafts/{draft_id}")
def api_draft(draft_id: str, identity: dict = Depends(user_from_header)):
    draft = get_draft(draft_id, identity)
    if not draft:
        raise HTTPException(status_code=404, detail="draft not found")
    return draft


@app.post("/drafts/{draft_id}/submit")
def api_submit(draft_id: str, identity: dict = Depends(user_from_header)):
    draft = get_draft(draft_id, identity)
    if not draft:
        raise HTTPException(status_code=404, detail="draft not found")
    _require_role(identity, draft["type"])
    try:
        return submit_draft(draft_id, identity)
    except RuntimeError as exc:
        if str(exc) == "unknown_outcome":
            raise HTTPException(status_code=504, detail="unknown outcome") from exc
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/invoices/{invoice_id}")
def api_invoice(invoice_id: str, identity: dict = Depends(user_from_header)):
    invoice = get_invoice(invoice_id, identity)
    if not invoice:
        raise HTTPException(status_code=404, detail="invoice not found")
    return invoice


@app.get("/settings")
def api_get_settings(identity: dict = Depends(user_from_header)):
    return get_user_settings(identity)


@app.post("/settings")
def api_set_settings(body: UserSettingsIn, identity: dict = Depends(user_from_header)):
    return set_user_settings(identity, body.prefer_excl_tax)


# --- Observation (teaching token, never a tool) ---


@app.post("/observation/reset")
def obs_reset(body: ResetIn, request: Request):
    _require_observation(request.headers.get("authorization"))
    if body.dataset not in DATASETS:
        raise HTTPException(status_code=400, detail=f"unknown dataset: {body.dataset}")
    load_dataset(body.dataset)
    return {"dataset": body.dataset, "cases": case_catalog()}


@app.get("/observation/state")
def obs_state(case: str, request: Request):
    _require_observation(request.headers.get("authorization"))
    return case_state(case)


@app.get("/observation/log")
def obs_log(request: Request):
    _require_observation(request.headers.get("authorization"))
    return read_call_log()


@app.post("/observation/failures")
def obs_failures(body: FailureIn, request: Request):
    _require_observation(request.headers.get("authorization"))
    arm_failure(body.type, body.active)
    return {"type": body.type, "active": body.active}


@app.post("/observation/test-token")
def obs_test_token(body: TokenIn, request: Request):
    _require_observation(request.headers.get("authorization"))
    record = user_record(body.user_id)
    if not record:
        raise HTTPException(status_code=404, detail="unknown test user")
    app_token = issue_token(record["id"], record["role"], record["organization_id"], typ="application")
    entry_token = issue_token(record["id"], record["role"], record["organization_id"], typ="entry")
    return {
        "user": record,
        "app_token": app_token,
        "entry_token": entry_token,
        "comment": "The entry token simulates the one received by the tool server; the business API only accepts the application token.",
    }


@app.get("/observation/catalog")
def obs_catalog(request: Request):
    _require_observation(request.headers.get("authorization"))
    return case_catalog()


def create_app() -> FastAPI:
    return app
