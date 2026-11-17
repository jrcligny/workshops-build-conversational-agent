"""Model client: talks to the proxy (simulated, replayed or live)."""

from __future__ import annotations

from typing import Any, Iterator

import httpx


class ModelUnavailable(RuntimeError):
    """The model could not answer (5xx, 429, timeout, unreachable): worth a fallback.

    Raised whatever the HTTP library underneath (httpx, or httpx2 behind a FastAPI TestClient),
    so a harness never has to inspect transport exceptions itself. A request error (4xx other
    than 429) is not wrapped: it is a bug of the caller, not an outage."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def model_unavailable(exc: BaseException) -> ModelUnavailable | None:
    """Classifies an exception raised while calling the model; None when it is not an outage."""
    if isinstance(exc, ModelUnavailable):
        return exc
    response = getattr(exc, "response", None)
    code = getattr(response, "status_code", None) if response is not None else None
    if isinstance(code, int):
        return ModelUnavailable(f"HTTP {code}") if code >= 500 or code == 429 else None
    names = {cls.__name__ for cls in type(exc).__mro__}
    if names & {"TransportError", "TimeoutException", "ConnectionError", "TimeoutError"}:
        return ModelUnavailable(type(exc).__name__)
    return None


class ModelClient:
    def __init__(self, base_url: str, token: str = "test-student", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(f"{self.base_url}{path}", headers=self._headers(), json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as exc:  # noqa: BLE001
            outage = model_unavailable(exc)
            if outage is not None and outage is not exc:
                raise outage from exc
            raise

    def generate(
        self, messages: list[dict[str, Any]], tools: list[dict] | None = None, model: str = "default"
    ) -> dict[str, Any]:
        """`model` is the logical name the proxy resolves: `default`, or `fallback` (workshop 18)."""
        return self._post(
            "/v1/chat/completions",
            {"model": model, "messages": messages, "tools": tools or None, "stream": False},
        )

    def generate_stream(
        self, messages: list[dict[str, Any]], tools: list[dict] | None = None, model: str = "default"
    ) -> Iterator[str]:
        # The proxy returns a single response; it is split here to exercise streaming.
        data = self.generate(messages, tools, model=model)
        text = data.get("choices", [{}])[0].get("message", {}).get("content") or ""
        yield from _split(text)

    def embeddings(self, texts: list[str]) -> list[list[float]]:
        data = self._post("/v1/embeddings", {"model": "embeddings", "input": texts})["data"]
        return [item["embedding"] for item in sorted(data, key=lambda x: x["index"])]


def _split(text: str, size: int = 24) -> list[str]:
    if not text:
        return [""]
    return [text[i : i + size] for i in range(0, len(text), size)] or [text]
