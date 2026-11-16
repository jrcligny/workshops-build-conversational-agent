"""Client of the interface contract, used by the workshop tests."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import httpx

# Default of `open`: a signed-in interface, which hands the agent a valid entry token for
# the user. Workshop 10a passes `app_token=None` (or a bad token) to test the refusal.
SIGNED_IN = object()


@dataclass
class Turn:
    events: list[tuple[str, dict]] = field(default_factory=list)
    text: str = ""
    ok: bool = False
    error: str | None = None

    @property
    def types(self) -> list[str]:
        return [t for t, _ in self.events]


class ChatClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.conversation_id: str | None = None

    def open(
        self,
        user_id: str = "camille-renard",
        role: str = "customer_service",
        organization: str = "organization-a",
        app_token: str | None | object = SIGNED_IN,
        limits: dict | None = None,
    ) -> str:
        sign_in = app_token is SIGNED_IN
        if sign_in:
            app_token = None
        body = {
            "user_id": user_id,
            "role": role,
            "organization": organization,
            "app_token": app_token,
            "sign_in": sign_in,
        }
        if limits:
            body["limits"] = limits
        r = httpx.post(f"{self.base_url}/conversations", json=body, timeout=10)
        r.raise_for_status()
        self.conversation_id = r.json()["id"]
        return self.conversation_id

    def turn(
        self,
        text: str,
        attachments: list[str] | None = None,
        interrupt: bool = False,
    ) -> Turn:
        if not self.conversation_id:
            self.open()
        with httpx.stream(
            "POST",
            f"{self.base_url}/conversations/{self.conversation_id}/messages",
            json={
                "text": text,
                "attachments": attachments or [],
                "interrupt": interrupt,
            },
            timeout=30,
        ) as response:
            result = Turn()
            event = "message"
            for line in response.iter_lines():
                if line.startswith("event:"):
                    event = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    data = json.loads(line.split(":", 1)[1].strip() or "{}")
                    result.events.append((event, data))
                    if event == "text":
                        result.text += data.get("content", "")
                    if event == "error":
                        result.error = data.get("detail")
                    if event == "end":
                        result.ok = bool(data.get("ok", True)) and not result.error
                        if data.get("text") and not result.text:
                            result.text = data["text"]
            return result

    def confirm(self, confirmed: bool = True) -> dict:
        if not self.conversation_id:
            self.open()
        r = httpx.post(
            f"{self.base_url}/conversations/{self.conversation_id}/confirmation",
            json={"confirmed": confirmed},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def interrupt(self) -> dict:
        if not self.conversation_id:
            self.open()
        r = httpx.post(
            f"{self.base_url}/conversations/{self.conversation_id}/interruption",
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
