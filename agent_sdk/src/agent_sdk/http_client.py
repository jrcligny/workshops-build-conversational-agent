"""HTTP transport to the business API and the document search: no business logic.

What it gives you: `business_api(token)` and `docs_search(token)` return a `ServiceClient`
whose `get(path, params=None)` and `post(path, json=None)` send the request with
`Authorization: Bearer <token>`, a timeout, and return the decoded JSON. The base URL is read
from `BUSINESS_API_URL` / `DOCS_SEARCH_URL` at each call. Any failure raises `ServiceError`,
with `status_code` (None when the service could not be reached) and the `detail` it returned.
Connections are pooled and reused between calls (one HTTP client per process): a tool that
checks several candidates stays fast.

`exchange_entry_token(entry_token)` calls the simulated token service (`POST /auth/exchange`
of the business API): the interface gives your harness an *entry* token (`TestUser.app_token`,
`typ` = "entry"), which the business API refuses; the exchange returns the *application* token
of the same user, the only one the business API accepts. It raises `ServiceError` (401) for a
missing, forged, expired or non-entry token.

What stays yours: which route to call and with which filters (05, 06), validating the inputs
before any call (04), where the exchange happens and what to do when it fails (07), and what an
error means for the user (16).

    from agent_sdk.http_client import ServiceError, business_api, exchange_entry_token

    try:
        token = exchange_entry_token(user.app_token)
        order = business_api(token).get("/orders/CMD-1042")
    except ServiceError as exc:
        ...  # exc.status_code == 401: no valid identity; 404: the order does not exist

Only needs `httpx`: usable from `harness.py` and from `mcp_server.py`.
"""

from __future__ import annotations

import os
import threading
from typing import Any

import httpx

DEFAULTS = {
    "BUSINESS_API_URL": "http://127.0.0.1:8001",
    "DOCS_SEARCH_URL": "http://127.0.0.1:8002",
}

_shared_client: httpx.Client | None = None
_shared_lock = threading.Lock()


def shared_http_client() -> httpx.Client:
    """One pooled `httpx.Client` per process (opening a client per call costs ~0.5 s on Windows)."""
    global _shared_client
    with _shared_lock:
        if _shared_client is None:
            _shared_client = httpx.Client(transport=httpx.HTTPTransport(retries=1))
        return _shared_client


class ServiceError(RuntimeError):
    """A call that did not succeed: HTTP error (`status_code`) or unreachable service (None)."""

    def __init__(self, method: str, path: str, status_code: int | None, detail: Any):
        self.method = method
        self.path = path
        self.status_code = status_code
        self.detail = detail
        where = f"HTTP {status_code}" if status_code is not None else "unreachable"
        super().__init__(f"{method} {path}: {where}: {detail}")


class ServiceClient:
    def __init__(self, url_variable: str, token: str | None = None, timeout: float = 10.0):
        self.url_variable = url_variable
        self.token = token
        self.timeout = timeout

    @property
    def base_url(self) -> str:
        return os.environ.get(self.url_variable, DEFAULTS.get(self.url_variable, "")).rstrip("/")

    def get(self, path: str, params: dict | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, json: Any = None) -> Any:
        return self.request("POST", path, json=json)

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        try:
            response = shared_http_client().request(
                method, f"{self.base_url}{path}", headers=headers, timeout=self.timeout, **kwargs
            )
        except httpx.HTTPError as exc:
            raise ServiceError(method, path, None, f"{type(exc).__name__}: {exc}") from exc
        if response.status_code >= 400:
            try:
                data = response.json()
                detail = data.get("detail", data) if isinstance(data, dict) else data
            except ValueError:
                detail = response.text
            raise ServiceError(method, path, response.status_code, detail)
        return response.json() if response.content else None


def business_api(token: str | None = None, timeout: float = 10.0) -> ServiceClient:
    return ServiceClient("BUSINESS_API_URL", token, timeout)


def docs_search(token: str | None = None, timeout: float = 10.0) -> ServiceClient:
    return ServiceClient("DOCS_SEARCH_URL", token, timeout)


def exchange_entry_token(entry_token: str | None, timeout: float = 10.0) -> str:
    """Exchanges the user's entry token for an application token (`POST /auth/exchange`).

    Raises `ServiceError` with `status_code` 401 when the token is missing or refused (forged,
    expired, not an entry token): never fall back to a token built from a declared user id."""
    if not entry_token:
        raise ServiceError("POST", "/auth/exchange", 401, "missing entry token")
    data = business_api(timeout=timeout).post("/auth/exchange", json={"entry_token": entry_token})
    return data["app_token"]
