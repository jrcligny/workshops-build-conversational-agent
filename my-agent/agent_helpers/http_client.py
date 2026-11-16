"""HTTP transport to the business API and the document search: no business logic.

What it gives you: `business_api(token)` and `docs_search(token)` return a `ServiceClient`
whose `get(path, params=None)` and `post(path, json=None)` send the request with
`Authorization: Bearer <token>`, a timeout, and return the decoded JSON. The base URL is read
from `BUSINESS_API_URL` / `DOCS_SEARCH_URL` at each call. Any failure raises `ServiceError`,
with `status_code` (None when the service could not be reached) and the `detail` it returned.

What stays yours: which route to call and with which filters (05, 07), validating the inputs
before any call (04), the token to present (10a), and what an error means for the user (18).

    from agent_helpers.http_client import ServiceError, business_api

    try:
        order = business_api(user.app_token).get("/orders/CMD-1042")
    except ServiceError as exc:
        ...  # exc.status_code == 404: the order does not exist

Only needs `httpx`: usable from `harness.py` and from `mcp_server.py`.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULTS = {
    "BUSINESS_API_URL": "http://127.0.0.1:8001",
    "DOCS_SEARCH_URL": "http://127.0.0.1:8002",
}


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
            response = httpx.request(
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
