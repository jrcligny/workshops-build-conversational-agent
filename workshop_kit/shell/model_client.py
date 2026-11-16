"""Model client: talks to the proxy (simulated, replayed, later live)."""

from __future__ import annotations

from typing import Any, Iterator

import httpx


class ModelClient:
    def __init__(self, base_url: str, token: str = "test-student", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def generate(self, messages: list[dict[str, Any]], tools: list[dict] | None = None) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self._headers(),
                json={"model": "default", "messages": messages, "tools": tools or None, "stream": False},
            )
            response.raise_for_status()
            return response.json()

    def generate_stream(self, messages: list[dict[str, Any]], tools: list[dict] | None = None) -> Iterator[str]:
        # During design, the proxy returns a single response; it is split here to exercise streaming.
        data = self.generate(messages, tools)
        text = data.get("choices", [{}])[0].get("message", {}).get("content") or ""
        yield from _split(text)

    def embeddings(self, texts: list[str]) -> list[list[float]]:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/v1/embeddings",
                headers=self._headers(),
                json={"model": "embeddings", "input": texts},
            )
            response.raise_for_status()
            data = response.json()["data"]
            return [item["embedding"] for item in sorted(data, key=lambda x: x["index"])]


def _split(text: str, size: int = 24) -> list[str]:
    if not text:
        return [""]
    return [text[i : i + size] for i in range(0, len(text), size)] or [text]
